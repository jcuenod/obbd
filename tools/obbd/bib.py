"""Bibliography formatting for the site: Pandoc-style citations -> readable HTML.

    [@george-gilgamesh]             -> (George 2003)
    [@lambert-bwl, pp. 92–95]       -> (Lambert 1960, 92–95)
    [@cos1, 1.105]                  -> (COS 1.105)
    [@cos2, 287]                    -> (COS 2:287)
    [@kai, no. 181]                 -> (KAI 181)
    [@rinap3-1; @rinap4; @anet]     -> (RINAP 3/1; RINAP 4; ANET)
    [see @day-dragon, 12–15]        -> (see Day 1985, 12–15)

Follows SBL Handbook style. Works with a `citation-label` (a standard abbreviation such
as COS, ANET, ABD) are cited by that label, italic unless it abbreviates a series;
everything else is cited author–date. Full references are built from the CSL-YAML in
bibliography/references.yaml.
"""
from __future__ import annotations

import html
import re
from functools import lru_cache

from .common import ROOT, load_yaml

esc = html.escape
BIB_FILE = ROOT / "bibliography" / "references.yaml"
ABBR_FILE = ROOT / "bibliography" / "abbreviations.yaml"
CITE_ITEM = re.compile(r"^(?P<prefix>(?:.*?\s)?)(?P<suppress>-?)@(?P<key>[\w][\w:.#$%&+?<>~/-]*)(?P<rest>.*)$", re.S)


@lru_cache(maxsize=1)
def bibliography() -> dict[str, dict]:
    if not BIB_FILE.exists():
        return {}
    data = load_yaml(BIB_FILE) or {}
    return {r["id"]: r for r in data.get("references") or []}


@lru_cache(maxsize=1)
def abbreviations() -> dict[str, dict[str, str]]:
    """{'series': {full title: abbreviation}, 'journals': {...}} from abbreviations.yaml."""
    data = (load_yaml(ABBR_FILE) if ABBR_FILE.exists() else None) or {}
    return {kind: {full: ab for ab, full in (data.get(kind) or {}).items()} for kind in ("series", "journals")}


def _abbr(kind: str, full: str) -> str:
    """'<abbr title="Writings from the Ancient World">WAW</abbr>', or the escaped full title."""
    ab = abbreviations()[kind].get(full)
    return f'<abbr title="{esc(full)}">{esc(ab)}</abbr>' if ab else esc(full)


# ------------------------------------------------------------------ names

def _given_first(n: dict) -> str:
    if n.get("literal"):
        return n["literal"]
    parts = [n.get("given"), n.get("dropping-particle"), n.get("non-dropping-particle"), n.get("family")]
    s = " ".join(p for p in parts if p)
    return f"{s} {n['suffix']}" if n.get("suffix") else s


def _family_first(n: dict) -> str:
    if n.get("literal"):
        return n["literal"]
    fam = " ".join(p for p in (n.get("non-dropping-particle"), n.get("family")) if p)
    giv = " ".join(p for p in (n.get("given"), n.get("dropping-particle")) if p)
    s = f"{fam}, {giv}" if giv else fam
    return f"{s}, {n['suffix']}" if n.get("suffix") else s


def _family(n: dict) -> str:
    if n.get("literal"):
        return n["literal"]
    return " ".join(p for p in (n.get("non-dropping-particle"), n.get("family")) if p)


def _join(names: list[str]) -> str:
    if len(names) <= 1:
        return "".join(names)
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + ", and " + names[-1]


def _year(r: dict) -> str:
    try:
        return str(r["issued"]["date-parts"][0][0])
    except (KeyError, IndexError, TypeError):
        return (r.get("issued") or {}).get("literal", "n.d.") if isinstance(r.get("issued"), dict) else "n.d."


# ------------------------------------------------------------------ abbreviations (sigla)

def _split_label(label: str) -> tuple[str, str]:
    """'COS 1' -> ('COS', '1'); 'RINAP 3/1' -> ('RINAP', '3/1'); 'ANET' -> ('ANET', '')."""
    m = re.match(r"^(.*?)(?:\s+(\d+(?:/\d+)?))?$", label)
    return m.group(1), m.group(2) or ""


def _is_series(r: dict, base: str) -> bool:
    """SBL italicises abbreviations of titles (ABD, COS, KAI) but not of series (RINAP, SAA):
    a label is a series abbreviation when it is the abbreviation of the record's series."""
    return abbreviations()["series"].get(r.get("collection-title", "")) == base


