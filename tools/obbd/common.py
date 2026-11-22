"""Shared loading/saving helpers."""
from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
ENTRIES = ROOT / "entries"
MEDIA = ROOT / "media"
SEED = ROOT / "seed"
VOCAB = ROOT / "vocab"
DIST = ROOT / "dist"
CACHE_DIR = ROOT / ".cache"

SCHEMA_HEADER = "# yaml-language-server: $schema=../schema/{name}.schema.json\n"


class _Dumper(yaml.SafeDumper):
    """YAML dumper that keeps key order, uses block style, and folds long text."""


def _str_rep(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    if len(data) > 88:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=">")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_Dumper.add_representer(str, _str_rep)


def _list_rep(dumper, data):
    # short lists of scalars inline: [a, b, c]
    flow = all(isinstance(x, (str, int, float)) and len(str(x)) < 40 for x in data) and len(data) <= 8
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=flow)


_Dumper.add_representer(list, _list_rep)


def dump_yaml(data, schema: str | None = None) -> str:
    body = yaml.dump(data, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=88)
    return (SCHEMA_HEADER.format(name=schema) if schema else "") + body


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text())


@lru_cache(maxsize=None)
def vocab(name: str) -> dict:
    return load_yaml(VOCAB / f"{name}.yaml")


def entry_types() -> dict:
    return vocab("entry-types")["types"]


def entry_corpus(e: dict) -> str:
    """Which part of the Bible an entry mainly bears on: 'ot', 'nt' or 'both'.

    An explicit `corpus` in the entry YAML wins. Otherwise it is inferred from the
    passage tags (deuterocanonical and pseudepigraphal tags are not counted): a side
    with at least twice as many tags as the other wins; anything closer is 'both'.
    Entries with no OT or NT tags default to 'ot'.
    """
    if e.get("corpus"):
        return e["corpus"]
    books = {b["id"]: b["corpus"] for b in vocab("books")["books"]}
    ot = nt = 0
    for p in e.get("passages") or []:
        c = books.get(p["ref"].split()[0])
        ot += c == "ot"
        nt += c == "nt"
    if nt == 0:
        return "ot"
    if ot == 0 or nt >= 2 * ot:
        return "nt"
    if ot >= 2 * nt:
        return "ot"
    return "both"


def entry_sections(e: dict) -> list[str]:
    """The article headings for an entry: its type's sections, with `{slot}` headings
    resolved by corpus (vocab/entry-types.yaml `corpus_headings`)."""
    v = vocab("entry-types")
    slots = v.get("corpus_headings", {}).get(entry_corpus(e), {})
    return [slots.get(s[1:-1], s) if s.startswith("{") and s.endswith("}") else s
            for s in v["types"][e["type"]]["sections"]]


def relations() -> dict:
    return vocab("relations")["relations"]


def cultures() -> dict:
    return vocab("cultures")["cultures"]


def contributors() -> dict:
    data = load_yaml(ROOT / "contributors.yaml") or {}
    return {c["id"]: c for c in data.get("contributors", [])}


_MASTER_LINE = re.compile(r"^([a-z0-9-]+)\s*\|\s*([a-z]+)\s*\|\s*(.+?)\s*\|\s*(.*)$")


@lru_cache(maxsize=1)
def master() -> dict[str, dict]:
    """Parse seed/master.txt -> {id: {id,type,title,hints,domain}} preserving order."""
    out: dict[str, dict] = {}
    domain = None
    for n, line in enumerate((SEED / "master.txt").read_text().splitlines(), 1):
        if line.startswith("## "):
            domain = line[3:].strip()
            continue
        if not line.strip() or line.startswith("#"):
            continue
        m = _MASTER_LINE.match(line)
        if not m:
            raise ValueError(f"master.txt:{n}: cannot parse {line!r}")
        id_, type_, title, hints = m.groups()
        if id_ in out:
            raise ValueError(f"master.txt:{n}: duplicate id {id_}")
        out[id_] = {"id": id_, "type": type_, "title": title, "hints": hints, "domain": domain}
    return out


def entry_paths(id_: str) -> tuple[Path, Path]:
    return ENTRIES / f"{id_}.yaml", ENTRIES / f"{id_}.md"


def all_entry_ids() -> list[str]:
    return sorted(p.stem for p in ENTRIES.glob("*.yaml"))


def load_entry(id_: str) -> dict:
    return load_yaml(ENTRIES / f"{id_}.yaml")


def save_entry(entry: dict) -> None:
    (ENTRIES / f"{entry['id']}.yaml").write_text(dump_yaml(entry, "entry"))


def article_hash(id_: str) -> str | None:
    """sha256 of the article text, normalised (LF newlines, no trailing spaces)."""
    p = ENTRIES / f"{id_}.md"
    if not p.exists():
        return None
    text = p.read_text().replace("\r\n", "\n")
    text = "\n".join(l.rstrip() for l in text.split("\n")).strip() + "\n"
    return hashlib.sha256(text.encode()).hexdigest()


def year_display(y: int) -> str:
    return f"{-y} BCE" if y < 0 else f"{y} CE"


def date_display(d: dict | None) -> str | None:
    if not d:
        return None
    c = "c. " if d.get("circa") else ""
    a, b = d.get("from"), d.get("to")
    if a is None:
        return None
    if b is None or a == b:
        return c + year_display(a)
    if (a < 0) == (b < 0):
        era = "BCE" if a < 0 else "CE"
        return f"{c}{abs(a)}–{abs(b)} {era}"
    return f"{c}{year_display(a)}–{year_display(b)}"
