"""Local Bible text for checking passage tags: World English Bible (public domain).

Source: https://ebible.org/Scriptures/eng-web_usfm.zip (USFM). `./obbd bible-import ZIPDIR`
parses it into .cache/bible/web.json; `./obbd verse REF` prints the text of a reference.
The WEB uses English versification, matching OBBD's convention.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from . import refs
from .common import CACHE_DIR

USFM_TO_OSIS = {
    "GEN": "Gen", "EXO": "Exod", "LEV": "Lev", "NUM": "Num", "DEU": "Deut", "JOS": "Josh", "JDG": "Judg",
    "RUT": "Ruth", "1SA": "1Sam", "2SA": "2Sam", "1KI": "1Kgs", "2KI": "2Kgs", "1CH": "1Chr", "2CH": "2Chr",
    "EZR": "Ezra", "NEH": "Neh", "EST": "Esth", "JOB": "Job", "PSA": "Ps", "PRO": "Prov", "ECC": "Eccl",
    "SNG": "Song", "ISA": "Isa", "JER": "Jer", "LAM": "Lam", "EZK": "Ezek", "DAN": "Dan", "HOS": "Hos",
    "JOL": "Joel", "AMO": "Amos", "OBA": "Obad", "JON": "Jonah", "MIC": "Mic", "NAM": "Nah", "HAB": "Hab",
    "ZEP": "Zeph", "HAG": "Hag", "ZEC": "Zech", "MAL": "Mal", "TOB": "Tob", "JDT": "Jdt", "ESG": "AddEsth",
    "WIS": "Wis", "SIR": "Sir", "BAR": "Bar", "1MA": "1Macc", "2MA": "2Macc", "1ES": "1Esd", "2ES": "2Esd",
    "MAN": "PrMan", "MAT": "Matt", "MRK": "Mark", "LUK": "Luke", "JHN": "John", "ACT": "Acts", "ROM": "Rom",
    "1CO": "1Cor", "2CO": "2Cor", "GAL": "Gal", "EPH": "Eph", "PHP": "Phil", "COL": "Col", "1TH": "1Thess",
    "2TH": "2Thess", "1TI": "1Tim", "2TI": "2Tim", "TIT": "Titus", "PHM": "Phlm", "HEB": "Heb", "JAS": "Jas",
    "1PE": "1Pet", "2PE": "2Pet", "1JN": "1John", "2JN": "2John", "3JN": "3John", "JUD": "Jude", "REV": "Rev",
}

BIBLE_JSON = CACHE_DIR / "bible" / "web.json"

_NOTE = re.compile(r"\\(f|x|fe)\s.*?\\\1\*", re.S)
_WORD = re.compile(r"\\\+?w\s+([^|\\]*?)(?:\|[^\\]*?)?\\\+?w\*")
_MARK = re.compile(r"\\\+?[a-z0-9]+\*?")


def _clean(s: str) -> str:
    s = _NOTE.sub("", s)
    s = _WORD.sub(r"\1", s)
    s = _MARK.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


def import_usfm(src: Path) -> None:
    data: dict = {}
    for f in sorted(src.glob("*.usfm")):
        text = f.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^\\id\s+(\w+)", text, re.M)
        if not m or m.group(1) not in USFM_TO_OSIS:
            continue
        book = USFM_TO_OSIS[m.group(1)]
        chap = None
        verses: dict = {}
        cur = None
        for line in text.splitlines():
            cm = re.match(r"\\c\s+(\d+)", line)
            if cm:
                chap = int(cm.group(1)); cur = None
                continue
            if chap is None:
                continue
            # a line may contain several \v markers
            parts = re.split(r"\\v\s+(\d+)\S*\s", line)
            head, rest = parts[0], parts[1:]
            if cur and head.strip() and not re.match(r"\\(s\d?|r|d|ms\d?|mr|sp|cl)\b", head):
                verses[cur] += " " + head
            for i in range(0, len(rest), 2):
                cur = (chap, int(rest[i]))
                verses[cur] = rest[i + 1]
        bk = data.setdefault(book, {})
        for (c, v), t in verses.items():
            bk.setdefault(str(c), {})[str(v)] = _clean(t)
    BIBLE_JSON.parent.mkdir(parents=True, exist_ok=True)
    BIBLE_JSON.write_text(json.dumps(data, ensure_ascii=False))
    print(f"imported {len(data)} books -> {BIBLE_JSON}")


@lru_cache(maxsize=1)
def bible() -> dict:
    if not BIBLE_JSON.exists():
        raise SystemExit("No Bible text: run ./obbd bible-import <dir with eng-web USFM files>")
    return json.loads(BIBLE_JSON.read_text())


def text(ref: str, max_verses: int = 400) -> list[tuple[str, str]]:
    """[(label, text)] for every verse in the reference (capped)."""
    out = []
    for r in refs.parse(ref):
        bk = bible().get(r.book)
        if bk is None:
            out.append((r.display(), "[book not in WEB text]"))
            continue
        for c in range(r.c1, r.c2 + 1):
            ch = bk.get(str(c), {})
            vs = sorted(int(v) for v in ch)
            for v in vs:
                if c == r.c1 and r.v1 is not None and v < r.v1:
                    continue
                if c == r.c2 and r.v2 is not None and v > r.v2:
                    continue
                out.append((f"{r.book} {c}:{v}", ch[str(v)]))
                if len(out) >= max_verses:
                    return out
            if r.v1 is not None and c == r.c1 and not ch.get(str(r.v1)):
                out.append((f"{r.book} {c}:{r.v1}", "[verse not found]"))
    return out


def last_verse(book: str, chap: int) -> int | None:
    ch = bible().get(book, {}).get(str(chap))
    return max(int(v) for v in ch) if ch else None
