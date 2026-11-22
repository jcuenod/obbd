"""Editorial workflow: status transitions recorded in each entry's `history`.

Statuses
  placeholder     scaffolded; no article text yet
  draft           article being written
  in-review       submitted for expert review
  needs-revision  reviewer requested changes
  approved        approved by a qualified reviewer (see contributors.yaml)

Approvals are pinned to content hashes. `article_sha256` covers the Markdown
file. `data_sha256` covers the scholarly claims in the YAML (title, scope,
date, passages, related). If either changes after approval, the approval
is reported as *stale* until it is re-approved.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json

from .common import article_hash, contributors, load_entry, save_entry

STATUSES = ["placeholder", "draft", "in-review", "needs-revision", "approved"]

ACTIONS = {
    # action: (allowed from statuses, resulting status, requires approver rights)
    "draft":    (None, "draft", False),
    "submit":   ({"draft", "needs-revision"}, "in-review", False),
    "revise":   ({"in-review", "approved"}, "needs-revision", True),
    "approve":  ({"in-review", "approved", "draft", "needs-revision"}, "approved", True),
    "comment":  (None, None, False),
    "metadata-edit": (None, None, False),
}

HASHED_FIELDS = ("title", "type", "scope", "date", "passages", "related")


def data_hash(entry: dict) -> str:
    payload = {k: entry.get(k) for k in HASHED_FIELDS}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def last_approval(entry: dict) -> dict | None:
    for h in reversed(entry.get("history") or []):
        if h.get("action") == "approved":
            return h
    return None


def approval_state(entry: dict) -> str:
    """'none' | 'current' | 'stale-article' | 'stale-data' | 'stale-both'."""
    a = last_approval(entry)
    if not a:
        return "none"
    art = a.get("article_sha256") != article_hash(entry["id"])
    dat = a.get("data_sha256") != data_hash(entry)
    if art and dat:
        return "stale-both"
    if art:
        return "stale-article"
    if dat:
        return "stale-data"
    return "current"


def apply(id_: str, action: str, by: str, note: str | None = None, role: str | None = None) -> dict:
    if action not in ACTIONS:
        raise SystemExit(f"unknown action {action!r}; choose from {', '.join(ACTIONS)}")
    people = contributors()
    if by not in people:
        raise SystemExit(f"{by!r} is not in contributors.yaml")
    person = people[by]
    allowed_from, to_status, needs_rights = ACTIONS[action]
    if needs_rights and not person.get("can_approve"):
        raise SystemExit(f"{by} does not have approval rights (can_approve) in contributors.yaml")
    if needs_rights and person.get("kind") == "ai":
        raise SystemExit("AI contributors cannot approve or reject entries")
    e = load_entry(id_)
    if allowed_from and e["status"] not in allowed_from:
        raise SystemExit(f"cannot {action} an entry with status {e['status']!r}")
    if action == "approve":
        # reviewer must be someone other than the sole author, unless explicitly self-approving
        authors = set((e.get("credits") or {}).get("authors") or [])
        if authors == {by}:
            print(f"warning: {by} is the only author of {id_}; consider an independent reviewer")
    rec = {"date": dt.date.today().isoformat(), "action": {
        "draft": "drafted", "submit": "submitted", "revise": "revision-requested",
        "approve": "approved", "comment": "commented", "metadata-edit": "metadata-edited"}[action], "by": by}
    if role:
        rec["role"] = role
    if note:
        rec["note"] = note
    if action == "approve":
        rec["article_sha256"] = article_hash(id_)
        rec["data_sha256"] = data_hash(e)
        rev = e.setdefault("credits", {}).setdefault("reviewers", [])
        if by not in rev:
            rev.append(by)
    if action == "draft":
        au = e.setdefault("credits", {}).setdefault("authors", [])
        if by not in au:
            au.append(by)
    e.setdefault("history", []).append(rec)
    if to_status:
        e["status"] = to_status
    save_entry(e)
    return rec
