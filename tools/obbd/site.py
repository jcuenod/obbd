"""Static HTML viewer for the dictionary (works from file:// or any static server).

  ./obbd site            -> dist/site/index.html (+ entry/, bible/, images.html, thumbs/)
  ./obbd serve [--port]  -> builds, then serves the repo at http://localhost:PORT/dist/site/

Renders entries in any state: placeholder entries show their scope, the
"content ideas" (author notes, section guidance, sources to check) and all
structured data; written articles are rendered from Markdown.
"""
from __future__ import annotations

import html
import json
import os
import re
from collections import defaultdict
from pathlib import Path

from . import bib, refs
from .common import (DIST, ENTRIES, MEDIA, ROOT, all_entry_ids, contributors, cultures, entry_sections,
                     entry_types, load_yaml, relations)
from .review import approval_state

SITE = DIST / "site"
THUMB = 480
esc = html.escape


# ------------------------------------------------------------------ markdown

# Citations rendered on the current page, in first-cited order (reset per page with
# start_citations(); listed by works_cited()).
_CITED: list[str] = []
CITE_TOKEN = r"\[[^\]\[]*@[^\]\[]*\](?!\()"


def start_citations() -> None:
    _CITED.clear()


def works_cited() -> str:
    return bib.works_cited_html(_CITED)


def _cite(tok: str) -> str:
    items = bib.parse(tok[1:-1])
    if items is None:
        return _emph(esc(tok))
    return bib.cite_html(items, lambda k: f"#ref-{k}", _CITED, _emph)


def _bib_item(txt: str, link) -> str | None:
    """A list item that opens with a single citation ('[@ael]: Translates…') is a
    bibliography line: show the full reference, then the annotation."""
    m = re.match(CITE_TOKEN, txt)
    items = bib.parse(m.group(0)[1:-1]) if m else None
    if not items or len(items) != 1 or items[0]["prefix"] or items[0]["key"] not in bib.bibliography():
        return None
    it = items[0]
    if it["key"] not in _CITED:
        _CITED.append(it["key"])
    rest = re.sub(r"^\s*[:,;—–-]?\s*", "", txt[m.end():])
    if rest and rest[0].islower() and not re.match(r"^(pp?|nos?|vols?|cols?|esp|cf)\.", rest):
        rest = rest[0].upper() + rest[1:]
    note = ""
    if it["locator"]:
        sig = bib.bibliography()[it["key"]].get("citation-label")
        note = f"See {bib.short_html(it, _emph) if sig else _inline(it['locator'], link)}."
    note = " ".join(x for x in (note, _inline(rest, link) if rest else "") if x)
    return (f'<span class="ref">{bib.full_html(it["key"])}</span>'
            + (f'<span class="annot">{note}</span>' if note else ""))


def _inline(s: str, link) -> str:
    out = []
    pos = 0
    pat = re.compile(rf"(`[^`]+`)|(!?\[\[[^\]]+\]\])|({CITE_TOKEN})|(\[[^\]]+\]\([^)]+\))")
    for m in pat.finditer(s):
        out.append(_emph(esc(s[pos:m.start()])))
        tok = m.group(0)
        if m.group(1):
            out.append(f"<code>{esc(tok[1:-1])}</code>")
        elif m.group(2):
            embed = tok.startswith("!")
            inner = tok.strip("!")[2:-2]
            target, _, label = inner.partition("|")
            target = target.split("#")[0].strip()
            out.append(link(target, label.strip() or None, embed))
        elif m.group(3):
            out.append(_cite(tok))
        else:
            mm = re.match(r"\[([^\]]+)\]\(([^)]+)\)", tok)
            out.append(f'<a href="{esc(mm.group(2))}">{_emph(esc(mm.group(1)))}</a>')
        pos = m.end()
    out.append(_emph(esc(s[pos:])))
    return "".join(out)


def _emph(s: str) -> str:
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"<em>\1</em>", s)
    return s


def render_md(text: str, link) -> str:
    """Small Markdown renderer for OBBD articles: headings, paragraphs, nested lists,
    Obsidian callouts, blockquotes, HTML comments (shown as writer guidance)."""
    text = re.sub(r"<!--(.*?)-->", lambda m: "\n\x00GUIDE " + m.group(1).strip().replace("\n", " ") + "\n", text, flags=re.S)
    lines = text.split("\n")
    out: list[str] = []
    i = 0

    def para(buf):
        if buf:
            out.append("<p>" + _inline(" ".join(buf), link) + "</p>")

    def render_list(block):
        # block: list of (indent, text)
        html_out, stack = [], []
        for ind, txt in block:
            while stack and ind < stack[-1]:
                html_out.append("</li></ul>"); stack.pop()
            entry = _bib_item(txt, link)
            li = '<li class="bib-entry">' if entry else "<li>"
            if not stack or ind > stack[-1]:
                html_out.append("<ul>" + li); stack.append(ind)
            else:
                html_out.append("</li>" + li)
            html_out.append(entry or _inline(txt, link))
        while stack:
            html_out.append("</li></ul>"); stack.pop()
        return "".join(html_out)

    buf: list[str] = []
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("\x00GUIDE "):
            para(buf); buf = []
            out.append(f'<div class="guide">{_inline(ln[7:], link)}</div>')
            i += 1; continue
        m = re.match(r"^(#{1,6})\s+(.*)", ln)
        if m:
            para(buf); buf = []
            lvl = min(len(m.group(1)) + 0, 6)
            hid = re.sub(r"[^a-z0-9]+", "-", m.group(2).lower()).strip("-")
            out.append(f'<h{lvl} id="{hid}">{_inline(m.group(2), link)}</h{lvl}>')
            i += 1; continue
        if ln.startswith(">"):
            para(buf); buf = []
            block = []
            while i < len(lines) and lines[i].startswith(">"):
                block.append(lines[i][1:].lstrip(" ") if lines[i] != ">" else "")
                i += 1
            cm = re.match(r"\[!(\w+)\][+-]?\s*(.*)", block[0]) if block else None
            inner = render_md("\n".join(block[1:] if cm else block), link)
            if cm:
                kind = cm.group(1).lower()
                title = _inline(cm.group(2), link) if cm.group(2) else kind.title()
                out.append(f'<div class="callout callout-{esc(kind)}"><div class="callout-title">{title}</div>{inner}</div>')
            else:
                out.append(f"<blockquote>{inner}</blockquote>")
            continue
        lm = re.match(r"^(\s*)[-*]\s+(.*)", ln)
        if lm:
            para(buf); buf = []
            block = []
            while i < len(lines):
                lm = re.match(r"^(\s*)[-*]\s+(.*)", lines[i])
                if lm:
                    block.append((len(lm.group(1)), lm.group(2)))
                elif lines[i].strip() and block and lines[i].startswith("  "):
                    ind, t = block[-1]; block[-1] = (ind, t + " " + lines[i].strip())
                else:
                    break
                i += 1
            out.append(render_list(block))
            continue
        if not ln.strip():
            para(buf); buf = []
        else:
            buf.append(ln.strip())
        i += 1
    para(buf)
    return "\n".join(out)


