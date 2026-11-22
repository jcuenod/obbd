# Data model

OBBD is a set of plain-text files in a git repository. Nothing is stored in a database.
Git history is the audit trail. The `history` block in each entry is the *editorial*
record: who drafted it, who approved it, and when.

```
entries/<id>.md        article prose (Markdown, Obsidian-compatible)
entries/<id>.yaml      structured data for the entry (the "manifest")
media/<media-id>.jpg   image file (downscaled copy of a free-licensed original)
media/<media-id>.yaml  provenance, license, and attribution for the image
contributors.yaml      people (and tools) who appear in credits/history
bibliography/references.yaml     shared bibliography (CSL-YAML); cite as [@key]
bibliography/abbreviations.yaml  SBL abbreviations for series and journals (AOAT, WAW, HUCA…)
vocab/*.yaml           controlled vocabularies: entry types, relations, cultures, books
schema/*.schema.json   JSON Schemas (editor autocompletion + validation)
seed/                  the master entry list and the seed files that generated the scaffold
tools/obbd/            command-line tool (./obbd)
dist/                  generated JSON indexes (./obbd build); not committed
```

## Why a sidecar YAML rather than front matter?

* **Review integrity.** An approval records SHA-256 hashes of the article (`.md`) and of
  the scholarly claims in the YAML (title, scope, date, passages, related). If either
  changes after approval, the entry is flagged *stale* until a reviewer re-approves it.
  Housekeeping such as adding an image or a Wikidata ID does **not** invalidate an approval.
* **Clean diffs and clean prose.** Writers edit prose without scrolling past 60 lines of
  metadata, and scripts update metadata without touching prose files.
* **Obsidian still works.** Open the repository as a vault. `[[mesha-stele]]` resolves to
  `entries/mesha-stele.md`, and `![[mesha-stele-louvre-ao-5066.jpg]]` embeds an image.
  Obsidian ignores the `.yaml` files.

## Entry types

Defined in `vocab/entry-types.yaml`. Each type has its own article template (section headings).
For `concept`, `practice`, and `deity`, two headings also depend on which part of the Bible
the entry mainly bears on (`corpus`; see below):

| corpus | background heading | Bible heading |
|---|---|---|
| `ot` | Ancient Near Eastern Evidence | In the Hebrew Bible |
| `nt` | Jewish and Greco-Roman Evidence | In the New Testament |
| `both` | Extrabiblical Evidence | In the Bible |

`corpus` is inferred from the passage tags: whichever of OT and NT has at least twice
as many tags wins, and anything closer is `both`. Deuterocanonical and pseudepigraphal tags
are not counted. Set `corpus` in the entry YAML to override it.

| type | what it is | examples |
|---|---|---|
| `artifact` | one specific, extant object | Mesha Stele, Cyrus Cylinder, Gudea Statue B |
| `text` | a composition or corpus known from one or more copies | Atrahasis, Amarna letters |
| `site` | place or archaeological site | Lachish, Ugarit, Tophet |
| `person` | historical individual | Sennacherib, Hezekiah |
| `deity` | god, demon, or class of divine being | Baal, Leviathan |
| `people` | ethnic group, kingdom, or empire | Philistines, Assyria |
| `event` | datable event that serves as a hub | Sennacherib's 701 campaign |
| `concept` | motif, worldview element, or theme | shepherd-kingship, divine council, cosmology |
| `practice` | legal/cultic/social institution | levirate marriage, divination, Sabbath |
| `realia` | class of objects or structures | horned altars, cylinder seals, four-room house |

Artefact-oriented and concept-oriented entries complement each other. Concept entries
(e.g. `shepherd-kingship`) are hubs that link to the artefacts that document them
(`statue-of-gudea`, `code-of-hammurabi`). Artefact entries keep the specifics.

## Entry YAML

```yaml
id: mesha-stele                 # permanent; equals filename
title: Mesha Stele
aliases: [Moabite Stone]
type: artifact
cultures: [moabite]             # vocab/cultures.yaml
corpus: ot                      # optional: ot | nt | both (default: inferred from passages)
date: {from: -840, to: -840, circa: true, display: c. 840 BCE}   # negative = BCE
scope: >-                       # 1–3 sentences; what the entry covers
  ...
passages:                       # the core structured data; see below
  - ref: 2Kgs 3:4-27
    rel: event
    note: Mesha's rebellion against Israel, told from the Moabite side
  - ref: 2Sam 8:2
    rel: attests
    disputed: true
    note: ...
related: [chemosh, omri, moabites]      # other entry ids
location: {institution: Musée du Louvre, Paris, accession: null}
media:                          # media ids; first `primary` is the lead image
  - {id: mesha-stele-louvre-ao-5066, role: primary}
external: {wikipedia: Mesha Stele, wikidata: Q...}
editorial:                      # working notes for writers; not published
  author_notes: [...]
  sources_to_check: [...]
  image_query: ...
status: placeholder             # placeholder | draft | in-review | needs-revision | approved
credits: {authors: [], reviewers: []}
history:                        # append-only editorial log
  - {date: 2026-11-20, action: created, by: claude-opus-5-5, note: ...}
  - {date: 2027-02-01, action: approved, by: jcuenod, article_sha256: ..., data_sha256: ...}
```

