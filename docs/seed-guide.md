# Seed authoring guide

Seed files (`seed/<domain>.yaml`) are compact, hand-curated definitions of entries.
`./obbd scaffold` expands them into `entries/<id>.yaml` and placeholder `entries/<id>.md`.
The canonical list of entry IDs, types, titles, and domains is `seed/master.txt`.

Run `./obbd seed-check seed/<domain>.yaml` until it reports no errors.

## Fields

| field | required | notes |
|---|---|---|
| `id` | yes | Must exist in `seed/master.txt`. |
| `title` | no | Only if the master title is wrong or poor. |
| `aliases` | no | Other names a reader might search for (e.g. "Moabite Stone"). |
| `cultures` | usually | Keys from `vocab/cultures.yaml`. Most specific first. |
| `corpus` | no | `ot`, `nt` or `both`: the part of the Bible the entry mainly bears on. It sets the corpus-dependent headings of `concept`, `practice` and `deity` articles. Leave it out unless the value inferred from the passage tags would be wrong (e.g. a Hebrew Bible deity whose few OT tags are outnumbered by synoptic parallels). |
| `date` | when meaningful | `[year]` or `[from, to]`; integers, negative = BCE, no year 0. Artefacts: date of the object. Texts: date of composition (or of main copies; say which in `author_notes`). Persons: reign or lifespan. Sites/concepts: usually omit. |
| `circa` | no | `true` when the date is approximate. |
| `scope` | yes | 1–3 sentences in an encyclopaedic register: what the entry *is*, and what it covers and leaves out. Shown to reviewers and used as the provisional summary. |
| `passages` | yes | `"REF \| REL \| note"`. See below. |
| `related` | yes | 2–8 ids from `master.txt`, all domains allowed. The most useful cross-references only; do not list everything. |
| `wikipedia` | if one exists | Exact English Wikipedia article title. Used to resolve Wikidata IDs and to find candidate images. |
| `image` | for image-bearing types | A Wikimedia Commons search phrase likely to find a photo of *this specific object/site* (e.g. `"Mesha Stele Louvre"`). `null` if no image is appropriate. |
| `location` | artefacts | Current holding institution, e.g. `"Musée du Louvre, Paris"`. Leave out if you are unsure. |
| `author_notes` | yes (2–5 items) | Concrete guidance for the article writer: key debates, consensus positions, common misconceptions to correct, things not to overstate. |
| `sources_to_check` | optional | Standard editions/translations the writer should consult (COS, ANET, RINAP, SAA, KAI, TAD, CAT/KTU, AEL for the ancient Near East; DJD, OTP, Loeb Classical Library, CIIP for Second Temple Jewish and Greco-Roman sources; etc.). **Only list items you are confident exist.** A reviewer verifies every one. |

## Passages

Format: `"<ref> | <rel> | <note>"`. Append `?` to the relation (`parallel?`) when the
connection is genuinely contested in mainstream scholarship.

* **Reference syntax**: OSIS book IDs from `vocab/books.yaml` (`Gen Exod Lev Num Deut Josh Judg Ruth 1Sam 2Sam 1Kgs 2Kgs 1Chr 2Chr Ezra Neh Esth Job Ps Prov Eccl Song Isa Jer Lam Ezek Dan Hos Joel Amos Obad Jonah Mic Nah Hab Zeph Hag Zech Mal`, plus `Sir Tob 1Macc 2Macc Bel 1En Jub`, NT `Matt Mark Luke John Acts Rom 1Cor ... Rev`). Forms: `2Kgs 18-19`, `2Kgs 18:13-19:37`, `Exod 25:9, 40`, `Ezek 14:14, 20; 28:3`, `Obad 10-14`.
* **Versification**: English (NRSV). Where the Hebrew differs, give the English reference and put the MT reference in the note ("MT 5:15").
* **Relations** (`vocab/relations.yaml`): `event`, `attests`, `parallel`, `form`, `imagery`, `concept`, `practice`, `polemic`, `language`, `realia`, `setting`.
* **Granularity**: tag the smallest passage where the connection actually lies (`Exod 21:28-36`, not `Exod 21-23`), unless the whole unit is in view (e.g. Atrahasis and `Gen 6:5-9:17`).
* **Notes**: one short clause saying *what* the connection is (≤ 20 words). They are shown to readers in passage lookups.
* **Number**: typically 3–10 per entry. Quality over quantity. Tag only connections a specialist would accept as meaningful; mark live debates with `?`; leave out fringe proposals entirely, or mention them in `author_notes` as misconceptions.
* **Accuracy**: double-check chapter:verse numbers. A wrong reference is worse than a missing one.

## Register and consensus

These entries are meant to be citable. Follow mainstream critical scholarship (as reflected in
standard reference works such as the *Anchor Bible Dictionary*, *COS*, the *Oxford
Handbook* series, and recent peer-reviewed literature). Where scholars disagree, say so
neutrally. Do not invent citations, museum numbers, or dates. If you are unsure of a detail,
leave it out or put it in `author_notes` as something to verify.

