"""Validate entries, media records, and cross-references."""
from __future__ import annotations

import re

from . import refs
from .common import (ENTRIES, MEDIA, ROOT, all_entry_ids, contributors, cultures,
                     entry_types, load_yaml, relations)
from .review import STATUSES, approval_state

WIKILINK = re.compile(r"!?\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
CITATION = re.compile(r"\[@([A-Za-z0-9_:.-]+)")

FREE_LICENSES = {"CC0-1.0", "PD", "CC-BY-1.0", "CC-BY-2.0", "CC-BY-2.5", "CC-BY-3.0", "CC-BY-4.0",
                 "CC-BY-SA-1.0", "CC-BY-SA-2.0", "CC-BY-SA-2.5", "CC-BY-SA-3.0", "CC-BY-SA-4.0",
                 "CC-BY-SA-2.0-DE", "CC-BY-SA-3.0-DE", "CC-BY-2.0-DE", "CC-BY-3.0-DE", "FAL", "OGL"}
# GFDL is deliberately absent: it requires shipping the full license text with every
# copy, which a website cannot reasonably do. Files dual-licensed GFDL + CC are recorded
# under their CC license instead (see media.file_info).


def load_bib_keys() -> set[str]:
    p = ROOT / "bibliography" / "references.yaml"
    if not p.exists():
        return set()
    data = load_yaml(p) or {}
    return {r["id"] for r in data.get("references") or []}


def validate(strict: bool = False) -> int:
    errors: list[str] = []
    warnings: list[str] = []
    ids = set(all_entry_ids())
    media_ids = {p.stem for p in MEDIA.glob("*.yaml")}
    media_files = {p.name for p in MEDIA.iterdir() if p.suffix.lower() != ".yaml"} if MEDIA.exists() else set()
    people = contributors()
    types = entry_types()
    rels = relations()
    cults = cultures()
    bib = load_bib_keys()
    from .bib import abbreviations, bibliography
    for key, r in bibliography().items():
        checks = [("collection-title", "series")]
        if r.get("type") == "article-journal":  # a chapter's container is a book, not abbreviated
            checks.append(("container-title", "journals"))
        for field, kind in checks:
            t = r.get(field)
            if t and t not in abbreviations()[kind]:
                warnings.append(f"bibliography/references.yaml: {key}: {field} {t!r} has no abbreviation in bibliography/abbreviations.yaml")
    try:
        import json
        import jsonschema
        schemas = {n: jsonschema.Draft202012Validator(json.loads((ROOT / "schema" / f"{n}.schema.json").read_text()))
                   for n in ("entry", "media")}
    except ImportError:
        schemas = {}

    for id_ in sorted(ids):
        e = load_yaml(ENTRIES / f"{id_}.yaml")
        where = f"entries/{id_}.yaml"
        if "entry" in schemas:
            for err in schemas["entry"].iter_errors(e):
                errors.append(f"{where}: schema: {'/'.join(map(str, err.path))}: {err.message[:160]}")
        if e.get("id") != id_:
            errors.append(f"{where}: id {e.get('id')!r} does not match filename")
        for k in ("title", "type", "scope", "status"):
            if not e.get(k):
                errors.append(f"{where}: missing {k}")
        if e.get("type") not in types:
            errors.append(f"{where}: unknown type {e.get('type')!r}")
        if e.get("status") not in STATUSES:
            errors.append(f"{where}: unknown status {e.get('status')!r}")
        for c in e.get("cultures") or []:
            if c not in cults:
                errors.append(f"{where}: unknown culture {c!r}")
        for p in e.get("passages") or []:
            if p.get("rel") not in rels:
                errors.append(f"{where}: unknown rel {p.get('rel')!r}")
            try:
                refs.parse(p.get("ref", ""))
            except refs.RefError as ex:
                errors.append(f"{where}: {ex}")
        if not e.get("passages"):
            warnings.append(f"{where}: no passages tagged")
        for r in e.get("related") or []:
            if r not in ids:
                errors.append(f"{where}: related entry {r!r} does not exist")
        for m in e.get("media") or []:
            if m.get("id") not in media_ids:
                errors.append(f"{where}: media {m.get('id')!r} has no record in media/")
        for h in e.get("history") or []:
            if h.get("by") not in people:
                errors.append(f"{where}: history references unknown contributor {h.get('by')!r}")
        for role in ("authors", "reviewers"):
            for who in (e.get("credits") or {}).get(role) or []:
                if who not in people:
                    errors.append(f"{where}: credits.{role} has unknown contributor {who!r}")
        st = approval_state(e)
        if e.get("status") == "approved" and st != "current":
            (errors if strict else warnings).append(f"{where}: approval is {st}; re-review needed")
        if types.get(e.get("type"), {}).get("image_expected") and not e.get("media"):
            warnings.append(f"{where}: {e['type']} entry has no image")

        md = ENTRIES / f"{id_}.md"
        if not md.exists():
            errors.append(f"entries/{id_}.md missing")
            continue
        text = re.sub(r"<!--.*?-->", "", md.read_text(), flags=re.S)  # ignore template guidance comments
        text = re.sub(r"```.*?```", "", text, flags=re.S)  # ignore code blocks
        text = re.sub(r"`[^`\n]*`", "", text)  # ignore inline code
        for target in WIKILINK.findall(text):
            t = target.strip()
            if t not in ids and t not in media_files and t not in media_ids:
                errors.append(f"entries/{id_}.md: broken link [[{t}]]")
        for key in CITATION.findall(text):
            if key not in bib:
                errors.append(f"entries/{id_}.md: citation @{key} not in bibliography/references.yaml")

    for mid in sorted(media_ids):
        m = load_yaml(MEDIA / f"{mid}.yaml")
        where = f"media/{mid}.yaml"
        if "media" in schemas:
            for err in schemas["media"].iter_errors(m):
                errors.append(f"{where}: schema: {'/'.join(map(str, err.path))}: {err.message[:160]}")
        if m.get("id") != mid:
            errors.append(f"{where}: id mismatch")
        if m.get("file") not in media_files:
            errors.append(f"{where}: file {m.get('file')!r} missing")
        lic = (m.get("license") or {}).get("id")
        if lic not in FREE_LICENSES:
            errors.append(f"{where}: license {lic!r} is not on the approved list")
        if not m.get("attribution"):
            errors.append(f"{where}: missing attribution string")
        for d in m.get("depicts") or []:
            if d not in ids:
                errors.append(f"{where}: depicts unknown entry {d!r}")

    for w in warnings:
        print("warning:", w)
    for e in errors:
        print("ERROR:", e)
    print(f"{len(ids)} entries, {len(media_ids)} media records: {len(errors)} errors, {len(warnings)} warnings")
    return len(errors)