# ------------------------------------------------------------------ helpers

_BIB_RULES = [
    (r"^COS\s*([1-4])\b", "cos{0}"), (r"^ANET\b", "anet"), (r"^ANEP\b", "anep"), (r"^KAI\b", "kai"),
    (r"^TAD\b", "tad"), (r"^(KTU|CAT)\b", "ktu3"), (r"^AEL\b", "ael"), (r"^DDD\b", "ddd"), (r"^NEAEHL\b", "neaehl"),
    (r"^ABD\b", "abd"), (r"^ABC\b", "abc"), (r"^RIMA\s*([23])\b", "rima{0}"), (r"^RINAP\s*(1|4)\b", "rinap{0}"),
    (r"^RINAP\s*3/1\b", "rinap3-1"), (r"^SAA\s*(2|9)\b", "saa{0}"),
    (r"Context of Scripture", None), (r"Roth,? Law Collections", "roth-law"), (r"Moran,? (The )?Amarna", "moran-amarna"),
    (r"Lichtheim", "ael"), (r"Horowitz,? Mesopotamian Cosmic", "horowitz-cosmic-geography"),
    (r"Lambert,? Babylonian Creation", "lambert-bcm"), (r"Lambert,? Babylonian Wisdom", "lambert-bwl"),
    (r"George,? The Babylonian Gilgamesh", "george-gilgamesh"), (r"Atra-?[hḫ]as[iī]s", "lambert-millard-atrahasis"),
    (r"Hurowitz,? I Have Built", "hurowitz-exalted-house"), (r"Mettinger,? No Graven", "mettinger-no-graven-image"),
    (r"Day,? God's Conflict", "day-dragon"), (r"Keel and Uehlinger|Keel & Uehlinger", "keel-uehlinger-ggig"),
    (r"Nissinen,? Prophets and Prophecy", "nissinen-prophets"), (r"Livingstone,? Hemerologies", "livingstone-hemerologies"),
    (r"Walker and Dick|Walker & Dick", "walker-dick-induction"), (r"Hallo,? .New Moons", "hallo-new-moons-sabbaths"),
    (r"Hebrew Inscriptions", "dobbs-allsopp-hebrew-inscriptions"), (r"Echoes from the Past", "ahituv-echoes"),
    (r"Corpus of West Semitic Stamp Seals", "avigad-sass-wsss"), (r"Parker,? Ugaritic Narrative", "parker-unp"),
    (r"Beckman,? Hittite Diplomatic", "beckman-hdt"), (r"Glassner", "glassner-chronicles"), (r"Grayson,? Assyrian and Babylonian Chronicles", "abc"),
]


def citekey_for(src: str) -> str | None:
    for pat, key in _BIB_RULES:
        m = re.search(pat, src)
        if m and key:
            return key.format(*m.groups()) if "{0}" in key else key
    return None


