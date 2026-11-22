"""OBBD command-line tool.  Run from the repository root:  ./obbd <command> ...

  seed-check [FILES]     validate seed/*.yaml against master list and vocabularies
  scaffold [IDS]         create entries for new master ids from seeds (existing YAML is canonical
                         and left alone; --refresh-from-seed overwrites placeholder entries)
  placeholders [IDS]     regenerate placeholder articles from the current entry YAML
  check-passages IDS     print each passage tag with its verse text, for verification
  validate [--strict]    validate entries, media, links, citations, approvals
  site                   generate the HTML viewer in dist/site/ (open dist/site/index.html)
  serve [--port 8000]    generate it and serve it at http://localhost:8000/dist/site/
  build                  write dist/entries.json, dist/passages.json, dist/media.json
  lookup REF             list entries tagged to passages overlapping REF, e.g. "Ezek 34:23"
  status [--type T]      table of entries with status and approval state
  review ACTION ID --by CONTRIBUTOR [--note TEXT]
                         ACTION: draft | submit | approve | revise | comment
  ref REF...             parse and normalise scripture references
  verse REF...           print verse text (World English Bible; run bible-import first)
  bible-import DIR       import WEB USFM files into .cache/bible/web.json

Media pipeline (see tools/obbd/media.py):
  wiki-resolve           resolve Wikipedia titles -> canonical title + Wikidata QID
  media-candidates [IDS] gather free-licensed Commons candidates into .cache/candidates/
  media-fetch [FILE]     download images chosen in seed/images.yaml, write media/*.yaml
  wikidata-enrich        add coordinates, Pleiades ids, collection/accession from Wikidata (empty fields only)
  media-search QUERY     search Commons; print candidates with license metadata (JSON lines)
  media-info FILE...     license metadata for specific Commons files
  media-sheet            HTML contact sheet of all entry images for human review
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path


def main(argv=None):
    ap = argparse.ArgumentParser(prog="obbd", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("seed-check"); p.add_argument("files", nargs="*")
    p = sub.add_parser("scaffold"); p.add_argument("ids", nargs="*"); p.add_argument("--refresh-from-seed", action="store_true")
    p = sub.add_parser("placeholders"); p.add_argument("ids", nargs="*")
    p = sub.add_parser("check-passages"); p.add_argument("ids", nargs="+"); p.add_argument("--per", type=int, default=3)
    p = sub.add_parser("validate"); p.add_argument("--strict", action="store_true")
    sub.add_parser("build")
    p = sub.add_parser("lookup"); p.add_argument("ref")
    p = sub.add_parser("status"); p.add_argument("--type"); p.add_argument("--status")
    p = sub.add_parser("review")
    p.add_argument("action"); p.add_argument("id"); p.add_argument("--by", required=True)
    p.add_argument("--note"); p.add_argument("--role")
    p = sub.add_parser("ref"); p.add_argument("refs", nargs="+")
    sub.add_parser("wiki-resolve")
    sub.add_parser("site")
    p = sub.add_parser("wikidata-enrich"); p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("serve"); p.add_argument("--port", type=int, default=8000)
    p = sub.add_parser("bible-import"); p.add_argument("dir")
    p = sub.add_parser("verse"); p.add_argument("refs", nargs="+"); p.add_argument("--max", type=int, default=60)
    p = sub.add_parser("media-candidates"); p.add_argument("ids", nargs="*"); p.add_argument("--refresh", action="store_true")
    p = sub.add_parser("media-fetch"); p.add_argument("selection", nargs="?", default="seed/images.yaml")
    p = sub.add_parser("media-sheet"); p.add_argument("--out", default="dist/media-review.html")
    p = sub.add_parser("media-search"); p.add_argument("query"); p.add_argument("--limit", type=int, default=15)
    p = sub.add_parser("media-info"); p.add_argument("files", nargs="+")
    p = sub.add_parser("media-preview"); p.add_argument("files", nargs="+"); p.add_argument("--out", required=True); p.add_argument("--width", type=int, default=400)
    a = ap.parse_args(argv)

    if a.cmd == "wikidata-enrich":
        from .wikidata import enrich
        return enrich(a.dry_run)
    if a.cmd == "site":
        from .site import build_site
        build_site(); return
    if a.cmd == "serve":
        from .site import serve
        return serve(a.port)
    if a.cmd == "bible-import":
        from .bible import import_usfm
        return import_usfm(Path(a.dir))
    if a.cmd == "verse":
        from .bible import text
        for r in a.refs:
            for label, t in text(r, a.max):
                print(f"{label}  {t}")
        return
    if a.cmd == "wiki-resolve":
        from .media import resolve_wikipedia
        return resolve_wikipedia()
    if a.cmd == "media-candidates":
        from .media import gather_candidates
        return gather_candidates(a.ids or None, a.refresh)
    if a.cmd == "media-fetch":
        from .media import fetch_selected
        return fetch_selected(Path(a.selection))
    if a.cmd in ("media-search", "media-info"):
        import json as _j
        from .media import commons_search, file_info, JUNK
        titles = commons_search(a.query, a.limit) if a.cmd == "media-search" else a.files
        if a.cmd == "media-search":
            titles = [t for t in titles if not JUNK.search(t)]
        info = file_info(titles) if titles else {}
        for t in titles:
            r = info.get(t if t.startswith("File:") else "File:" + t)
            if not r:
                print(f"- {t}: not on Commons"); continue
            print(_j.dumps({k: r[k] for k in ("title", "free", "license_short", "artist", "width", "height", "description", "thumb")}, ensure_ascii=False))
        return
    if a.cmd == "media-preview":
        from .media import api, COMMONS, S, slugify
        out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
        titles = [t if t.startswith("File:") else "File:" + t for t in a.files]
        d = api(COMMONS, action="query", titles="|".join(titles[:50]), prop="imageinfo", iiprop="url", iiurlwidth=a.width)
        norm = {n["to"]: n["from"] for n in d.get("query", {}).get("normalized", [])}
        found = {}
        for pg in d.get("query", {}).get("pages", []):
            if pg.get("imageinfo"):
                found[norm.get(pg["title"], pg["title"])] = pg["imageinfo"][0]
        for t in titles:
            ii = found.get(t)
            if not ii:
                print(f"{t}: not found"); continue
            url = ii.get("thumburl") or ii["url"]
            dest = out / (slugify(t) + ".jpg")
            resp = S.get(url, timeout=60); resp.raise_for_status()
            dest.write_bytes(resp.content)
            print(dest)
        return
    if a.cmd == "media-sheet":
        from .sheet import media_sheet
        return media_sheet(Path(a.out))

    if a.cmd == "seed-check":
        from .common import SEED
        from .seed import check_files
        files = [Path(f) for f in a.files] or sorted(SEED.glob("*.yaml"))
        sys.exit(1 if check_files(files) else 0)
    if a.cmd == "scaffold":
        from .scaffold import scaffold
        print(scaffold(set(a.ids) or None, refresh_from_seed=a.refresh_from_seed))
    elif a.cmd == "placeholders":
        from .scaffold import regenerate_placeholders
        print(f"regenerated {regenerate_placeholders(set(a.ids) or None)} placeholder articles")
    elif a.cmd == "check-passages":
        from .bible import text
        from .common import load_entry
        for id_ in a.ids:
            e = load_entry(id_)
            print(f"## {id_} | {e['type']} | {e['title']}\n   scope: {e['scope'][:300]}")
            for k, p in enumerate(e["passages"]):
                print(f"[{k}] {p['ref']} | {p['rel']}{'?' if p.get('disputed') else ''} | {p.get('note','')}")
                try:
                    vs = text(p["ref"], 400)
                except Exception as ex:
                    print(f"     !! {ex}"); continue
                show = vs if len(vs) <= a.per + 1 else vs[:a.per] + [("…", f"({len(vs) - a.per - 1} more verses)")] + vs[-1:]
                for label, t in show:
                    print(f"     {label}  {t[:400]}")
            print()
    elif a.cmd == "validate":
        from .validate import validate
        sys.exit(1 if validate(a.strict) else 0)
    elif a.cmd == "build":
        from .build import build
        build()
    elif a.cmd == "lookup":
        from .build import lookup
        from .common import relations
        rl = relations()
        for _, id_, title, disp, rel, disputed, note in lookup(a.ref):
            lab = rl[rel]["label"] + (" (disputed)" if disputed else "")
            print(f"{disp:18} {lab:36} {id_:34} {note or ''}")
    elif a.cmd == "status":
        from .common import ENTRIES, all_entry_ids, load_yaml
        from .review import approval_state
        c = Counter()
        for id_ in all_entry_ids():
            e = load_yaml(ENTRIES / f"{id_}.yaml")
            if a.type and e["type"] != a.type:
                continue
            if a.status and e["status"] != a.status:
                continue
            st = approval_state(e)
            c[e["status"]] += 1
            print(f"{id_:45} {e['type']:9} {e['status']:15} {st:14} {len(e.get('media') or [])} img  {len(e.get('passages') or [])} psg")
        print(dict(c))
    elif a.cmd == "review":
        from .review import apply
        print(apply(a.id, a.action, a.by, a.note, a.role))
    elif a.cmd == "ref":
        from . import refs
        for r in a.refs:
            try:
                print(f"{r} -> {refs.display(r)}  {[x.osis() for x in refs.parse(r)]}")
            except refs.RefError as ex:
                print(f"{r} !! {ex}")


if __name__ == "__main__":
    main()
