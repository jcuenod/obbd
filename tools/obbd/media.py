"""Image sourcing from Wikimedia Commons, with license verification.

Pipeline:
  1. resolve     For entries with external.wikipedia: resolve redirects, record the
                 Wikidata QID, and note the article's lead image.
  2. candidates  For entries that want an image: collect candidate files (Wikipedia
                 lead image, images used in the article, Commons search hits) and fetch
                 their Commons metadata. Files whose license is not free are dropped.
                 Writes .cache/candidates/<entry>.json.
  3. (selection) A person or agent writes seed/images.yaml: entry -> chosen files + captions.
  4. fetch       Downloads each chosen file (max 1600 px wide), writes media/<id>.<ext>
                 and media/<id>.yaml with full attribution, and links it from the entry.

Only files on Wikimedia Commons are used, because Commons requires a free license
and machine-readable license metadata. Non-free (fair-use) English Wikipedia
uploads are never used.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import time
from pathlib import Path

import requests
import yaml

from .common import (ENTRIES, MEDIA, ROOT, all_entry_ids, dump_yaml, entry_types, load_yaml,
                     save_entry)

CACHE = ROOT / ".cache"
UA = "OBBD-media-sourcing/0.1 (https://parabible.com; Open Bible Background Dictionary) python-requests/" + requests.__version__
COMMONS = "https://commons.wikimedia.org/w/api.php"
ENWIKI = "https://en.wikipedia.org/w/api.php"
THUMB_WIDTH = 1600

S = requests.Session()
S.headers["User-Agent"] = UA


def api(url: str, **params) -> dict:
    params = {"format": "json", "formatversion": 2, "maxlag": 5, **params}
    for attempt in range(10):
        r = S.get(url, params=params, timeout=60)
        if r.status_code == 429 or r.status_code >= 500:
            wait = int(r.headers.get("Retry-After", 0) or 0) or min(15 * (attempt + 1), 120)
            print(f"  (HTTP {r.status_code}; waiting {wait}s)", flush=True)
            time.sleep(wait)
            continue
        r.raise_for_status()
        d = r.json()
        if d.get("error", {}).get("code") == "maxlag":
            time.sleep(5)
            continue
        time.sleep(0.5)  # be polite: at most ~2 requests/second
        return d
    r.raise_for_status()
    return {}


# ---------------------------------------------------------------- licenses

def strip_html(s: str | None) -> str | None:
    if not s:
        return None
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip() or None


_LIC_MAP = [
    (r"^cc0", "CC0-1.0"),
    (r"^public domain|^pd\b|^pd-", "PD"),
    (r"^cc by-sa (\d\.\d)( (de|at|es|fr|it|nl|pl))?", "CC-BY-SA-{0}"),
    (r"^cc by (\d\.\d)", "CC-BY-{0}"),
    (r"^cc-by-sa-(\d\.\d)", "CC-BY-SA-{0}"),
    (r"^cc-by-(\d\.\d)", "CC-BY-{0}"),
    (r"^gfdl", "GFDL"),
    (r"^fal|^free art", "FAL"),
]

# Licenses recognised by normalise_license() but not accepted for use. GFDL requires the
# full license text to accompany every copy, which is impractical for a website, and
# Commons itself stopped accepting GFDL-only photos in 2018.
REJECTED_LICENSES = {"GFDL"}

# Commons license categories, in order of preference, used to find a usable license on
# files whose LicenseShortName is a rejected one (e.g. GFDL + CC BY-SA dual licensing).
_ALT_LIC_CATS = [
    (r"^(?:CC-Zero|CC0)$", "CC0-1.0", "CC0"),
    (r"^CC-BY-(\d\.\d)$", "CC-BY-{0}", "CC BY {0}"),
    (r"^CC-BY-SA-(\d\.\d)(?:-migrated)?$", "CC-BY-SA-{0}", "CC BY-SA {0}"),
    (r"^FAL$", "FAL", "FAL"),
]

LICENSE_URLS = {
    "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "PD": "https://creativecommons.org/publicdomain/mark/1.0/",
    "FAL": "https://artlibre.org/licence/lal/en/",
}


def alternative_license(categories: str | None) -> tuple[str, str] | None:
    """Best accepted license among a file's Commons categories, as (id, short name)."""
    cats = [c.strip() for c in (categories or "").split("|")]
    for pat, lic_id, short in _ALT_LIC_CATS:
        for c in cats:
            m = re.match(pat, c)
            if m:
                return lic_id.format(*m.groups()), short.format(*m.groups())
    return None


