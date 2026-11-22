"""Enrich entries from Wikidata (using the QIDs found by wiki-resolve).

Adds, only where the field is empty:
  sites      coordinates {lat, lon, source}   (P625)   and external.pleiades (P1584)
  artefacts  location.institution (P195 collection label) and location.accession (P217)
Every changed entry gets a history record, so the provenance is visible. These
fields are not covered by approval hashes, so enrichment never invalidates an approval.
"""
from __future__ import annotations

import datetime as dt

from .common import ENTRIES, all_entry_ids, load_yaml, save_entry
from .media import api

WD = "https://www.wikidata.org/w/api.php"


def _claims(ids: list[str]) -> dict:
    out = {}
    for i in range(0, len(ids), 50):
        d = api(WD, action="wbgetentities", ids="|".join(ids[i:i + 50]), props="claims|labels", languages="en")
        out.update(d.get("entities", {}))
    return out


def _vals(ent: dict, prop: str) -> list:
    res = []
    for c in ent.get("claims", {}).get(prop, []):
        if c.get("rank") == "deprecated":
            continue
        dv = c.get("mainsnak", {}).get("datavalue")
        if dv:
            res.append((dv["value"], c.get("qualifiers", {})))
    return res


def enrich(dry_run: bool = False) -> None:
    E = {i: load_yaml(ENTRIES / f"{i}.yaml") for i in all_entry_ids()}
    qids = {i: (e.get("external") or {}).get("wikidata") for i, e in E.items()}
    qids = {i: q for i, q in qids.items() if q and E[i]["type"] in ("site", "artifact")}
    ents = _claims(sorted(set(qids.values())))
    # labels for collections
    coll_ids = set()
    for q in qids.values():
        for v, _ in _vals(ents.get(q, {}), "P195"):
            coll_ids.add(v["id"])
        for v, qual in _vals(ents.get(q, {}), "P217"):
            for qq in qual.get("P195", []):
                coll_ids.add(qq["datavalue"]["value"]["id"])
    labels = {k: v.get("labels", {}).get("en", {}).get("value") for k, v in _claims(sorted(coll_ids)).items()} if coll_ids else {}
    today = dt.date.today().isoformat()
    n = 0
    for i, q in sorted(qids.items()):
        e, ent, changes = E[i], ents.get(q, {}), []
        if e["type"] == "site":
            co = _vals(ent, "P625")
            if co and not e.get("coordinates"):
                v = co[0][0]
                e["coordinates"] = {"lat": round(v["latitude"], 5), "lon": round(v["longitude"], 5), "source": f"wikidata:{q}"}
                changes.append("coordinates")
            pl = _vals(ent, "P1584")
            if pl and not (e.get("external") or {}).get("pleiades"):
                e.setdefault("external", {})["pleiades"] = str(pl[0][0])
                changes.append("Pleiades id")
        else:
            loc = e.get("location") or {}
            colls = [labels.get(v["id"]) for v, _ in _vals(ent, "P195") if labels.get(v["id"])]
            invs = _vals(ent, "P217")
            if colls and not loc.get("institution"):
                loc["institution"] = colls[0]
                changes.append("institution")
            if invs and not loc.get("accession") and len(invs) == 1:
                v, qual = invs[0]
                coll = [labels.get(x["datavalue"]["value"]["id"]) for x in qual.get("P195", [])]
                loc["accession"] = v + (f" ({coll[0]})" if coll and coll[0] and coll[0] != loc.get("institution") else "")
                changes.append("accession")
            if changes:
                e["location"] = {"institution": loc.get("institution"), "accession": loc.get("accession")}
        if changes:
            e.setdefault("history", []).append({
                "date": today, "action": "metadata-edited", "by": "claude-opus-5-5",
                "note": f"Added {', '.join(changes)} from Wikidata {q} (verify)."})
            n += 1
            if not dry_run:
                save_entry(e)
            print(f"{i}: {', '.join(changes)}")
    print(f"enriched {n} entries")
