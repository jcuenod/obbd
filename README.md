# Open Bible Background Dictionary (OBBD)

An openly licensed, peer-reviewed reference work on the ancient Near Eastern and
Greco-Roman background of the Bible. It works like a wiki, but every entry also carries
structured data: which biblical passages it bears on and *how*, which images illustrate
it (with verified licenses), and who has reviewed and approved it.

Entries cover four kinds of subject:

* **artefacts and texts**: Mesha Stele, Sennacherib's Annals, Gudea Cylinders, Atrahasis, Amarna letters…
* **concepts and motifs**: shepherd-kingship, divine council, cosmology, cloud rider, name theology…
* **practices and realia**: Sabbath, levirate marriage, divination, horned altars, four-room house…
* **sites, peoples, persons, deities, events**: Lachish, Philistines, Hezekiah, Baal, the 701 campaign…

Concept entries act as hubs linking to the artefacts that document them.

```
$ ./obbd lookup "Ezek 34:23"
Ezek 34            Imagery or metaphor                  shepherd-kingship                  Indictment of Israel's shepherds; YHWH and 'my servant David' as shepherd
Ezek 34:1–24       Imagery or metaphor                  statue-of-gudea                    Ruler as shepherd chosen by the deity to care for the people
Ezek 34:23–24      Imagery or metaphor                  gudea                              Ruler as shepherd appointed by the deity
```

## Viewing it

```sh
./obbd serve          # builds dist/site and serves it at http://localhost:8000/dist/site/
# or: ./obbd site, then open dist/site/index.html directly in a browser
```

The viewer renders every entry in its current state. For entries that are still
placeholders it shows the scope, the planned outline, the writer notes, the editions to
consult (with bibliography citekeys where they match), the images with attribution, the
passage tags, related entries, and the editorial history. Its pages are:

* **Entries**: search and filter by type, region, and image.
* **Passages**: look up any reference and see every tagged entry, or browse by book.
* **Images**: the full gallery, with uncertain picks flagged.
* **Map**: sites with Wikidata coordinates.
* **Review**: the image picks and passage-verification notes that need an expert's eye.

## Status

The catalogue contains draft entries awaiting expert review.

* **699 entries**: 129 artefacts, 93 texts, 92 sites, 106 concepts, 88 practices, 61 realia, 51 persons, 39 deities, 29 peoples, and 11 events. The 39 most recent were added on 27 November 2026 from the entry additions and revisions report.
* **5,145 passage tags**, typed by relation. 453 are marked as disputed.
* **575 entries** are linked to Wikidata.
* **669 images** illustrate 536 entries. All are freely licensed (CC BY-SA, CC BY, CC0, public domain), and each has an attribution record.
* Every passage tag was checked by an agent against the verse text (World English Bible, `./obbd verse`). Changes are logged in each entry's history and summarised, with items flagged for expert review, in `seed/verification/`.
* Wikidata supplied coordinates and Pleiades ids for 85 sites, and collection and accession data for artefacts. These are marked "verify" in the history.
* `bibliography/references.yaml` collects standard editions, reference works, and other cited sources (COS, ANET, KAI, TAD, RINAP, SAA, …).

Each entry's `history` records AI contributions to drafting and scaffolding. Start with the image picks flagged in `seed/images/uncertain.md`, and look at
images with `./obbd media-sheet` (which opens `dist/media-review.html`).

`./obbd status` shows progress, and `./obbd validate` checks integrity.

## Layout

| path | contents |
|---|---|
| `entries/<id>.md` | article (Markdown, Obsidian-compatible; open the repo as a vault) |
| `entries/<id>.yaml` | structured data: type, date, scope, passages, related, media, review history |
| `media/` | image files and their license/attribution records |
| `contributors.yaml` | contributors, credentials, and who may approve |
| `bibliography/references.yaml` | shared bibliography (CSL-YAML), cited as `[@key]` |
| `vocab/` | controlled vocabularies: entry types, passage relations, cultures, Bible books |
| `schema/` | JSON Schemas for entry and media YAML (editor validation) |
| `seed/` | archival: the master entry list and seed files the scaffold was generated from, `seed/images/` (image selections and uncertain picks), and `seed/verification/` (passage-check reports). **The entry YAML is now canonical**: edit `entries/*.yaml`, not the seeds. |
| `tools/obbd/` | command-line tool (`./obbd --help`); Python 3.10+, PyYAML, requests, jsonschema |
| `docs/` | [data model](docs/data-model.md), [seed guide](docs/seed-guide.md), [image selection guide](docs/image-selection-guide.md) |

See [CONTRIBUTING.md](CONTRIBUTING.md) for the editorial workflow (draft → review →
approve) and how approvals are pinned to content hashes.

## Licensing

* **Article text and data**: proposed CC BY 4.0. *(Decision pending: CC BY-SA 4.0 is the main alternative.)*
* **Images**: each has its own free license, recorded in `media/<id>.yaml`. Show the `attribution` line wherever the image appears.
* **Code** (`tools/`): proposed MIT.