def normalise_license(short: str | None) -> str | None:
    if not short:
        return None
    s = short.strip().lower()
    for pat, out in _LIC_MAP:
        m = re.match(pat, s)
        if m:
            return out.format(*m.groups()) if "{0}" in out else out
    return None


def license_url(lic_id: str, meta_url: str | None) -> str | None:
    if meta_url:
        return meta_url
    if lic_id in LICENSE_URLS:
        return LICENSE_URLS[lic_id]
    m = re.match(r"CC-(BY(?:-SA)?)-(\d\.\d)", lic_id)
    if m:
        return f"https://creativecommons.org/licenses/{m.group(1).lower()}/{m.group(2)}/"
    return None


def file_info(titles: list[str]) -> dict[str, dict]:
    """Commons imageinfo + extmetadata for File: titles (batched)."""
    out = {}
    titles = [t if t.startswith("File:") else f"File:{t}" for t in titles]
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        d = api(COMMONS, action="query", titles="|".join(batch), prop="imageinfo",
                iiprop="url|size|mime|sha1|extmetadata|timestamp", iiurlwidth=THUMB_WIDTH)
        norm = {n["from"]: n["to"] for n in d.get("query", {}).get("normalized", [])}
        for p in d.get("query", {}).get("pages", []):
            if p.get("missing") or not p.get("imageinfo"):
                continue
            ii = p["imageinfo"][0]
            em = {k: v.get("value") for k, v in (ii.get("extmetadata") or {}).items()}
            lic_short = em.get("LicenseShortName")
            lic_id = normalise_license(lic_short)
            meta_url = em.get("LicenseUrl")
            if lic_id in REJECTED_LICENSES:
                alt = alternative_license(em.get("Categories"))
                if alt:  # dual-licensed: use the accepted license, not the rejected one
                    lic_id, lic_short = alt
                    meta_url = None
                else:
                    lic_id = None
            nonfree = str(em.get("NonFree", "")).lower() == "true"
            rec = {
                "title": p["title"],
                "page": ii.get("descriptionurl"),
                "url": ii.get("url"),
                "thumb": ii.get("thumburl"),
                "width": ii.get("width"), "height": ii.get("height"),
                "mime": ii.get("mime"), "sha1": ii.get("sha1"),
                "description": strip_html(em.get("ImageDescription")),
                "artist": strip_html(em.get("Artist")),
                "credit": strip_html(em.get("Credit")),
                "license_short": lic_short,
                "license_id": lic_id,
                "license_url": license_url(lic_id, meta_url) if lic_id else None,
                "attribution_required": str(em.get("AttributionRequired", "")).lower() == "true",
                "usage_terms": strip_html(em.get("UsageTerms")),
                "restrictions": em.get("Restrictions") or None,
                "date": strip_html(em.get("DateTimeOriginal")),
                "categories": strip_html(em.get("Categories")),
                "free": bool(lic_id) and not nonfree,
            }
            out[p["title"]] = rec
        for a, b in norm.items():
            if b in out:
                out[a] = out[b]
    return out


# ---------------------------------------------------------------- resolve

def resolve_wikipedia() -> None:
    CACHE.mkdir(exist_ok=True)
    cache_p = CACHE / "wikipedia.json"
    cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
    todo = {}
    for id_ in all_entry_ids():
        e = load_yaml(ENTRIES / f"{id_}.yaml")
        t = (e.get("external") or {}).get("wikipedia")
        if t and t not in cache:
            todo[t] = id_
    titles = list(todo)
    for i in range(0, len(titles), 40):
        batch = titles[i:i + 40]
        d = api(ENWIKI, action="query", titles="|".join(batch), redirects=1,
                prop="pageprops|pageimages", ppprop="wikibase_item", piprop="name")
        q = d.get("query", {})
        fwd = {}
        for n in q.get("normalized", []):
            fwd[n["from"]] = n["to"]
        for r in q.get("redirects", []):
            fwd[r["from"]] = r["to"]
        pages = {p["title"]: p for p in q.get("pages", [])}
        for t in batch:
            final = t
            for _ in range(3):
                final = fwd.get(final, final)
            p = pages.get(final, {})
            if p.get("missing") or not p:
                cache[t] = {"missing": True}
            else:
                cache[t] = {"title": p["title"], "wikidata": (p.get("pageprops") or {}).get("wikibase_item"),
                            "pageimage": p.get("pageimage")}
        cache_p.write_text(json.dumps(cache, indent=1, ensure_ascii=False))
    cache_p.write_text(json.dumps(cache, indent=1, ensure_ascii=False))
    # write back to entries
    missing = []
    for id_ in all_entry_ids():
        e = load_yaml(ENTRIES / f"{id_}.yaml")
        ext = e.get("external") or {}
        t = ext.get("wikipedia")
        if not t:
            continue
        c = cache.get(t, {})
        if c.get("missing"):
            missing.append((id_, t))
            ext.pop("wikipedia", None)
            e["external"] = ext
            save_entry(e)
            continue
        changed = False
        if c.get("title") and c["title"] != t:
            ext["wikipedia"] = c["title"]; changed = True
        if c.get("wikidata") and ext.get("wikidata") != c["wikidata"]:
            ext["wikidata"] = c["wikidata"]; changed = True
        if changed:
            e["external"] = ext
            save_entry(e)
    for id_, t in missing:
        print(f"no Wikipedia article: {id_}: {t!r}")
    print(f"resolved {len(cache)} titles; {len(missing)} missing")