def siglum_html(key: str) -> str:
    """The citation-label as SBL sets it: '<i>COS</i> 1', 'RINAP 4'."""
    r = bibliography()[key]
    base, vol = _split_label(str(r["citation-label"]))
    b = esc(base) if _is_series(r, base) else f"<i>{esc(base)}</i>"
    return b + (f" {esc(vol)}" if vol else "")


def _siglum_with_locator(key: str, loc: str) -> str:
    """SBL: no comma between abbreviation and locator; volume:page for multivolume works.
        COS 1 + '1.105' -> COS 1.105      COS 2 + '287' -> COS 2:287
        KAI + 'no. 181' -> KAI 181        RINAP 1 + 'no. 35' -> RINAP 1 no. 35"""
    r = bibliography()[key]
    base, vol = _split_label(str(r["citation-label"]))
    b = esc(base) if _is_series(r, base) else f"<i>{esc(base)}</i>"
    if not loc:
        return siglum_html(key)
    if vol:
        if loc.startswith(vol + "."):
            return f"{b} {esc(loc)}"
        if re.match(r"^\d", loc):
            return f"{b} {esc(vol)}:{esc(loc)}"
        return f"{b} {esc(vol)} {esc(loc)}"
    return f"{b} {esc(re.sub(r'^nos?\.\s*', '', loc))}"


# ------------------------------------------------------------------ author-date

def _names_short(r: dict) -> str:
    names = r.get("author") or r.get("editor") or r.get("translator") or []
    fams = [_family(n) for n in names]
    if not fams:
        return str(r.get("title-short") or r.get("title", r["id"]))
    if len(fams) > 3:
        return f"{fams[0]} et al."
    return _join(fams)


def short_label(key: str) -> str | None:
    """Plain-text short form: 'COS 1', 'George 2003', 'King and Stager 2001'."""
    r = bibliography().get(key)
    if not r:
        return None
    if r.get("citation-label"):
        return str(r["citation-label"])
    return f"{_names_short(r)} {_year(r)}"


def sort_key(key: str) -> str:
    r = bibliography().get(key) or {}
    if r.get("citation-label"):
        return str(r["citation-label"]).casefold()
    lead = (r.get("author") or r.get("editor") or r.get("translator") or [{}])[0]
    return f"{_family_first(lead) if lead else r.get('title', key)} {_year(r)}".casefold()


# ------------------------------------------------------------------ full reference

def _dash(s) -> str:
    return str(s).replace("-", "–")


def _title_html(r: dict) -> str:
    t = esc(str(r.get("title", "")).rstrip("."))
    if r.get("type") in ("book", "thesis", "report") or not r.get("container-title"):
        return f"<i>{t}</i>"
    return f"“{t}.”"


def full_html(key: str, year_first: bool | None = None) -> str:
    """An SBL bibliography entry as inline HTML. Works cited author–date put the year
    after the names (SBL author–date reference list); works cited by abbreviation keep
    the year with the publisher (SBL bibliography)."""
    r = bibliography().get(key)
    if not r:
        return esc(key)
    if year_first is None:
        year_first = not r.get("citation-label")
    year = _year(r)
    out: list[str] = []
    authors, editors, trans = r.get("author") or [], r.get("editor") or [], r.get("translator") or []
    lead = authors or editors or trans
    if lead:
        s = _family_first(lead[0])
        rest = [_given_first(n) for n in lead[1:]]
        if len(rest) == 1:
            s += f", and {rest[0]}"
        elif rest:
            s = _join([s] + rest)
        if not authors:
            roles = []
            if editors:
                roles.append("eds." if len(editors) > 1 else "ed.")
            if trans and (not editors or trans == editors):
                roles.append("trans.")
            s += ", " + " and ".join(roles)
        out.append(esc(s.rstrip(".")) + ".")
    elif year_first:
        out.append(_title_html(r) + ".")
    if year_first:
        out.append(esc(year) + ".")
    title = _title_html(r) if lead or not year_first else ""
    cont = r.get("container-title")
    if r.get("type") == "article-journal" and cont:
        vol = f" {esc(str(r['volume']))}" if r.get("volume") else ""
        when = "" if year_first else f" ({esc(year)})"
        pg = (":" if vol and year_first else ": ") + esc(_dash(r["page"])) if r.get("page") else ""
        out.append(f"{title} <i>{_abbr('journals', cont)}</i>{vol}{when}{pg}.".strip())
        return " ".join(out)
    if title:
        out.append(title if title.endswith("”") else title + ".")
    if cont:
        pages = f"Pages {esc(_dash(r['page']))} in " if r.get("page") else "In "
        out.append(f"{pages}<i>{esc(cont)}</i>.")
        if authors and editors:
            out.append(f"Edited by {esc(_join([_given_first(n) for n in editors]))}.")
    if authors and trans:
        out.append(f"Translated by {esc(_join([_given_first(n) for n in trans]))}.")
    if authors and editors and not cont:
        out.append(f"Edited by {esc(_join([_given_first(n) for n in editors]))}.")
    elif not authors and editors and trans and trans != editors:
        out.append(f"Translated by {esc(_join([_given_first(n) for n in trans]))}.")
    if r.get("edition"):
        ed = str(r["edition"])
        out.append(esc(ed if ed.endswith(".") else ed + "."))
    if r.get("volume") and not cont:
        out.append(f"Vol. {esc(str(r['volume']))}.")
    if r.get("number-of-volumes"):
        out.append(f"{esc(str(r['number-of-volumes']))} vols.")
    if r.get("collection-title"):
        out.append(_abbr("series", r["collection-title"]) + (f" {esc(str(r['collection-number']))}" if r.get("collection-number") else "") + ".")
    pub = ": ".join(p for p in (r.get("publisher-place"), r.get("publisher")) if p)
    tail = pub if year_first else ", ".join(p for p in (pub, year) if p)
    if tail:
        out.append(esc(tail) + ".")
    if r.get("note"):
        out.append(esc(str(r["note"])))
    return " ".join(out)


