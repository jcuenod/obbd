"""Expand seed entries into entries/<id>.yaml + entries/<id>.md.

Safe to re-run: once an entry has left `placeholder` status, its article
is never touched and only empty structured fields are filled in.
"""
from __future__ import annotations

import datetime as dt

from . import refs
from .common import (ENTRIES, MEDIA, article_hash, date_display, dump_yaml, entry_paths,
                     entry_sections, load_yaml, master, relations)
from .seed import load_seed_files, parse_passage

SCAFFOLD_BY = "claude-opus-5-5"

SECTION_GUIDANCE = {
    "Overview": "One paragraph saying what this is, when and where it comes from, and why it matters for reading the Bible. This paragraph is also used as the entry summary in search results and link previews, so it must stand on its own.",
    "Description and Provenance": "Physical description (material, dimensions, script/language), discovery (who, when, where; excavated or purchased), and current location. Note any provenance concerns.",
    "Manuscripts and Date": "Principal manuscripts/copies, their find-spots and dates, and the date of composition if different. Language and script.",
    "Contents": "Summary of contents. Quote short key lines in translation (own translation or openly licensed), with line numbers.",
    "Location and Identification": "Where the site is, its modern name(s), and how its identification with the ancient place was made (and how secure it is).",
    "Archaeological History": "Excavation history and main occupation phases. Key finds, with dates.",
    "Extrabiblical Sources": "The inscriptions, documents, or artefacts that attest this person, with dates.",
    "Biblical Portrayal": "How the biblical texts present this person, with references.",
    "Historical Assessment": "Where the biblical and extrabiblical evidence agree, where they differ, and what the mainstream reconstruction is.",
    "Sources and Iconography": "Primary textual sources and iconographic representations, with their cultures and dates.",
    "In the Hebrew Bible": "Where and how the topic appears in the Hebrew Bible. Organise by theme or corpus, not as a verse list.",
    "In the New Testament": "Where and how the topic appears in the New Testament, including how New Testament writers use Hebrew Bible texts. Organise by theme or corpus, not as a verse list.",
    "Sources": "Primary sources (textual and archaeological) for the topic.",
    "History": "A short historical overview.",
    "In the Bible": "Where and how the topic appears in the Bible. Organise by theme or corpus (e.g. Hebrew Bible, New Testament), not as a verse list.",
    "Reconstruction": "The mainstream historical reconstruction, noting points of debate.",
    "Biblical Accounts": "The relevant biblical narratives and how they relate to the other sources.",
    "Ancient Near Eastern Evidence": "Representative evidence from across the ANE (Mesopotamia, Egypt, Anatolia, Levant). Link to the artefact and text entries with [[wikilinks]].",
    "Jewish and Greco-Roman Evidence": "Representative Second Temple Jewish sources (Dead Sea Scrolls, apocrypha and pseudepigrapha, Philo, Josephus, inscriptions, archaeology) and Greco-Roman sources. Mention earlier ancient Near Eastern background only where it matters. Link to the artefact and text entries with [[wikilinks]].",
    "Extrabiblical Evidence": "Representative evidence from outside the Bible: the ancient Near East (Mesopotamia, Egypt, Anatolia, Levant), Second Temple Jewish sources, and the Greco-Roman world, as relevant. Link to the artefact and text entries with [[wikilinks]].",
    "Archaeological Evidence": "What the archaeological record shows: typical examples, sites, periods. Link to specific artefact entries.",
    "Significance for Biblical Studies": "How this illuminates the tagged passages. Separate what the source shows directly from what scholars infer, and note which comparisons are disputed.",
    "Interpretive Significance": "What difference this background makes to interpretation. Separate consensus from minority positions.",
    "Scholarly Issues": "Open questions, major debates, and positions held, stated even-handedly.",
    "Further Reading": "3–6 items cited as [@citekey], with the keys defined in bibliography/references.yaml. Prefer standard editions and translations (e.g. COS, ANET, RINAP, SAA, KAI, TAD for the ancient Near East; DJD, OTP, Loeb Classical Library, CIIP for Second Temple Jewish and Greco-Roman sources) and recent peer-reviewed treatments.",
}