# ---------------------------------------------------------------- candidates

JUNK = re.compile(r"(flag|logo|icon|symbol|commons-|wiki|stub|disambig|question_book|edit-clear|"
                  r"crystal|nuvola|ambox|padlock|portal|locator|location_map|blank|"
                  r"\.svg$|\.pdf$|\.djvu$|\.ogg$|\.webm$|\.ogv$|\.mp3$|\.tif$|\.tiff$)", re.I)


def wiki_images(title: str, limit: int = 25) -> list[str]:
    d = api(ENWIKI, action="query", titles=title, redirects=1, prop="images", imlimit=limit)
    pages = d.get("query", {}).get("pages", [])
    return [i["title"] for p in pages for i in p.get("images", [])]


def commons_search(q: str, limit: int = 12) -> list[str]:
    d = api(COMMONS, action="query", list="search", srsearch=f"{q} filetype:bitmap",
            srnamespace=6, srlimit=limit)
    return [h["title"] for h in d.get("query", {}).get("search", [])]


def wants_image(e: dict) -> bool:
    ed = e.get("editorial") or {}
    if "image_query" in ed:
        return ed["image_query"] is not None
    return entry_types()[e["type"]].get("image_expected", False)


def wiki_images_batch(titles: list[str]) -> dict[str, list[str]]:
    """Images used on many enwiki articles, 20 titles per request (with continuation)."""
    out: dict[str, list[str]] = {t: [] for t in titles}
    for i in range(0, len(titles), 20):
        batch = titles[i:i + 20]
        cont: dict = {}
        while True:
            d = api(ENWIKI, action="query", titles="|".join(batch), prop="images", imlimit="max", **cont)
            for p in d.get("query", {}).get("pages", []):
                if p["title"] in out:
                    out[p["title"]].extend(im["title"] for im in p.get("images", []))
            if "continue" not in d:
                break
            cont = {k: v for k, v in d["continue"].items()}
        print(f"  wiki images: {min(i + 20, len(titles))}/{len(titles)} articles", flush=True)
    return out


