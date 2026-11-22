"""Scripture reference parsing.

A reference string names one book followed by one or more ranges:

    "2Kgs 18-19"            whole chapters 18-19
    "2Kgs 18:13-19:37"      verse range across chapters
    "Exod 20:24"            single verse
    "Exod 25:9, 40"         comma: further verses in the same chapter
    "Ezek 14:14, 20; 28:3"  semicolon: new chapter (or chapter:verse) context
    "Obad 10-14"            single-chapter books take verse numbers directly
    "Ps 23"                 whole chapter

Book IDs are OSIS IDs (see vocab/books.yaml). A few common alternates
("1 Kgs", "Qoh", "Cant") are normalised. Each parsed range is
(book, c1, v1, c2, v2) with v1/v2 = None for whole-chapter ranges.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]

ALIASES = {
    "Qoh": "Eccl", "Cant": "Song", "Psa": "Ps", "Pss": "Ps", "Jon": "Jonah",
    "Phm": "Phlm", "Jas": "Jas", "Sirach": "Sir", "Ecclus": "Sir",
}


@lru_cache(maxsize=1)
def books() -> dict[str, dict]:
    data = yaml.safe_load((ROOT / "vocab" / "books.yaml").read_text())
    out = {}
    for i, b in enumerate(data["books"]):
        b = dict(b, order=i)
        out[b["id"]] = b
    return out


def normalise_book(raw: str) -> str | None:
    key = raw.replace(" ", "").replace(".", "")
    key = ALIASES.get(key, key)
    bk = books()
    if key in bk:
        return key
    # case-insensitive fallback, also matching SBL abbreviations
    for b in bk.values():
        if key.lower() in (b["id"].lower(), b["sbl"].replace(" ", "").lower()):
            return b["id"]
    return None


@dataclass(frozen=True)
class Range:
    book: str
    c1: int
    v1: int | None
    c2: int
    v2: int | None

    def key(self) -> tuple:
        o = books()[self.book]["order"]
        return (o, self.c1, self.v1 or 0, self.c2, self.v2 or 999)

    def contains(self, book: str, c: int, v: int | None = None) -> bool:
        if book != self.book:
            return False
        start = (self.c1, self.v1 or 0)
        end = (self.c2, self.v2 if self.v2 is not None else 10_000)
        if v is None:
            return self.c1 <= c <= self.c2
        return start <= (c, v) <= end

    def overlaps(self, other: "Range") -> bool:
        if other.book != self.book:
            return False
        a0, a1 = (self.c1, self.v1 or 0), (self.c2, self.v2 if self.v2 is not None else 10_000)
        b0, b1 = (other.c1, other.v1 or 0), (other.c2, other.v2 if other.v2 is not None else 10_000)
        return a0 <= b1 and b0 <= a1

    def osis(self) -> str:
        def pt(c, v):
            return f"{self.book}.{c}" + (f".{v}" if v is not None else "")
        a, b = pt(self.c1, self.v1), pt(self.c2, self.v2)
        return a if a == b else f"{a}-{b}"

    def display(self) -> str:
        b = books()[self.book]
        single = b["chapters"] == 1
        def pt(c, v):
            if single and v is not None:
                return str(v)
            return f"{c}" + (f":{v}" if v is not None else "")
        start = pt(self.c1, self.v1)
        if (self.c1, self.v1) == (self.c2, self.v2):
            return f"{b['sbl']} {start}"
        if self.c1 == self.c2 and self.v1 is not None:
            return f"{b['sbl']} {start}–{self.v2}"
        return f"{b['sbl']} {start}–{pt(self.c2, self.v2)}"


class RefError(ValueError):
    pass


_BOOK_RE = re.compile(r"^\s*((?:[1-4]\s?)?[A-Za-z]+)\.?\s+(.+?)\s*$")
_PT = r"(\d+)(?::(\d+))?"
_RANGE_RE = re.compile(rf"^{_PT}(?:\s*[-–]\s*{_PT})?[a-z]?$")


def parse(ref: str) -> list[Range]:
    m = _BOOK_RE.match(ref)
    if not m:
        raise RefError(f"cannot parse reference {ref!r}")
    book = normalise_book(m.group(1))
    if not book:
        raise RefError(f"unknown book {m.group(1)!r} in {ref!r}")
    info = books()[book]
    single = info["chapters"] == 1
    out: list[Range] = []
    chapter_ctx: int | None = None
    for group in m.group(2).split(";"):
        group = group.strip()
        if not group:
            continue
        verse_ctx = False  # inside a group, bare numbers after a comma are verses
        for part in group.split(","):
            part = part.strip().rstrip("abcdef")
            pm = _RANGE_RE.match(part)
            if not pm:
                raise RefError(f"cannot parse segment {part!r} in {ref!r}")
            a, av, b, bv = pm.groups()
            a = int(a)
            av = int(av) if av else None
            b = int(b) if b else None
            bv = int(bv) if bv else None
            if single and av is None:
                # "Obad 10-14": numbers are verses in chapter 1
                r = Range(book, 1, a, 1, b if b is not None else a)
            elif verse_ctx and av is None and chapter_ctx is not None:
                # "25:9, 40" -> 40 is a verse of chapter 25; "25:9, 40-42" likewise
                if bv is not None:
                    r = Range(book, chapter_ctx, a, b, bv)
                else:
                    r = Range(book, chapter_ctx, a, chapter_ctx, b if b is not None else a)
            elif av is None:
                # chapter or chapter range
                r = Range(book, a, None, b if b is not None else a, None)
            else:
                if b is None:
                    r = Range(book, a, av, a, av)
                elif bv is None:
                    r = Range(book, a, av, a, b)  # 18:13-37
                else:
                    r = Range(book, a, av, b, bv)  # 18:13-19:37
            for c in (r.c1, r.c2):
                if not 1 <= c <= info["chapters"]:
                    raise RefError(f"{book} has no chapter {c} ({ref!r})")
            if (r.c1, r.v1 or 0) > (r.c2, r.v2 if r.v2 is not None else 10_000):
                raise RefError(f"range runs backwards in {ref!r}")
            out.append(r)
            chapter_ctx = r.c2
            verse_ctx = r.v2 is not None
    if not out:
        raise RefError(f"empty reference {ref!r}")
    return out


def display(ref: str) -> str:
    """Canonical SBL-style display string for a reference string."""
    ranges = parse(ref)
    first = ranges[0]
    parts = [first.display()]
    prev = first
    sbl = books()[first.book]["sbl"] + " "
    for r in ranges[1:]:
        d = r.display()[len(sbl):]
        if r.c1 == prev.c2 and r.v1 is not None and prev.v2 is not None and r.c1 == r.c2:
            # same chapter: drop the chapter
            d = d.split(":", 1)[1] if ":" in d else d
            parts.append(", " + d)
        else:
            parts.append("; " + d)
        prev = r
    return "".join(parts)


if __name__ == "__main__":
    import sys
    for s in sys.argv[1:]:
        try:
            rs = parse(s)
            print(f"{s!r:32} -> {display(s):32} {[r.osis() for r in rs]}")
        except RefError as e:
            print(f"{s!r:32} !! {e}")