CSS = r"""
:root{
  --bg:#f7f4ee;--panel:#fffdf9;--ink:#1f1c18;--muted:#6d665c;--faint:#9a9286;--line:#e3ddd2;
  --accent:#8a3b12;--accent-soft:#f3e4d8;--link:#7a3410;--chip:#efe9df;--warn:#9a5b00;--warn-soft:#fbf0dc;
  --ok:#2f6b3a;--ok-soft:#e3f0e3;--bad:#9b2c2c;--guide:#f1efe9;--shadow:0 1px 2px rgba(40,30,20,.06),0 4px 14px rgba(40,30,20,.05);
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,serif;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
  color-scheme:light;
}
@media (prefers-color-scheme:dark){:root{
  --bg:#171512;--panel:#201d19;--ink:#ece6dc;--muted:#a59d90;--faint:#7c7569;--line:#38322b;
  --accent:#e0915f;--accent-soft:#3a2a1f;--link:#eba778;--chip:#2c2722;--warn:#e3b05a;--warn-soft:#3a2f1c;
  --ok:#8fcf98;--ok-soft:#1f3322;--bad:#f08b8b;--guide:#26231f;--shadow:none;color-scheme:dark}}
*{box-sizing:border-box}
html{font-size:16px}
body{margin:0;background:var(--bg);color:var(--ink);font:1rem/1.6 var(--serif)}
a{color:var(--link);text-decoration-thickness:1px;text-underline-offset:2px}
a:hover{text-decoration-thickness:2px}
img{max-width:100%;display:block}
.wrap{max-width:1180px;margin:0 auto;padding:0 clamp(16px,4vw,40px)}
header.top{border-bottom:1px solid var(--line);background:var(--panel)}
header.top .wrap{display:flex;gap:24px;align-items:center;flex-wrap:wrap;padding-block:14px}
.brand{font:600 1.15rem var(--serif);color:var(--ink);text-decoration:none;letter-spacing:.01em}
.brand small{display:block;font:500 .72rem var(--sans);color:var(--muted);letter-spacing:.06em;text-transform:uppercase}
nav.main{display:flex;gap:18px;font:500 .9rem var(--sans);flex-wrap:wrap}
nav.main a{color:var(--muted);text-decoration:none}nav.main a:hover,nav.main a.on{color:var(--ink)}
main{padding-block:28px 64px}
h1,h2,h3{font-family:var(--serif);font-weight:600;line-height:1.25}
h1{font-size:clamp(1.7rem,3.4vw,2.4rem);margin:.1em 0 .25em}
h2{font-size:1.3rem;margin:2em 0 .6em;padding-bottom:.3em;border-bottom:1px solid var(--line)}
h3{font-size:1.08rem;margin:1.6em 0 .4em}
.ui{font-family:var(--sans)}
.muted{color:var(--muted)}.faint{color:var(--faint)}
.chip{display:inline-flex;align-items:center;gap:4px;font:500 .74rem/1 var(--sans);padding:5px 9px;border-radius:999px;background:var(--chip);color:var(--muted);white-space:nowrap}
.chip.type{background:var(--accent-soft);color:var(--accent)}
.chip.disputed{background:var(--warn-soft);color:var(--warn)}
.chip.ok{background:var(--ok-soft);color:var(--ok)}
.chip.st-placeholder{background:var(--chip);color:var(--faint)}
.chips{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
/* index */
.toolbar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:8px 0 18px}
.toolbar input[type=search]{flex:1 1 280px;font:1rem var(--sans);padding:10px 14px;border:1px solid var(--line);border-radius:10px;background:var(--panel);color:var(--ink)}
.toolbar select,.toolbar label{font:.88rem var(--sans);color:var(--muted)}
.toolbar select{padding:9px 10px;border:1px solid var(--line);border-radius:10px;background:var(--panel);color:var(--ink)}
.typebar{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:18px}
.typebar button{font:500 .8rem var(--sans);border:1px solid var(--line);background:var(--panel);color:var(--muted);padding:6px 11px;border-radius:999px;cursor:pointer}
.typebar button.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:16px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden;text-decoration:none;color:inherit;display:flex;flex-direction:column;box-shadow:var(--shadow);transition:transform .12s}
.card:hover{transform:translateY(-2px)}
.card .ph{aspect-ratio:4/3;background:var(--chip);display:flex;align-items:center;justify-content:center;overflow:hidden}
.card .ph img{width:100%;height:100%;object-fit:cover}
.card .ph span{font:600 2rem var(--serif);color:var(--faint)}
.card .bd{padding:10px 12px 13px;display:flex;flex-direction:column;gap:6px}
.card .t{font:600 1rem/1.3 var(--serif)}
.card .s{font:.82rem/1.45 var(--sans);color:var(--muted);display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.count{font:.85rem var(--sans);color:var(--muted);margin-bottom:10px}
/* entry */
.crumbs{font:.82rem var(--sans);color:var(--muted)}
.lede{font-size:1.12rem;line-height:1.6;color:var(--ink);max-width:68ch;margin:.6em 0 0}
.entry{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:40px;margin-top:22px}
@media (max-width:900px){.entry{grid-template-columns:1fr}.side{order:-1}}
.article{max-width:72ch}
.side{display:flex;flex-direction:column;gap:18px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;box-shadow:var(--shadow)}
.panel h4{margin:0 0 8px;font:600 .75rem var(--sans);letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
figure{margin:0}
figure.primary{background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden;box-shadow:var(--shadow)}
figure.primary img{width:100%;max-height:520px;object-fit:contain;background:var(--chip)}
figcaption{padding:10px 14px 12px;font:.84rem/1.45 var(--sans)}
figcaption .attr{display:block;margin-top:5px;color:var(--faint);font-size:.75rem}
.gallery{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.gallery a{display:block;aspect-ratio:1;border-radius:8px;overflow:hidden;background:var(--chip);border:1px solid var(--line)}
.gallery img{width:100%;height:100%;object-fit:cover}
dl.facts{display:grid;grid-template-columns:auto 1fr;gap:6px 12px;margin:0;font:.86rem/1.45 var(--sans)}
dl.facts dt{color:var(--muted)}dl.facts dd{margin:0}
.banner{border:1px dashed var(--line);border-radius:12px;padding:14px 16px;font:.9rem/1.5 var(--sans);color:var(--muted);background:var(--panel)}
.ideas{border-left:3px solid var(--accent);padding:2px 0 2px 16px;margin:12px 0}
.ideas li{margin:.35em 0}
.outline{list-style:none;padding:0;margin:0;counter-reset:s}
.outline li{counter-increment:s;padding:10px 0;border-bottom:1px solid var(--line)}
.outline li:last-child{border:0}
.outline b{font-family:var(--serif)}
.outline b::before{content:counter(s) ". ";color:var(--faint)}
.outline span{display:block;font:.86rem/1.5 var(--sans);color:var(--muted);margin-top:2px}
.guide{font:.85rem/1.5 var(--sans);color:var(--muted);background:var(--guide);border-radius:8px;padding:8px 12px;margin:.6em 0}
.callout{border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:8px;padding:10px 14px;margin:1em 0;background:var(--panel);font-size:.95rem}
.callout-title{font:600 .82rem var(--sans);text-transform:uppercase;letter-spacing:.05em;color:var(--accent);margin-bottom:4px}
.callout p:first-child{margin-top:0}.callout p:last-child{margin-bottom:0}
.citation{color:var(--muted);font-size:.92em}
a.cite{color:inherit;text-decoration:underline dotted;text-underline-offset:2px}
a.cite:hover{color:var(--link)}
li.bib-entry{margin:.6em 0}
li.bib-entry .annot{display:block;color:var(--muted);font-size:.92em}
.works-cited{margin-top:2.2em;border-top:1px solid var(--line)}
ul.bib{list-style:none;padding:0;font-size:.92rem}
ul.bib li{padding-left:1.6em;text-indent:-1.6em;margin:.5em 0}
ul.bib li:target{background:var(--accent-soft);border-radius:4px}
ul.bib .abbr{font-weight:600}
abbr[title]{text-decoration:underline dotted;text-decoration-color:var(--faint);text-underline-offset:2px;cursor:help}
table.psg{width:100%;border-collapse:collapse;font:.9rem/1.45 var(--sans)}
table.psg td{padding:8px 8px 8px 0;border-bottom:1px solid var(--line);vertical-align:top}
table.psg td.ref{white-space:nowrap;font-weight:600;width:1%;padding-right:14px}
table.psg td.rel{width:1%;white-space:nowrap;padding-right:14px}
table.psg tr.book td{border:0;padding-top:16px;font:600 .74rem var(--sans);letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.scroll{overflow-x:auto}
.related{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:10px}
.mini{display:flex;gap:10px;align-items:center;padding:8px;border:1px solid var(--line);border-radius:10px;background:var(--panel);text-decoration:none;color:inherit}
.mini img,.mini .ph{width:44px;height:44px;border-radius:6px;object-fit:cover;flex:none;background:var(--chip);display:flex;align-items:center;justify-content:center;font:600 1rem var(--serif);color:var(--faint)}
.mini b{font:600 .86rem/1.3 var(--sans)}.mini small{display:block;font:.72rem var(--sans);color:var(--muted)}
.history{font:.82rem/1.5 var(--sans);color:var(--muted);padding-left:18px;margin:0}
.history li{margin:.35em 0}
.missing{color:var(--bad)}
/* bible */
.books{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}
.books a{display:flex;justify-content:space-between;padding:9px 12px;border:1px solid var(--line);border-radius:10px;background:var(--panel);text-decoration:none;color:var(--ink);font:.9rem var(--sans)}
.books a span{color:var(--muted)}
.books a.none{opacity:.4;pointer-events:none}
h3.corpus{font:600 .78rem var(--sans);letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin:22px 0 10px}
/* images */
.imgs{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px}
.imgs figure{background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.imgs figure img{width:100%;aspect-ratio:4/3;object-fit:cover;background:var(--chip)}
.imgs figcaption{font-size:.78rem}
.flag{outline:2px solid var(--warn);outline-offset:-2px}
dialog.lb{border:0;padding:0;margin:auto;background:transparent;max-width:min(96vw,1400px);max-height:96vh;overflow:visible}
html:has(dialog.lb[open]){overflow:hidden}
dialog.lb::backdrop{background:rgba(12,10,8,.88)}
dialog.lb img{max-width:min(96vw,1400px);max-height:84vh;width:auto;height:auto;margin:0 auto;border-radius:6px;cursor:zoom-out}
dialog.lb p{margin:10px auto 0;max-width:70ch;text-align:center;font:.86rem/1.45 var(--sans);color:#e8e2d8}
dialog.lb p a{color:#f0b48a}
dialog.lb button{position:fixed;background:rgba(0,0,0,.45);color:#fff;border:0;border-radius:50%;width:44px;height:44px;font:1.5rem/1 var(--sans);cursor:pointer}
dialog.lb button:hover{background:rgba(0,0,0,.7)}
dialog.lb .x{top:14px;right:14px}dialog.lb .pv{left:14px;top:50%}dialog.lb .nx{right:14px;top:50%}
footer{border-top:1px solid var(--line);padding:22px 0 40px;font:.8rem var(--sans);color:var(--muted)}
"""