## Examples

```yaml
- id: mesha-stele
  aliases: [Moabite Stone]
  cultures: [moabite]
  date: [-840]
  circa: true
  scope: >-
    The basalt victory and building inscription of Mesha, king of Moab, found at
    Dhiban in 1868. It records Moab's liberation from Israelite control after the
    reign of Omri's dynasty, and is the longest Iron Age inscription from the
    southern Levant.
  passages:
    - "2Kgs 3:4-27 | event | Mesha's rebellion against Israel, told from the Moabite side"
    - "2Kgs 1:1 | event | Moab's rebellion after Ahab's death"
    - "1Kgs 16:21-28 | attests | Omri named as oppressor of Moab"
    - "Num 21:29 | language | Moabites as the 'people of Chemosh'"
    - "Judg 11:24 | concept | Chemosh as the national god who grants territory"
    - "Num 32:34-38 | setting | Dibon, Ataroth, Nebo, Baal-meon: towns named in the stele"
    - "Josh 6:17-21 | practice | ḥērem: Mesha devotes Nebo's population to Ashtar-Chemosh"
    - "Isa 15-16 | setting | Oracle against Moab naming many of the same towns"
    - "2Sam 8:2 | attests? | 'House of David' reading in line 31 (bt[d]wd) is debated"
  related: [chemosh, omri, moabites, dibon, herem, tel-dan-stele, ahab]
  wikipedia: Mesha Stele
  image: Mesha Stele Louvre
  location: Musée du Louvre, Paris
  author_notes:
    - Explain the discovery in 1868, the stone's breakage, and the role of Clermont-Ganneau's squeeze in its reconstruction.
    - Contrast the Moabite and biblical accounts of the revolt's timing ("in his days" vs. after Ahab's death) and outcome.
    - Note the theological parallel of a national god angry with his land (Chemosh/YHWH) and the language of ḥērem.
    - Present the "House of David" (line 31) reading as proposed and debated, not as settled.
  sources_to_check:
    - KAI 181
    - COS 2.23
    - ANET 320-321

- id: statue-of-gudea
  cultures: [sumerian]
  date: [-2150, -2125]
  circa: true
  scope: >-
    The diorite statues of Gudea, ruler of Lagash (Neo-Sumerian period), many inscribed
    with building and dedicatory texts. Statue B, seated with a temple ground-plan on
    his lap, presents the ruler as the god-chosen shepherd and temple builder.
  passages:
    - "Ezek 34:1-24 | imagery | Ruler as shepherd chosen by the deity to care for the people"
    - "Ps 78:70-72 | imagery | Divine choice of a shepherd-ruler"
    - "Exod 25:9, 40 | concept | Divinely revealed sanctuary plan (tabnît); cf. plan on Statue B's lap"
    - "Ezek 40:1-4 | concept | Visionary measured temple plan"
    - "1Chr 28:11-19 | concept | David hands Solomon the temple plan"
  related: [gudea, gudea-cylinders, shepherd-kingship, temple-building-accounts]
  wikipedia: Statues of Gudea
  image: Gudea statue B Louvre
  location: Musée du Louvre, Paris (Statue B and others); other statues in various collections
  author_notes:
    - Distinguish the excavated statues (Tello, from 1877) from unprovenanced ones of uncertain authenticity.
    - Stress that the comparison is typological. No direct influence on Ezekiel is claimed.

- id: shepherd-kingship
  cultures: [ane]
  scope: >-
    The image of the king or god as shepherd of the people, attested across the ancient
    Near East from third-millennium Sumer onward, and its use in the Hebrew Bible for
    YHWH, David, failed rulers, and an expected Davidic ruler.
  passages:
    - "Ps 23 | imagery | YHWH as shepherd providing, guiding, and protecting"
    - "Ezek 34 | imagery | Indictment of Israel's shepherds; YHWH and 'my servant David' as shepherd"
    - "2Sam 5:2 | imagery | David commissioned to 'shepherd my people Israel'"
    - "1Sam 16:11 | imagery | David chosen from the flock"
    - "Exod 3:1 | imagery | Moses called while shepherding"
    - "Jer 23:1-6 | imagery | Woe to the shepherds; righteous Branch"
    - "Isa 44:28 | imagery | Cyrus called 'my shepherd'"
    - "Mic 5:4 | imagery | Ruler from Bethlehem shepherds in YHWH's strength"
    - "John 10:1-18 | imagery | The good shepherd"
  related: [statue-of-gudea, code-of-hammurabi, royal-ideology, egyptian-kingship, gudea, david]
  wikipedia: null
  image: null
  author_notes:
    - Survey Sumerian/Akkadian royal epithets (rēʾû "shepherd"; Hammurabi's prologue and epilogue), Egyptian crook (heka) regalia and the Middle Kingdom image of the king as herdsman, and Assyrian usage.
    - Note that the image combines care with authority and accountability, which is why it suits prophetic critique of rulers (Ezek 34; Jer 23).
```
