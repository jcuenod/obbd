"""Static HTML contact sheet for reviewing entry images (open locally in a browser)."""
from __future__ import annotations

import html
import os
from pathlib import Path

from .common import ENTRIES, MEDIA, all_entry_ids, load_yaml
from .media import wants_image

CSS = """
:root{--bg:#faf8f4;--fg:#1d1b18;--mut:#6b655c;--card:#fff;--line:#e4ded3;--warn:#a4441b}
@media (prefers-color-scheme:dark){:root{--bg:#191714;--fg:#ece6dc;--mut:#a39b8f;--card:#24211d;--line:#3a352e;--warn:#e08a5f}}
body{background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,sans-serif;margin:0;padding:24px clamp(16px,4vw,48px)}
h1{font:600 22px Georgia,serif;margin:0 0 4px} .mut{color:var(--mut)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px;margin-top:20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;overflow:hidden;display:flex;flex-direction:column}
.card img{width:100%;aspect-ratio:4/3;object-fit:contain;background:#0001}
.card .b{padding:10px 12px;display:flex;flex-direction:column;gap:4px}
.t{font-weight:600}.id{font:12px ui-monospace,monospace;color:var(--mut)}
.lic{font-size:12px}.miss{color:var(--warn)}
details{margin-top:24px}
"""


def media_sheet(out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    rel = os.path.relpath(MEDIA, out.parent)
    cards, missing = [], []
    for id_ in all_entry_ids():
        e = load_yaml(ENTRIES / f"{id_}.yaml")
        if not e.get("media"):
            if wants_image(e):
                missing.append(e)
            continue
        for mref in e["media"]:
            m = load_yaml(MEDIA / f"{mref['id']}.yaml")
            cards.append(f"""<div class="card"><a href="{html.escape(m['source']['page'])}"><img loading="lazy" src="{rel}/{html.escape(m['file'])}" alt=""></a>
<div class="b"><span class="t">{html.escape(e['title'])}</span><span class="id">{id_} · {mref.get('role','')} · {m['id']}</span>
<span>{html.escape(m.get('caption') or '')}</span>
<span class="lic mut">{html.escape(m['attribution'])}</span>
<span class="lic mut">review: {html.escape(m['review']['status'])}</span></div></div>""")
    miss = "".join(f"<li><b>{html.escape(e['title'])}</b> <span class='id'>{e['id']}</span></li>" for e in missing)
    out.write_text(f"""<!doctype html><meta charset="utf-8"><title>OBBD image review</title><style>{CSS}</style>
<h1>OBBD image review sheet</h1><p class="mut">{len(cards)} images on entries · {len(missing)} image-bearing entries still without an image. Click an image to open its Commons page and check the license.</p>
<div class="grid">{''.join(cards)}</div>
<details><summary class="miss">Entries still needing an image ({len(missing)})</summary><ul>{miss}</ul></details>""")
    print(f"wrote {out}")