# Opens image links (any <a> wrapping an <img> whose href points into media/)
# in an overlay instead of navigating to the raw file. Modified clicks
# (ctrl/cmd/shift/middle) still open the file normally.
LIGHTBOX_JS = r"""(()=>{
const sel='a[href*="media/"]:has(img)';
const d=document.createElement("dialog");d.className="lb";
d.innerHTML='<img alt=""><p></p><button class="x" aria-label="Close">×</button><button class="pv" aria-label="Previous">‹</button><button class="nx" aria-label="Next">›</button>';
document.body.append(d);
const im=d.querySelector("img"),cap=d.querySelector("p"),pv=d.querySelector(".pv"),nx=d.querySelector(".nx");
let set=[],k=0;
const vis=a=>a.offsetParent!==null;
function caption(a){const f=a.closest("figure")?.querySelector("figcaption");
if(f)return f.innerHTML;const t=a.getAttribute("title");if(!t)return"";const s=document.createElement("span");s.textContent=t;return s.outerHTML}
function show(i){k=(i+set.length)%set.length;const a=set[k];im.src=a.href;im.alt=a.querySelector("img").alt||"";
cap.innerHTML=caption(a);cap.hidden=!cap.innerHTML;pv.hidden=nx.hidden=set.length<2}
document.addEventListener("click",e=>{const a=e.target.closest(sel);
if(!a||e.button||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;
e.preventDefault();set=[...document.querySelectorAll(sel)].filter(vis);show(set.indexOf(a));d.showModal()});
d.addEventListener("click",e=>{if(e.target===pv)show(k-1);else if(e.target===nx)show(k+1);else if(!e.target.closest("p a"))d.close()});
d.addEventListener("keydown",e=>{if(e.key==="ArrowLeft")show(k-1);else if(e.key==="ArrowRight")show(k+1)});
d.addEventListener("close",()=>{im.removeAttribute("src")});
})();
"""


def page(title: str, body: str, depth: int, active: str = "", extra_head: str = "") -> str:
    up = "../" * depth
    nav = [("index.html", "Entries", "entries"), ("bible/index.html", "Passages", "bible"),
           ("images.html", "Images", "images"), ("map.html", "Map", "map"), ("review.html", "Review", "review"), ("about.html", "About", "about")]
    links = "".join(f'<a href="{up}{h}" class="{"on" if k == active else ""}">{t}</a>' for h, t, k in nav)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · OBBD</title><link rel="stylesheet" href="{up}assets/style.css">{extra_head}</head>
