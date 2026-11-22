# Contributing and editorial workflow

OBBD aims to be **citable**. Every article must represent mainstream critical scholarship
accurately, distinguish consensus from debate, and be approved by someone with relevant
expertise before it is shown as approved.

## Roles

* **Writers** draft and revise articles. Anyone can write.
* **Reviewers** (`can_approve: true` in `contributors.yaml`) hold a doctorate or equivalent
  in a relevant field. Their `areas` say what they review. Reviewers approve or request
  revisions, and only within their areas.
* **Editors** manage the entry list, vocabularies, and contributor records.
* **AI tools** may scaffold entries, suggest passage tags, and find images, but never
  approve anything. Their contributions appear in `history` so readers can see them.

## Status lifecycle

```
placeholder ──draft──▶ draft ──submit──▶ in-review ──approve──▶ approved
                         ▲                   │                      │
                         └──── needs-revision ◀──revise─────────────┘
```

```sh
./obbd review draft   mesha-stele --by jdoe            # writer starts drafting
./obbd review submit  mesha-stele --by jdoe            # ready for review
./obbd review approve mesha-stele --by jcuenod --note "Checked against KAI 181; passages verified"
./obbd review revise  mesha-stele --by jcuenod --note "Line 31 reading overstated"
./obbd review comment mesha-stele --by jcuenod --note "..."
```

An approval stores hashes of the article and of the entry's scholarly metadata (title,
scope, date, passages, related). `./obbd validate` warns when an approved entry has
changed since approval (*stale*). `./obbd validate --strict` (used in CI) fails on it.
Adding images, Wikidata IDs, or museum numbers does not make an approval stale.

## What a reviewer checks

1. **Accuracy**: facts, dates, readings, and translations match the standard editions.
2. **Consensus**: debated points are presented as debated, with major positions fairly stated.
3. **Passage tags**: every `passages` entry is correct (book, chapter, verse), the
   relation type is right, and contested links carry `disputed: true`. Remove weak tags.
4. **Citations**: every `[@key]` exists, is real, and supports the claim.
5. **Images**: each image shows what its caption says (see below).
6. **Scope**: the article does what the `scope` says, and the `scope` is still accurate.

## Writing guidelines

* Length: 300–900 words for most entries, and up to ~1500 for major hubs (e.g. `cosmology`, `divine-council`).
* Register: encyclopaedic, third person, no devotional or polemical framing.
* Quote ancient sources in your own translation or an openly licensed one. Do not paste copyrighted translations beyond fair-quotation length.
* Cite primary-source editions (e.g. COS, RINAP, KAI, TAD; DJD, Josephus or Philo in the Loeb Classical Library) and 3–6 items of further reading.
* Use `[[links]]` to other entries rather than repeating their content.
* Separate what the source *shows* from what scholars *infer*.

## Images

Images come only from free-licensed sources. At present that means Wikimedia Commons,
whose license metadata `./obbd media-fetch` records automatically. When reviewing an
image record (`media/*.yaml`):

* confirm the image shows the actual object or site (not a replica, unless the caption says so);
* confirm the license on the Commons page matches the record;
* then set `review: {status: approved, checked_by: <you>, date: YYYY-MM-DD}`.

You can add your own photographs. Place the file in `media/`, write a YAML record with your
chosen license (CC BY 4.0 or CC0 recommended), and add yourself as `creator`.

## Adding an entry

1. Add a line to `seed/master.txt` (`id | type | Title | hints`) under the appropriate domain.
2. Add a seed record to `seed/<domain>.yaml` (see `docs/seed-guide.md`) and run `./obbd seed-check`.
3. `./obbd scaffold <id>` creates the YAML and a placeholder article. It never overwrites an existing entry.
4. From then on, edit `entries/<id>.yaml` directly. The seeds are archival. After editing the YAML of a placeholder entry, run `./obbd placeholders <id>` to refresh its placeholder article.

## Useful commands while writing

* `./obbd check-passages <id>`: each passage tag with its verse text.
* `./obbd verse "Exod 20:8-11"`: verse text (World English Bible, public domain; English versification).
* `./obbd lookup "Ps 82"`: every entry tagged to a passage.
* `./obbd serve`: the browsable viewer.