def gather_candidates(ids: list[str] | None = None, refresh: bool = False) -> None:
    """Batched: (1) article images for all entries, (2) one Commons search per entry,
    (3) Commons metadata for all candidate files 50 at a time, (4) per-entry JSON."""
    out_dir = CACHE / "candidates"
    out_dir.mkdir(parents=True, exist_ok=True)
    wcache_p = CACHE / "wikipedia.json"
    wcache = json.loads(wcache_p.read_text()) if wcache_p.exists() else {}
    scache_p = CACHE / "commons-search.json"
    scache = json.loads(scache_p.read_text()) if scache_p.exists() else {}
    todo = []
    for id_ in ids or all_entry_ids():
        e = load_yaml(ENTRIES / f"{id_}.yaml")
        if wants_image(e) and (refresh or not (out_dir / f"{id_}.json").exists()):
            todo.append(e)
    print(f"{len(todo)} entries to process", flush=True)
    # 1. article images, batched
    art_titles = {}
    for e in todo:
        wt = (e.get("external") or {}).get("wikipedia")
        wc = wcache.get(wt or "", {})
        if wt and not wc.get("missing"):
            art_titles[e["id"]] = wc.get("title", wt)
    art_imgs = wiki_images_batch(sorted(set(art_titles.values()))) if art_titles else {}
    # 2. commons search per entry (cached so the step can resume)
    for n, e in enumerate(todo, 1):
        q = (e.get("editorial") or {}).get("image_query") or e["title"]
        if q not in scache:
            scache[q] = commons_search(q)
            if not scache[q] and e["title"] != q and e["title"] not in scache:
                scache[e["title"]] = commons_search(e["title"])
            scache_p.write_text(json.dumps(scache, ensure_ascii=False))
        if n % 25 == 0:
            print(f"  commons search: {n}/{len(todo)}", flush=True)
    # assemble sources
    per_entry: dict[str, dict[str, set]] = {}
    for e in todo:
        sources: dict[str, set] = {}
        wt = (e.get("external") or {}).get("wikipedia")
        wc = wcache.get(wt or "", {})
        if wc.get("pageimage"):
            sources.setdefault("File:" + wc["pageimage"].replace("_", " "), set()).add("wp-lead")
        for t in art_imgs.get(art_titles.get(e["id"], ""), [])[:30]:
            if not JUNK.search(t):
                sources.setdefault(t, set()).add("wp-article")
        q = (e.get("editorial") or {}).get("image_query") or e["title"]
        hits = scache.get(q) or scache.get(e["title"]) or []
        for t in hits:
            if not JUNK.search(t):
                sources.setdefault(t, set()).add("commons-search")
        per_entry[e["id"]] = sources
    # 3. metadata, batched across entries
    icache_p = CACHE / "fileinfo.json"
    icache = json.loads(icache_p.read_text()) if icache_p.exists() else {}
    want = sorted({t if t.startswith("File:") else "File:" + t for s in per_entry.values() for t in s} - set(icache))
    for i in range(0, len(want), 50):
        got = file_info(want[i:i + 50])
        for t in want[i:i + 50]:
            icache[t] = got.get(t)  # None = not on Commons
        icache_p.write_text(json.dumps(icache, ensure_ascii=False))
        print(f"  file info: {min(i + 50, len(want))}/{len(want)}", flush=True)
    # 4. write per-entry candidate files
    for e in todo:
        cands = []
        for t, srcs in per_entry[e["id"]].items():
            rec = icache.get(t if t.startswith("File:") else "File:" + t)
            if rec:
                cands.append(dict(rec, sources=sorted(srcs)))
        free = [c for c in cands if c["free"]]
        nonfree = [c["title"] for c in cands if not c["free"]]
        free.sort(key=lambda c: ("wp-lead" not in c["sources"], "wp-article" not in c["sources"],
                                 (c["width"] or 0) * (c["height"] or 0) < 800 * 600))
        q = (e.get("editorial") or {}).get("image_query") or e["title"]
        (out_dir / f"{e['id']}.json").write_text(json.dumps(
            {"id": e["id"], "title": e["title"], "type": e["type"], "query": q, "scope": e.get("scope"),
             "candidates": free, "rejected_nonfree": nonfree}, indent=1, ensure_ascii=False))
    print(f"wrote candidates for {len(todo)} entries")


# ---------------------------------------------------------------- fetch

def slugify(s: str, maxlen: int = 64) -> str:
    s = re.sub(r"^File:", "", s)
    s = re.sub(r"\.[A-Za-z0-9]{2,5}$", "", s)
    s = s.lower()
    s = re.sub(r"[^\w]+", "-", s, flags=re.ASCII)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:maxlen].rstrip("-") or "image"


def attribution(rec: dict) -> str:
    who = rec.get("artist") or "Unknown author"
    lic = rec.get("license_short") or rec.get("license_id")
    if rec.get("license_id") == "PD":
        return f"{who}. Public domain, via Wikimedia Commons."
    if rec.get("license_id") == "CC0-1.0":
        return f"{who}. CC0, via Wikimedia Commons."
    return f"{who}, {lic}, via Wikimedia Commons."


