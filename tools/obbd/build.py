"""Build machine-readable outputs in dist/ (generated; not committed).

  dist/entries.json   every entry: YAML data + article Markdown + derived fields
  dist/passages.json  passage index: one row per tagged range, sorted canonically
  dist/media.json     media records
"""
from __future__ import annotations

import json
import re

from . import refs
from .common import (DIST, ENTRIES, MEDIA, all_entry_ids, cultures, load_yaml)
from .review import approval_state, last_approval
from .validate import WIKILINK


def load_all() -> list[dict]:
    out = []
    for id_ in all_entry_ids():
        e = load_yaml(ENTRIES / f"{id_}.yaml")
        md = (ENTRIES / f"{id_}.md").read_text() if (ENTRIES / f"{id_}.md").exists() else ""
        e["article"] = md
        e["approval"] = approval_state(e)
        la = last_approval(e)
        e["approved"] = {"by": la["by"], "date": la["date"]} if la else None
        e["regions"] = sorted({cultures()[c]["region"] for c in e.get("cultures") or [] if c in cultures()})
        e["links_out"] = sorted(set(WIKILINK.findall(md)))
        out.append(e)
    return out


def passage_rows(entries: list[dict]) -> list[dict]:
    rows = []
    for e in entries:
        for p in e.get("passages") or []:
            for r in refs.parse(p["ref"]):
                rows.append({
                    "book": r.book, "c1": r.c1, "v1": r.v1, "c2": r.c2, "v2": r.v2,
                    "osis": r.osis(), "display": r.display(),
                    "entry": e["id"], "rel": p["rel"], "disputed": bool(p.get("disputed")),
                    "note": p.get("note"), "_key": r.key(),
                })
    rows.sort(key=lambda x: (x["_key"], x["entry"]))
    for r in rows:
        del r["_key"]
    return rows


def build() -> None:
    DIST.mkdir(exist_ok=True)
    entries = load_all()
    ids = {e["id"] for e in entries}
    backlinks: dict[str, set] = {i: set() for i in ids}
    for e in entries:
        for r in e.get("related") or []:
            if r in backlinks:
                backlinks[r].add(e["id"])
        for l in e["links_out"]:
            if l in backlinks:
                backlinks[l].add(e["id"])
    for e in entries:
        e["backlinks"] = sorted(backlinks[e["id"]] - {e["id"]})
    media = [load_yaml(p) for p in sorted(MEDIA.glob("*.yaml"))]
    rows = passage_rows(entries)
    (DIST / "entries.json").write_text(json.dumps(entries, ensure_ascii=False, indent=1))
    (DIST / "passages.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    (DIST / "media.json").write_text(json.dumps(media, ensure_ascii=False, indent=1))
    print(f"dist/: {len(entries)} entries, {len(rows)} passage rows, {len(media)} media")


def lookup(ref: str) -> list[tuple]:
    """Entries tagged to any range overlapping `ref`."""
    targets = refs.parse(ref)
    hits = []
    for id_ in all_entry_ids():
        e = load_yaml(ENTRIES / f"{id_}.yaml")
        for p in e.get("passages") or []:
            for r in refs.parse(p["ref"]):
                if any(r.overlaps(t) for t in targets):
                    hits.append((r.key(), e["id"], e["title"], r.display(), p["rel"], p.get("disputed"), p.get("note")))
                    break
    hits.sort()
    return hits
