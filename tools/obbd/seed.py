"""Seed files: compact, hand-written entry definitions that `scaffold` expands.

A seed file (seed/<domain>.yaml) is a YAML list of mappings:

    - id: mesha-stele                  # must exist in seed/master.txt
      title: Mesha Stele               # optional; overrides master title
      aliases: [Moabite Stone]
      cultures: [moabite]
      date: [-850, -830]               # years; negative = BCE; one or two numbers
      circa: true
      scope: >-                        # 1-3 sentences: what the entry is about
        ...
      passages:                        # "REF | REL | note"; REL? = disputed
        - "2Kgs 3:4-27 | event | Mesha's revolt from the Moabite side"
        - "Judg 11:24 | concept? | Chemosh as land-giving god"
      related: [omri, chemosh]         # ids from master.txt
      wikipedia: Mesha Stele           # English Wikipedia title, if any
      image: Mesha stele Louvre        # Commons search phrase, or null
      location: Musée du Louvre, Paris # current holding institution (artifacts)
      author_notes:                    # guidance for the article writer
        - Discuss the reading bt[d]wd in line 31 ...
      sources_to_check:                # standard editions/translations to verify
        - KAI 181
        - COS 2.23
"""
from __future__ import annotations

from pathlib import Path

import yaml

from . import refs
from .common import cultures, master, relations, SEED

ALLOWED_KEYS = {
    "id", "title", "aliases", "cultures", "corpus", "date", "circa", "scope", "passages",
    "related", "wikipedia", "image", "location", "author_notes", "sources_to_check",
}


def parse_passage(s: str) -> dict:
    parts = [p.strip() for p in s.split("|")]
    if len(parts) < 2:
        raise ValueError(f"passage needs 'REF | REL[ | note]': {s!r}")
    ref, rel = parts[0], parts[1]
    note = " | ".join(parts[2:]).strip() or None
    disputed = rel.endswith("?")
    rel = rel.rstrip("?")
    out = {"ref": ref, "rel": rel}
    if disputed:
        out["disputed"] = True
    if note:
        out["note"] = note
    return out


def load_seed_files(paths: list[Path] | None = None) -> dict[str, dict]:
    paths = paths or sorted(SEED.glob("*.yaml"))
    out: dict[str, dict] = {}
    for p in paths:
        data = yaml.safe_load(p.read_text()) or []
        for e in data:
            e["_file"] = p.name
            out[e["id"]] = e
    return out


def check_seed_entry(e: dict) -> list[str]:
    errs = []
    m = master()
    id_ = e.get("id")
    if id_ not in m:
        return [f"{id_}: id not in master.txt"]
    if e.get("corpus") not in (None, "ot", "nt", "both"):
        errs.append(f"{id_}: corpus must be ot, nt or both")
    extra = set(e) - ALLOWED_KEYS - {"_file"}
    if extra:
        errs.append(f"{id_}: unknown keys {sorted(extra)}")
    if not e.get("scope"):
        errs.append(f"{id_}: missing scope")
    for c in e.get("cultures") or []:
        if c not in cultures():
            errs.append(f"{id_}: unknown culture {c!r}")
    d = e.get("date")
    if d is not None:
        if not (isinstance(d, list) and 1 <= len(d) <= 2 and all(isinstance(x, int) for x in d)):
            errs.append(f"{id_}: date must be [year] or [from, to] integers")
        elif len(d) == 2 and d[0] > d[1]:
            errs.append(f"{id_}: date range runs backwards")
    rels = relations()
    ps = e.get("passages") or []
    if not ps:
        errs.append(f"{id_}: no passages")
    for key in ("aliases", "author_notes", "sources_to_check", "related", "cultures"):
        for item in e.get(key) or []:
            if not isinstance(item, str):
                errs.append(f"{id_}: {key} item is not a string (quote it; an unquoted ': ' makes a mapping): {item!r}"[:200])
    for k in ("scope", "wikipedia", "image", "location", "title"):
        if e.get(k) is not None and not isinstance(e[k], str):
            errs.append(f"{id_}: {k} must be a string")
    for s in ps:
        if not isinstance(s, str):
            errs.append(f"{id_}: passage is not a string (quote it; an unquoted ': ' makes a mapping): {s!r}"[:200])
            continue
        try:
            p = parse_passage(s)
        except ValueError as ex:
            errs.append(f"{id_}: {ex}")
            continue
        if p["rel"] not in rels:
            errs.append(f"{id_}: unknown relation {p['rel']!r} in {s!r}")
        try:
            refs.parse(p["ref"])
        except refs.RefError as ex:
            errs.append(f"{id_}: {ex}")
    for r in e.get("related") or []:
        if r not in m:
            errs.append(f"{id_}: related id {r!r} not in master.txt")
        if r == id_:
            errs.append(f"{id_}: relates to itself")
    return errs


def check_files(paths: list[Path]) -> int:
    m = master()
    n_err = 0
    seen: dict[str, str] = {}
    for p in paths:
        try:
            data = yaml.safe_load(p.read_text()) or []
        except yaml.YAMLError as ex:
            print(f"{p.name}: YAML error: {ex}")
            n_err += 1
            continue
        domain = p.stem
        expected = {k for k, v in m.items() if v["domain"] == domain}
        got = set()
        for e in data:
            if not isinstance(e, dict) or "id" not in e:
                print(f"{p.name}: item without id: {str(e)[:80]}")
                n_err += 1
                continue
            if e["id"] in seen:
                print(f"{p.name}: {e['id']} duplicated (also in {seen[e['id']]})")
                n_err += 1
            seen[e["id"]] = p.name
            got.add(e["id"])
            for err in check_seed_entry(e):
                print(f"{p.name}: {err}")
                n_err += 1
        if expected:
            missing = expected - got
            if missing:
                print(f"{p.name}: {len(missing)} master ids not yet seeded: {', '.join(sorted(missing))}")
        print(f"{p.name}: {len(got)} entries checked")
    return n_err