def full_text(key: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", full_html(key)))


# ------------------------------------------------------------------ citations

def parse(body: str) -> list[dict] | None:
    """Parse the inside of a [...] citation; None if it is not one."""
    items = []
    for part in body.split(";"):
        m = CITE_ITEM.match(part.strip())
        if not m:
            return None
        key = m.group("key").rstrip(".,:")
        rest = m.group("rest")
        locator = rest.lstrip(",").strip() if rest.lstrip().startswith(",") else rest.strip()
        locator = re.sub(r"^pp?\.\s*", "", locator)  # SBL gives bare page numbers
        items.append({"key": key, "prefix": m.group("prefix").strip(), "locator": locator,
                      "suppress": bool(m.group("suppress"))})
    return items


def short_html(it: dict, emph=lambda s: s) -> str:
    """One item in SBL form, no parentheses: '<i>COS</i> 1.105', 'George 2003, 23'."""
    r = bibliography()[it["key"]]
    if r.get("citation-label"):
        return _siglum_with_locator(it["key"], it["locator"])
    who = "" if it["suppress"] else esc(_names_short(r)) + " "
    return who + esc(_year(r)) + (", " + emph(esc(it["locator"])) if it["locator"] else "")


def cite_html(items: list[dict], href, used: list[str], emph) -> str:
    """Render parsed items as '(A; B 2003, 23)'. `href(key)` gives the link target;
    `used` collects keys in first-cited order; `emph` renders inline markup."""
    parts = []
    for it in items:
        k = it["key"]
        if k not in used:
            used.append(k)
        pre = emph(esc(it["prefix"])) + " " if it["prefix"] else ""
        if k in bibliography():
            parts.append(f'{pre}<a class="cite" href="{href(k)}" title="{esc(full_text(k))}">{short_html(it, emph)}</a>')
        else:
            loc = ", " + emph(esc(it["locator"])) if it["locator"] else ""
            parts.append(f'{pre}<span class="cite missing" title="not in bibliography/references.yaml">@{esc(k)}</span>{loc}')
    return '<span class="citation">(' + "; ".join(parts) + ")</span>"


def bib_li(k: str, extra: str = "") -> str:
    """One reference-list item: '<li id="ref-cos1"><span class="abbr">COS 1</span> Hallo…</li>'."""
    r = bibliography()[k]
    abbr = f'<span class="abbr">{siglum_html(k)}</span> ' if r.get("citation-label") else ""
    return f'<li id="ref-{esc(k)}">{abbr}{full_html(k)}{extra}</li>'


def works_cited_html(keys: list[str], heading: str = "Works Cited", more=None) -> str:
    """`more(key)`, if given, returns an href to the key in the full bibliography."""
    known = sorted({k for k in keys if k in bibliography()}, key=sort_key)
    if not known:
        return ""
    lis = [bib_li(k, f' <a class="more" href="{more(k)}" title="In the full bibliography, with every entry that cites it">↗</a>' if more else "")
           for k in known]
    return f'<section class="works-cited"><h2 id="works-cited">{esc(heading)}</h2><ul class="bib">{"".join(lis)}</ul></section>'