def fetch_selected(selection_path: Path) -> None:
    """seed/images.yaml format:
         <entry-id>:
           - file: "File:Mesha stele Louvre.jpg"
             caption: The Mesha Stele (Louvre, Paris)
             role: primary            # primary | gallery
             depicts: [mesha-stele]   # optional extra entries to link this media to
    """
    sel = yaml.safe_load(selection_path.read_text()) or {}
    MEDIA.mkdir(exist_ok=True)
    titles = sorted({(i["file"] if i["file"].startswith("File:") else "File:" + i["file"])
                     for items in sel.values() for i in items or []})
    info = file_info(titles)
    existing = {load_yaml(p).get("source", {}).get("page"): p.stem for p in MEDIA.glob("*.yaml")}
    used_ids = {p.stem for p in MEDIA.glob("*.yaml")}
    today = dt.date.today().isoformat()
    n_new = 0
    for entry_id, items in sel.items():
        if not (ENTRIES / f"{entry_id}.yaml").exists():
            print(f"skip: no entry {entry_id}")
            continue
        for item in items or []:
            t = item["file"] if item["file"].startswith("File:") else "File:" + item["file"]
            rec = info.get(t)
            if not rec:
                print(f"!! {entry_id}: {t} not found on Commons")
                continue
            if not rec["free"]:
                print(f"!! {entry_id}: {t} license {rec['license_short']!r} not accepted")
                continue
            mid = existing.get(rec["page"])
            if not mid:
                base = entry_id
                mid = base
                k = 2
                while mid in used_ids:
                    mid = f"{base}-{k}"; k += 1
                used_ids.add(mid)
                url = rec["thumb"] if max(rec["width"] or 0, rec["height"] or 0) > THUMB_WIDTH and rec.get("thumb") else rec["url"]
                ext = Path(url.split("?")[0]).suffix.lower() or ".jpg"
                if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                    ext = ".jpg"
                if ext == ".jpeg":
                    ext = ".jpg"
                fname = f"{mid}{ext}"
                for attempt in range(5):
                    r = S.get(url, timeout=120)
                    if r.status_code == 429:
                        time.sleep(5 * (attempt + 1)); continue
                    r.raise_for_status(); break
                (MEDIA / fname).write_bytes(r.content)
                w, h = rec["width"], rec["height"]
                try:
                    from PIL import Image
                    with Image.open(MEDIA / fname) as im:
                        big = max(im.size) > THUMB_WIDTH
                        heavy = (MEDIA / fname).stat().st_size > 500_000
                        if big or heavy:
                            if ext == ".jpg":
                                im = im.convert("RGB")
                            if big:
                                im.thumbnail((THUMB_WIDTH, THUMB_WIDTH), Image.LANCZOS)
                            im.save(MEDIA / fname, **({"quality": 85, "optimize": True, "progressive": True} if ext == ".jpg" else {"optimize": True}))
                        w, h = im.size
                except Exception as ex:
                    print(f"  (could not inspect/resize {fname}: {ex})")
                m = {
                    "id": mid,
                    "file": fname,
                    "title": re.sub(r"^File:", "", t),
                    "caption": item.get("caption"),
                    "description": (rec.get("description") or "")[:600] or None,
                    "creator": rec.get("artist"),
                    "credit_line": rec.get("credit"),
                    "license": {"id": rec["license_id"], "name": rec["license_short"], "url": rec["license_url"]},
                    "attribution": attribution(rec),
                    "source": {"page": rec["page"], "original_url": rec["url"].split("?")[0], "sha1": rec["sha1"],
                               "original_size": [rec["width"], rec["height"]], "retrieved": today},
                    "derivative": (f"Downscaled to {w}×{h} px" if (w, h) != (rec["width"], rec["height"]) else None),
                    "size": [w, h],
                    "depicts": sorted({entry_id, *(item.get("depicts") or [])}),
                    "review": {"status": "unreviewed", "checked_by": None, "date": None,
                               "note": "Picked by an AI agent from Commons search results. Check that the image really shows the subject and that the license is correct."},
                }
                if rec.get("restrictions"):
                    m["restrictions"] = rec["restrictions"]
                (MEDIA / f"{mid}.yaml").write_text(dump_yaml(m, "media"))
                existing[rec["page"]] = mid
                n_new += 1
                time.sleep(0.5)
            else:
                m = load_yaml(MEDIA / f"{mid}.yaml")
                dep = set(m.get("depicts") or []) | {entry_id} | set(item.get("depicts") or [])
                if dep != set(m.get("depicts") or []):
                    m["depicts"] = sorted(dep)
                    (MEDIA / f"{mid}.yaml").write_text(dump_yaml(m, "media"))
            # link to entry/entries
            for target in {entry_id, *(item.get("depicts") or [])}:
                p = ENTRIES / f"{target}.yaml"
                if not p.exists():
                    continue
                e = load_yaml(p)
                media = e.get("media") or []
                if not any(x["id"] == mid for x in media):
                    role = item.get("role", "primary" if not media else "gallery") if target == entry_id else "gallery"
                    if role == "primary" and any(x.get("role") == "primary" for x in media):
                        role = "gallery"
                    media.append({"id": mid, "role": role})
                    e["media"] = media
                    save_entry(e)
    print(f"fetched {n_new} new media files")