<body><header class="top"><div class="wrap"><a class="brand" href="{up}index.html">Open Bible Background Dictionary<small>Working draft · not for citation</small></a>
<nav class="main">{links}</nav></div></header>
<main class="wrap">{body}</main>
<script src="{up}assets/lightbox.js" defer></script>
<footer><div class="wrap">Generated from the OBBD repository. All entries are scaffold drafts awaiting expert review unless marked approved. Images: see each attribution line.</div></footer>
</body></html>"""


def build_thumbs(media: dict) -> None:
    from PIL import Image
    tdir = SITE / "thumbs"
    tdir.mkdir(parents=True, exist_ok=True)
    for mid, m in media.items():
        src = MEDIA / m["file"]
        dst = tdir / f"{mid}.jpg"
        if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
            continue
        try:
            with Image.open(src) as im:
                im = im.convert("RGB")
                im.thumbnail((THUMB, THUMB))
                im.save(dst, quality=80, optimize=True)
        except Exception as ex:
            print(f"thumb failed for {mid}: {ex}")


def ensure_media_link() -> None:
    link = SITE / "media"
    if link.is_symlink() or link.exists():
        return
    try:
        os.symlink(os.path.relpath(MEDIA, SITE), link)
    except OSError:
        import shutil
        shutil.copytree(MEDIA, link)


def uncertain_ids() -> dict[str, str]:
    p = ROOT / "seed" / "images" / "uncertain.md"
    out = {}
    if p.exists():
        for m in re.finditer(r"^- \*\*([^*]+)\*\*:?\s*(.*)$", p.read_text(), re.M):
            for i in re.split(r"\s*[,/]\s*|\s+and\s+", m.group(1)):
                i = i.strip().split(" ")[0]
                if i:
                    out[i] = m.group(2)
    return out


# ------------------------------------------------------------------ build

def build_site() -> Path:
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "assets").mkdir(exist_ok=True)
    (SITE / "entry").mkdir(exist_ok=True)
    (SITE / "bible").mkdir(exist_ok=True)
    (SITE / "assets" / "style.css").write_text(CSS)
    (SITE / "assets" / "lightbox.js").write_text(LIGHTBOX_JS)
    ensure_media_link()

    types = entry_types(); rels = relations(); cults = cultures(); people = contributors()
    E = {i: load_yaml(ENTRIES / f"{i}.yaml") for i in all_entry_ids()}
    media = {p.stem: load_yaml(p) for p in sorted(MEDIA.glob("*.yaml"))}
    build_thumbs(media)
    flagged = uncertain_ids()

    # backlinks
    back = defaultdict(set)
    for i, e in E.items():
        for r in e.get("related") or []:
            back[r].add(i)

    def thumb_of(e, depth):
        for m in e.get("media") or []:
            if m["id"] in media:
                return f'{"../" * depth}thumbs/{m["id"]}.jpg'
        return None

    def mini(i, depth):
        e = E.get(i)
        if not e:
            return f'<span class="mini missing">{esc(i)}</span>'
        t = thumb_of(e, depth)
        img = f'<img src="{t}" alt="" loading="lazy">' if t else f'<span class="ph">{esc(e["title"][:1])}</span>'
        return f'<a class="mini" href="{"../" * depth}entry/{i}.html">{img}<span><b>{esc(e["title"])}</b><small>{esc(types[e["type"]]["label"])}</small></span></a>'

    def link_for(depth):
        def link(target, label, embed):
            if embed:
                mid = Path(target).stem
                if mid in media:
                    m = media[mid]
                    return (f'<figure class="primary"><img src="{"../" * depth}media/{esc(m["file"])}" alt="">'
                            f'<figcaption>{esc(m.get("caption") or "")}<span class="attr">{esc(m["attribution"])}</span></figcaption></figure>')
                return f'<span class="missing">[missing image {esc(target)}]</span>'
            if target in E:
                return f'<a href="{target}.html">{esc(label or E[target]["title"])}</a>'
            return f'<span class="missing" title="no such entry">{esc(label or target)}</span>'
        return link

    # ---------------- entry pages
    for i, e in E.items():
        t = types[e["type"]]
        chips = [f'<span class="chip type">{esc(t["label"])}</span>']
        if e.get("date"):
            chips.append(f'<span class="chip">{esc(e["date"].get("display") or "")}</span>')
        for c in e.get("cultures") or []:
            chips.append(f'<span class="chip">{esc(cults.get(c, {}).get("label", c))}</span>')
        st = e.get("status", "placeholder")
        ap = approval_state(e)
        chips.append(f'<span class="chip st-{st} {"ok" if st == "approved" and ap == "current" else ""}">{esc(st)}{" · " + ap if st == "approved" else ""}</span>')
        aliases = f'<div class="muted ui" style="font-size:.9rem">Also: {esc(", ".join(e["aliases"]))}</div>' if e.get("aliases") else ""

        # images
        side = []
        ms = [m for m in (e.get("media") or []) if m["id"] in media]
        if ms:
            prim = next((m for m in ms if m.get("role") == "primary"), ms[0])
            pm = media[prim["id"]]
            cap = prim.get("caption") or pm.get("caption") or ""
            rv = pm.get("review", {}).get("status", "unreviewed")
            side.append(f'''<figure class="primary"><a href="../media/{esc(pm["file"])}"><img src="../media/{esc(pm["file"])}" alt="{esc(cap)}"></a>
<figcaption>{esc(cap)}<span class="attr">{esc(pm["attribution"])} · <a href="{esc(pm["source"]["page"])}">source</a> · image {esc(rv)}{" · ⚑ flagged" if i in flagged else ""}</span></figcaption></figure>''')
            others = [m for m in ms if m is not prim]
            if others:
                g = "".join(f'<a href="../media/{esc(media[m["id"]]["file"])}" title="{esc(media[m["id"]].get("caption") or "")}"><img src="../thumbs/{m["id"]}.jpg" alt="" loading="lazy"></a>' for m in others)
                side.append(f'<div class="panel"><h4>More images</h4><div class="gallery">{g}</div></div>')
        elif t.get("image_expected"):
            side.append('<div class="banner">No openly licensed image found yet.</div>')

        facts = [("Type", t["label"])]
        if e.get("date"):
            facts.append(("Date", e["date"].get("display")))
        if e.get("cultures"):
            facts.append(("Culture", ", ".join(cults.get(c, {}).get("label", c) for c in e["cultures"])))
        loc = e.get("location") or {}
        if loc.get("institution"):
            facts.append(("Location", loc["institution"] + (f" ({loc['accession']})" if loc.get("accession") else "")))
        if e.get("coordinates"):
            co = e["coordinates"]
            facts.append(("Coordinates", f'{co["lat"]:.4f}, {co["lon"]:.4f}'))
        ext = e.get("external") or {}
        links = []
        if ext.get("wikipedia"):
            links.append(f'<a href="https://en.wikipedia.org/wiki/{esc(ext["wikipedia"].replace(" ", "_"))}">Wikipedia</a>')
        if ext.get("wikidata"):
            links.append(f'<a href="https://www.wikidata.org/wiki/{esc(ext["wikidata"])}">Wikidata</a>')
        if ext.get("pleiades"):
            links.append(f'<a href="https://pleiades.stoa.org/places/{esc(ext["pleiades"])}">Pleiades</a>')
        fdl = "".join(f"<dt>{esc(k)}</dt><dd>{esc(str(v))}</dd>" for k, v in facts)
        if links:
            fdl += f"<dt>Links</dt><dd>{' · '.join(links)}</dd>"
        cred = e.get("credits") or {}
        who = lambda ids: ", ".join(people.get(x, {}).get("name", x) for x in ids) or "—"
        fdl += f"<dt>Authors</dt><dd>{esc(who(cred.get('authors') or []))}</dd><dt>Reviewers</dt><dd>{esc(who(cred.get('reviewers') or []))}</dd>"
        side.append(f'<div class="panel"><h4>Facts</h4><dl class="facts">{fdl}</dl></div>')
        hist = "".join(f'<li><b>{esc(str(h["date"]))}</b> · {esc(h["action"])} by {esc(people.get(h["by"], {}).get("name", h["by"]))}{": " + esc(h["note"]) if h.get("note") else ""}</li>' for h in reversed(e.get("history") or []))
        side.append(f'<div class="panel"><h4>Editorial history</h4><ol class="history" reversed>{hist}</ol></div>')

        # article
        main = []
        start_citations()
        md_text = (ENTRIES / f"{i}.md").read_text() if (ENTRIES / f"{i}.md").exists() else ""
        ed = e.get("editorial") or {}
        if st == "placeholder":
            main.append('<div class="banner"><b>Article not yet written.</b> Below are the planned outline and the notes for the writer, generated with the entry. All of it needs expert review.</div>')
            if ed.get("author_notes"):
                notes = "".join(f"<li>{_inline(n, link_for(1))}</li>" for n in ed["author_notes"])
                main.append(f'<h2>What the article should cover</h2><ul class="ideas">{notes}</ul>')
            from .scaffold import SECTION_GUIDANCE
            outl = "".join(f'<li><b>{esc(s)}</b><span>{esc(SECTION_GUIDANCE.get(s, ""))}</span></li>' for s in entry_sections(e))
            main.append(f'<h2>Planned sections</h2><ol class="outline">{outl}</ol>')
            if ed.get("sources_to_check"):
                srcs = "".join(f"<li>{esc(s)}{(' <span class=\"chip ok\" title=\"citekey in bibliography/references.yaml\">@' + k + '</span>') if (k := citekey_for(s)) else ''}</li>" for s in ed["sources_to_check"])
                main.append(f'<h2>Editions and studies to consult</h2><p class="muted ui" style="font-size:.85rem">AI-suggested; every item must be verified.</p><ul>{srcs}</ul>')
        else:
            main.append(f'<div class="prose">{render_md(md_text, link_for(1))}</div>')
        main.append(works_cited())

        # passages
        if e.get("passages"):
            rows, last_book = [], None
            parsed = []
            for p in e["passages"]:
                try:
                    rs = refs.parse(p["ref"])
                    parsed.append((rs[0].key(), rs, p))
                except refs.RefError:
                    parsed.append(((999,), [], p))
            for _, rs, p in sorted(parsed, key=lambda x: x[0]):
                book = refs.books()[rs[0].book]["name"] if rs else "?"
                if book != last_book:
                    rows.append(f'<tr class="book"><td colspan="3">{esc(book)}</td></tr>')
                    last_book = book
                disp = refs.display(p["ref"]) if rs else p["ref"]
                anchor = f'../bible/{rs[0].book}.html#c{rs[0].c1}' if rs else "#"
                dis = ' <span class="chip disputed">disputed</span>' if p.get("disputed") else ""
                rows.append(f'<tr><td class="ref"><a href="{anchor}">{esc(disp)}</a></td><td class="rel"><span class="chip" title="{esc(rels[p["rel"]]["definition"])}">{esc(rels[p["rel"]]["label"])}</span>{dis}</td><td>{esc(p.get("note") or "")}</td></tr>')
            main.append(f'<h2>Biblical passages <span class="faint ui" style="font-size:.8rem;font-weight:400">({len(e["passages"])})</span></h2><div class="scroll"><table class="psg">{"".join(rows)}</table></div>')
        rel = e.get("related") or []
        if rel:
            main.append(f'<h2>Related entries</h2><div class="related">{"".join(mini(r, 1) for r in rel)}</div>')
        bl = sorted(back[i] - set(rel))
        if bl:
            main.append(f'<h2>Referenced by</h2><div class="related">{"".join(mini(r, 1) for r in bl)}</div>')

        body = f'''<div class="crumbs"><a href="../index.html">Entries</a> / {esc(t["label"])}</div>
<h1>{esc(e["title"])}</h1>{aliases}<div class="chips" style="margin-top:8px">{"".join(chips)}</div>
<p class="lede">{esc(e.get("scope") or "")}</p>
<div class="entry"><div class="article">{"".join(main)}</div><aside class="side">{"".join(side)}</aside></div>'''
        (SITE / "entry" / f"{i}.html").write_text(page(e["title"], body, 1, "entries"))

    # ---------------- index
    idx = []
    for i, e in E.items():
        idx.append({"id": i, "t": e["title"], "a": e.get("aliases") or [], "ty": e["type"],
                    "s": e.get("scope", ""), "d": (e.get("date") or {}).get("display") or "",
                    "c": e.get("cultures") or [], "r": sorted({cults.get(c, {}).get("region", "") for c in e.get("cultures") or []}),
                    "img": thumb_of(e, 0), "st": e.get("status"), "np": len(e.get("passages") or [])})
    idx.sort(key=lambda x: x["t"].lower().lstrip("ʿ\"'"))
    tl = {k: v["label"] for k, v in types.items()}
    regions = sorted({v["region"] for v in cults.values()})
    body = f'''<h1>Entries</h1>
<p class="lede">An open, structured dictionary of the ancient Near Eastern and Greco-Roman background of the Bible. <span class="muted">{len(E)} entries · {sum(len(e.get("passages") or []) for e in E.values())} passage tags · {len(media)} images.</span></p>
<div class="toolbar ui"><input type="search" id="q" placeholder="Search titles, aliases, scope…  (e.g. Mesha, shepherd, Sabbath)" autofocus>
<select id="region"><option value="">All regions</option>{"".join(f'<option value="{r}">{r.title()}</option>' for r in regions)}</select>
<select id="sort"><option value="t">A–Z</option><option value="np">Most passages</option></select>
<label><input type="checkbox" id="img"> with image</label></div>
<div class="typebar" id="types"><button data-t="" class="on">All</button>{"".join(f'<button data-t="{k}">{esc(v)}</button>' for k, v in tl.items())}</div>
<div class="count" id="count"></div><div class="grid" id="grid"></div>
<script>
const D={json.dumps(idx, ensure_ascii=False)};
const TL={json.dumps(tl)};
let ty="";const $=s=>document.querySelector(s);
const norm=s=>s.normalize("NFD").replace(/[\\u0300-\\u036f\\u02be\\u02bf\\u02bc'ʿʾ]/g,"").toLowerCase();
D.forEach(d=>d.k=norm([d.t,...d.a,d.s,d.id].join(" ")));
function esc(s){{return s.replace(/[&<>"]/g,c=>({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]))}}
function draw(){{const q=norm($("#q").value.trim()).split(/\\s+/).filter(Boolean),rg=$("#region").value,im=$("#img").checked;
let r=D.filter(d=>(!ty||d.ty===ty)&&(!rg||d.r.includes(rg))&&(!im||d.img)&&q.every(w=>d.k.includes(w)));
if($("#sort").value==="np")r=[...r].sort((a,b)=>b.np-a.np);
$("#count").textContent=r.length+" of "+D.length+" entries";
$("#grid").innerHTML=r.map(d=>`<a class="card" href="entry/${{d.id}}.html"><div class="ph">${{d.img?`<img src="${{d.img}}" alt="" loading="lazy">`:`<span>${{esc(d.t[0])}}</span>`}}</div><div class="bd"><div class="chips"><span class="chip type">${{TL[d.ty]}}</span>${{d.d?`<span class="chip">${{esc(d.d)}}</span>`:""}}</div><div class="t">${{esc(d.t)}}</div><div class="s">${{esc(d.s)}}</div></div></a>`).join("");
try{{localStorage.setItem("obbd-q",JSON.stringify({{q:$("#q").value,ty,rg,im}}))}}catch(e){{}}}}
document.querySelectorAll("#types button").forEach(b=>b.onclick=()=>{{ty=b.dataset.t;document.querySelectorAll("#types button").forEach(x=>x.classList.toggle("on",x===b));draw()}});
["#q","#region","#img","#sort"].forEach(s=>$(s).addEventListener("input",draw));
try{{const s=JSON.parse(localStorage.getItem("obbd-q")||"null");if(s){{$("#q").value=s.q||"";$("#region").value=s.rg||"";$("#img").checked=!!s.im;ty=s.ty||"";document.querySelectorAll("#types button").forEach(x=>x.classList.toggle("on",x.dataset.t===ty))}}}}catch(e){{}}
draw();
</script>'''
    (SITE / "index.html").write_text(page("Entries", body, 0, "entries"))

    # ---------------- bible
    rows_by_book = defaultdict(list)
    for i, e in E.items():
        for p in e.get("passages") or []:
            try:
                for r in refs.parse(p["ref"]):
                    rows_by_book[r.book].append((r, i, p))
            except refs.RefError:
                pass
    bk = refs.books()
    corp = {"ot": "Hebrew Bible / Old Testament", "dc": "Deuterocanonical books", "pseud": "Pseudepigrapha", "nt": "New Testament"}
    blocks = []
    for c, label in corp.items():
        items = "".join(f'<a href="{b["id"]}.html" class="{"" if rows_by_book.get(b["id"]) else "none"}">{esc(b["name"])}<span>{len(rows_by_book.get(b["id"], []))}</span></a>'
                        for b in bk.values() if b["corpus"] == c)
        blocks.append(f'<h3 class="corpus">{label}</h3><div class="books">{items}</div>')
    allrows = [{"b": r.book, "c1": r.c1, "v1": r.v1, "c2": r.c2, "v2": r.v2, "d": r.display(), "e": i, "t": E[i]["title"],
                "rel": rels[p["rel"]]["label"], "x": bool(p.get("disputed")), "n": p.get("note") or ""}
               for b in rows_by_book for r, i, p in rows_by_book[b]]
    aliases = {}
    for b in bk.values():
        for k in {b["id"], b["sbl"], b["name"], b["sbl"].replace(" ", ""), b["name"].replace(" ", "")}:
            aliases[k.lower()] = b["id"]
    for k, v in {"psalm": "Ps", "psalms": "Ps", "qoh": "Eccl", "song of solomon": "Song", "canticles": "Song"}.items():
        aliases[k] = v
    body = f'''<h1>Passages</h1><p class="lede">Look up a passage to see every entry tagged to it, or browse by book.</p>
<div class="toolbar ui"><input type="search" id="ref" placeholder="e.g. Ezek 34:23, Gen 11, 2 Kgs 18:13-16, Ps 82" autofocus></div>
<div class="count" id="count"></div><div class="scroll"><table class="psg" id="res"></table></div>
{"".join(blocks)}
<script>
const R={json.dumps(allrows, ensure_ascii=False)};const A={json.dumps(aliases)};
const $=s=>document.querySelector(s);
function esc(s){{return s.replace(/[&<>"]/g,c=>({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]))}}
function parse(s){{const m=s.trim().match(/^((?:[1-4]\\s*)?[A-Za-z][A-Za-z .]*?)\\.?\\s+(\\d+)(?::(\\d+))?(?:\\s*[-–]\\s*(\\d+)(?::(\\d+))?)?$/);if(!m)return null;
const b=A[m[1].toLowerCase().replace(/\\.$/,"")]||A[m[1].toLowerCase().replace(/\\s+/g,"")];if(!b)return null;
let c1=+m[2],v1=m[3]?+m[3]:null,c2=c1,v2=v1;if(m[4]){{if(m[5]){{c2=+m[4];v2=+m[5]}}else if(v1!==null){{v2=+m[4]}}else{{c2=+m[4]}}}}return{{b,c1,v1,c2,v2}}}}
const key=(c,v,end)=>c*10000+(v===null?(end?9999:0):v);
function hit(r,q){{return r.b===q.b&&key(r.c1,r.v1,0)<=key(q.c2,q.v2,1)&&key(q.c1,q.v1,0)<=key(r.c2,r.v2,1)}}
function go(){{const q=parse($("#ref").value);if(!q){{$("#res").innerHTML="";$("#count").textContent=$("#ref").value?"Type a reference like Gen 1:1-2:3":"";return}}
const h=R.filter(r=>hit(r,q)).sort((a,b)=>key(a.c1,a.v1,0)-key(b.c1,b.v1,0));
$("#count").textContent=h.length+" tag"+(h.length==1?"":"s");
$("#res").innerHTML=h.map(r=>`<tr><td class="ref">${{esc(r.d)}}</td><td class="rel"><span class="chip">${{r.rel}}</span>${{r.x?' <span class="chip disputed">disputed</span>':""}}</td><td><a href="../entry/${{r.e}}.html"><b>${{esc(r.t)}}</b></a><br><span class="muted">${{esc(r.n)}}</span></td></tr>`).join("")}}
$("#ref").addEventListener("input",go);if(location.hash)$("#ref").value=decodeURIComponent(location.hash.slice(1));go();
</script>'''
    (SITE / "bible" / "index.html").write_text(page("Passages", body, 1, "bible"))
    for b, lst in rows_by_book.items():
        lst.sort(key=lambda x: (x[0].key(), x[1]))
        chap_rows = defaultdict(list)
        for r, i, p in lst:
            chap_rows[r.c1].append((r, i, p))
        sections = []
        for c in sorted(chap_rows):
            trs = "".join(
                f'<tr><td class="ref">{esc(r.display())}</td><td class="rel"><span class="chip">{esc(rels[p["rel"]]["label"])}</span>{" <span class=\"chip disputed\">disputed</span>" if p.get("disputed") else ""}</td>'
                f'<td><a href="../entry/{i}.html"><b>{esc(E[i]["title"])}</b></a><br><span class="muted">{esc(p.get("note") or "")}</span></td></tr>'
                for r, i, p in chap_rows[c])
            sections.append(f'<h2 id="c{c}">{esc(bk[b]["name"])} {c}</h2><div class="scroll"><table class="psg">{trs}</table></div>')
        chaps = " ".join(f'<a href="#c{c}">{c}</a>' for c in sorted(chap_rows))
        body = f'<div class="crumbs"><a href="index.html">Passages</a> / {esc(bk[b]["name"])}</div><h1>{esc(bk[b]["name"])}</h1><p class="ui muted">{len(lst)} tags · chapters: {chaps}</p>{"".join(sections)}'
        (SITE / "bible" / f"{b}.html").write_text(page(bk[b]["name"], body, 1, "bible"))

    # ---------------- images
    figs = []
    for mid, m in sorted(media.items()):
        ents = [d for d in m.get("depicts") or [] if d in E]
        main_e = ents[0] if ents else None
        fl = any(d in flagged for d in ents)
        note = esc(flagged.get(main_e, "")) if fl else ""
        figs.append(f'''<figure class="{"flag" if fl else ""}" data-f="{1 if fl else 0}" data-r="{esc(m.get("review", {}).get("status", ""))}"><a href="media/{esc(m["file"])}"><img src="thumbs/{mid}.jpg" alt="" loading="lazy"></a>
<figcaption><b>{" · ".join(f'<a href="entry/{d}.html">{esc(E[d]["title"])}</a>' for d in ents)}</b><br>{esc(m.get("caption") or "")}
<span class="attr">{esc(m["license"]["id"])} · {esc(m.get("review", {}).get("status", ""))}{" · ⚑ " + note if fl else ""}</span></figcaption></figure>''')
    body = f'''<h1>Images</h1><p class="lede">{len(media)} openly licensed images. Images outlined in amber were flagged as uncertain by the selection agents (see <code>seed/images/uncertain.md</code>).</p>
<div class="toolbar ui"><label><input type="checkbox" id="fl"> flagged only</label></div><div class="imgs" id="imgs">{"".join(figs)}</div>
<script>document.querySelector("#fl").addEventListener("input",e=>document.querySelectorAll("#imgs figure").forEach(f=>f.hidden=e.target.checked&&f.dataset.f!=="1"))</script>'''
    (SITE / "images.html").write_text(page("Images", body, 0, "images"))

    # ---------------- map
    pts = [{"id": i, "t": e["title"], "ty": e["type"], "lat": e["coordinates"]["lat"], "lon": e["coordinates"]["lon"], "img": thumb_of(e, 0)}
           for i, e in E.items() if e.get("coordinates")]
    head = ('<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">'
            '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>')
    body = f'''<h1>Map</h1><p class="lede">{len(pts)} entries with coordinates (from Wikidata). Needs an internet connection for the base map.</p>
<div id="map" style="height:72vh;border-radius:12px;border:1px solid var(--line)"></div>
<script>const P={json.dumps(pts, ensure_ascii=False)};
if(window.L){{const m=L.map("map").setView([32,38],5);L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png",{{attribution:"© OpenStreetMap contributors",maxZoom:17}}).addTo(m);
P.forEach(p=>L.circleMarker([p.lat,p.lon],{{radius:6,color:"#8a3b12",fillOpacity:.7}}).addTo(m).bindPopup(`${{p.img?`<img src="${{p.img}}" style="width:160px;border-radius:6px">`:""}}<a href="entry/${{p.id}}.html"><b>${{p.t}}</b></a>`));}}
else document.getElementById("map").textContent="Map library could not load (offline?).";</script>'''
    (SITE / "map.html").write_text(page("Map", body, 0, "map", head))

    # ---------------- review queue
    def linkify(h):
        def rep(m):
            tok = m.group(2)
            return f'{m.group(1)}<a href="entry/{tok}.html">{tok}</a>{m.group(3)}' if tok in E else m.group(0)
        h = re.sub(r"(<strong>|<code>)([a-z0-9-]+)(</strong>|</code>)", rep, h)
        return h
    secs = []
    up = ROOT / "seed" / "images" / "uncertain.md"
    vfiles = sorted((ROOT / "seed" / "verification").glob("batch-*.md"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0))
    toc = ['<a href="#images">Uncertain image picks</a>'] + [f'<a href="#{f.stem}">Passage check, {f.stem.replace("-", " ")}</a>' for f in vfiles]
    if up.exists():
        secs.append(f'<section id="images">{linkify(render_md(up.read_text(), lambda t, l, e: esc(l or t)))}</section>')
    for f in vfiles:
        txt = re.sub(r"^# .*\n", "", f.read_text(), count=1)
        secs.append(f'<section id="{f.stem}"><h1 style="font-size:1.5rem;margin-top:2em">Passage verification: {f.stem.replace("-", " ")}</h1>{linkify(render_md(txt, lambda t, l, e: esc(l or t)))}</section>')
    body = f'''<h1>Review queue</h1><p class="lede">Notes produced while preparing the scaffold: image picks the selection agents were unsure of, and the passage-tag verification reports (changes made, with items flagged for expert review). Entry ids link to their pages.</p>
<p class="ui chips">{" ".join(f'<span class="chip">{t}</span>' for t in toc)}</p><div class="article" style="max-width:80ch">{"".join(secs)}</div>'''
    (SITE / "review.html").write_text(page("Review queue", body, 0, "review"))

    # ---------------- about
    st = defaultdict(int)
    for e in E.values():
        st[e.get("status")] += 1
    rel_rows = "".join(f'<tr><td class="ref">{esc(v["label"])}</td><td>{esc(v["definition"])}</td></tr>' for v in rels.values())
    type_rows = "".join(f'<tr><td class="ref">{esc(v["label"])}</td><td>{esc(v["definition"])}</td></tr>' for v in types.values())
    body = f'''<h1>About this draft</h1><div class="article" style="max-width:76ch">
<p class="lede">This is a generated preview of the Open Bible Background Dictionary repository.</p>
<div class="callout callout-warning"><div class="callout-title">Scaffold stage</div><p>Status counts: {", ".join(f"{k}: {v}" for k, v in sorted(st.items()))}. Passage tags, scope statements, writer notes and image choices were generated by AI and must be reviewed by a qualified scholar before an entry is approved. Do not cite.</p></div>
<h2>Passage relations</h2><table class="psg">{rel_rows}</table>
<h2>Entry types</h2><table class="psg">{type_rows}</table>
<h2>Regenerate</h2><p class="ui">Run <code>./obbd site</code> (or <code>./obbd serve</code>) in the repository.</p></div>'''
    (SITE / "about.html").write_text(page("About", body, 0, "about"))
    print(f"site: {SITE}/index.html ({len(E)} entries, {len(media)} images, {len(pts)} mapped)")
    return SITE / "index.html"


def serve(port: int = 8000) -> None:
    import functools
    import http.server
    build_site()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as httpd:
        print(f"Serving at http://localhost:{port}/dist/site/index.html  (Ctrl+C to stop)")
        httpd.serve_forever()