def build_entry(seed: dict | None, m: dict) -> dict:
    seed = seed or {}
    title = seed.get("title") or m["title"]
    e: dict = {"id": m["id"], "title": title}
    if seed.get("aliases"):
        e["aliases"] = seed["aliases"]
    e["type"] = m["type"]
    if seed.get("cultures"):
        e["cultures"] = seed["cultures"]
    if seed.get("corpus"):
        e["corpus"] = seed["corpus"]
    if seed.get("date"):
        d = seed["date"]
        date = {"from": d[0], "to": d[-1]}
        if seed.get("circa"):
            date["circa"] = True
        date["display"] = date_display(date)
        e["date"] = date
    e["scope"] = (seed.get("scope") or "").strip() or f"TODO: scope statement. Seed hints: {m['hints']}"
    passages = []
    for s in seed.get("passages") or []:
        passages.append(parse_passage(s))
    e["passages"] = passages
    e["related"] = seed.get("related") or []
    if seed.get("location"):
        e["location"] = {"institution": seed["location"], "accession": None}
    e["media"] = []
    ext = {}
    if seed.get("wikipedia"):
        ext["wikipedia"] = seed["wikipedia"]
    e["external"] = ext
    editorial = {}
    if seed.get("author_notes"):
        editorial["author_notes"] = seed["author_notes"]
    if seed.get("sources_to_check"):
        editorial["sources_to_check"] = seed["sources_to_check"]
    if seed.get("image") is not None:
        editorial["image_query"] = seed.get("image")
    if editorial:
        e["editorial"] = editorial
    e["status"] = "placeholder"
    e["credits"] = {"authors": [], "reviewers": []}
    e["history"] = [{
        "date": dt.date.today().isoformat(),
        "action": "created",
        "by": SCAFFOLD_BY,
        "note": "Scaffolded from the seed list. Passage tags and scope are AI-generated and need expert review.",
    }]
    return e


def placeholder_md(e: dict) -> str:
    rels = relations()
    lines = [
        "> [!info] Placeholder: this article has not been written",
        "> This file was generated from the seed list. Write the article under the headings below,",
        "> adapting them as needed, and delete these callouts once drafting starts.",
        "> Structured data (passages, images, review status) is kept in the sidecar YAML file, not here.",
        "",
        "> [!abstract] Scope",
    ]
    lines += [f"> {l}" for l in e["scope"].splitlines()]
    lines.append("")
    notes = (e.get("editorial") or {}).get("author_notes") or []
    lines.append("> [!todo] What the article should cover")
    for n in notes:
        lines.append(f"> - {n}")
    if e["passages"]:
        lines.append("> - Explain how the entry bears on each tagged passage:")
        for p in e["passages"]:
            try:
                disp = refs.display(p["ref"])
            except refs.RefError:
                disp = p["ref"]
            rl = rels.get(p["rel"], {}).get("label", p["rel"])
            dis = " (disputed)" if p.get("disputed") else ""
            note = f": {p['note']}" if p.get("note") else ""
            lines.append(f">   - **{disp}** [{rl}{dis}]{note}")
    if e["related"]:
        lines.append("> - Link related entries where relevant: " + ", ".join(f"[[{r}]]" for r in e["related"]))
    srcs = (e.get("editorial") or {}).get("sources_to_check") or []
    if srcs:
        lines.append("> - Standard editions and translations to check (AI-suggested; verify every one): " + "; ".join(srcs))
    if e.get("media"):
        lines.append("> - Available images (the primary image is placed automatically; embed others with `![[file]]`): "
                     + ", ".join(f"`{m['id']}`" for m in e["media"]))
    lines.append("")
    for sec in entry_sections(e):
        lines.append(f"## {sec}")
        lines.append("")
        lines.append(f"<!-- {SECTION_GUIDANCE.get(sec, '')} -->")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def regenerate_placeholders(only: set[str] | None = None) -> int:
    """Rebuild the placeholder article of every entry still in `placeholder` status
    from its *current* YAML (the YAML, not the seed, is canonical once scaffolded)."""
    n = 0
    for ypath in sorted(ENTRIES.glob("*.yaml")):
        if only and ypath.stem not in only:
            continue
        e = load_yaml(ypath)
        if e.get("status") == "placeholder":
            (ENTRIES / f"{e['id']}.md").write_text(placeholder_md(e))
            n += 1
    return n


def scaffold(only: set[str] | None = None, rewrite_placeholders: bool = True,
             refresh_from_seed: bool = False) -> dict:
    """Create entries for master ids that have no YAML yet. With refresh_from_seed, also
    overwrite placeholder-status entries from their seeds (discarding later YAML edits
    to seed-derived fields)."""
    seeds = load_seed_files()
    stats = {"created": 0, "updated": 0, "skipped": 0, "unseeded": 0}
    ENTRIES.mkdir(exist_ok=True)
    for id_, m in master().items():
        if only and id_ not in only:
            continue
        seed = seeds.get(id_)
        if not seed:
            stats["unseeded"] += 1
        ypath, mpath = entry_paths(id_)
        new = build_entry(seed, m)
        if ypath.exists() and not refresh_from_seed:
            stats["skipped"] += 1
            continue
        if ypath.exists():
            old = load_yaml(ypath)
            if old.get("status") != "placeholder":
                stats["skipped"] += 1
                continue
            # keep fields that tools/humans have added since scaffolding
            for k in ("media", "history", "credits"):
                if old.get(k):
                    new[k] = old[k]
            if old.get("external"):
                # resolved/curated external ids win over raw seed values
                new["external"] = {**new.get("external", {}), **old["external"]}
            if old.get("location") and new.get("location"):
                new["location"]["accession"] = old["location"].get("accession")
            stats["updated"] += 1
        else:
            stats["created"] += 1
        ypath.write_text(dump_yaml(new, "entry"))
        if rewrite_placeholders and (not mpath.exists() or new["status"] == "placeholder"):
            mpath.write_text(placeholder_md(new))
    return stats