### Passage tags

`ref` is one book plus one or more ranges in OSIS book IDs with `chapter:verse`
notation: `2Kgs 18-19`, `2Kgs 18:13-19:37`, `Exod 25:9, 40`, `Ezek 14:14, 20; 28:3`,
`Obad 10-14`. Versification is **English (NRSV)**. MT differences go in the note.
`./obbd ref "..."` parses and normalises a reference, and the build expands every tag into
OSIS ranges (`2Kgs.18.13-2Kgs.19.37`) for interoperability.

`rel` says *how* the entry bears on the passage (`vocab/relations.yaml`): `event`, `attests`,
`parallel`, `form`, `imagery`, `concept`, `practice`, `polemic`, `language`, `realia`,
`setting`. `disputed: true` marks connections that are live debates in mainstream scholarship.

This makes queries such as "everything relevant to Ezek 34:23", "every extrabiblical
account of an event in 2 Kings", or "all disputed connections in Genesis 1–11" trivial:

```
$ ./obbd lookup "Ezek 34:23"
```

## Media YAML

```yaml
id: mesha-stele-louvre-ao-5066
file: mesha-stele-louvre-ao-5066.jpg
caption: The Mesha Stele, Musée du Louvre
creator: ...                    # from Commons metadata
license: {id: CC-BY-SA-4.0, name: CC BY-SA 4.0, url: https://creativecommons.org/licenses/by-sa/4.0/}
attribution: "X, CC BY-SA 4.0, via Wikimedia Commons."   # ready to print
source: {page: https://commons.wikimedia.org/wiki/File:..., original_url: ..., sha1: ..., retrieved: 2026-11-20}
derivative: Downscaled to 1600×2133 px
depicts: [mesha-stele]          # entries this image may illustrate
review: {status: unreviewed, checked_by: null, date: null, note: ...}
```

Accepted licenses: public domain, CC0, CC BY, CC BY-SA (any version), and Free Art License.
GFDL-only files are rejected, because the GFDL requires its full text to accompany every copy;
files dual-licensed GFDL + CC are recorded under their CC license.
NC and ND licenses, fair use, and "permission" licenses are rejected automatically.
CC BY-SA images keep their own license. Including them in the dictionary is aggregation,
so the dictionary's text license is unaffected, but each image must be shown with its attribution line.

## Markdown conventions

* `[[entry-id]]` or `[[entry-id|display text]]`: cross-reference to another entry.
* `![[media-file.jpg]]`: embed an additional figure (the primary image is placed automatically).
* `[@citekey]`, `[@citekey, 45–47]`, `[@a; @b]`, `[see @a, 12]`: Pandoc-style citations; keys live in `bibliography/references.yaml`. The site renders them in SBL Handbook style: author–date for most works, "(George 2003, 45–47)", or the work's `citation-label` abbreviation for standard editions and reference works, "(*COS* 1.105)", "(*COS* 2:287)", "(*KAI* 181)", "(RINAP 1 no. 35)". Write locators as you would in SBL style; a leading "p."/"pp." is dropped, as is "no."/"nos." after a single-volume abbreviation. Each short citation links to a Works Cited list at the end of the article. A Further Reading list item that begins with a citation (`- [@ael]: Translates…`) is shown as the full reference followed by its annotation.
* Scripture references in prose are written in SBL style ("2 Kgs 18:13–16") and are auto-linked by the renderer. The authoritative passage index is the YAML, not the prose.
* Obsidian callouts (`> [!note]`) are allowed. The `[!info]`/`[!todo]` placeholder callouts are removed when drafting starts.
* No front matter and no H1: the title comes from the YAML. Articles start at `## Overview`.
* The first paragraph under `## Overview` serves as the entry summary.

## Building

`./obbd build` writes:

* `dist/entries.json`: every entry with article text, approval state, backlinks, and regions;
* `dist/passages.json`: one row per tagged range, in canonical order, with OSIS IDs;
* `dist/media.json`: all media records.

A website, an Obsidian plugin, a Logos/Accordance export, or an API can all be built on these files.
