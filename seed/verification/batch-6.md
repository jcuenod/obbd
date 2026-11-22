# Passage-tag verification: batch 6

Checked 80 entries (millstones-and-grinding through purple-dye) against the WEB text with `./obbd check-passages --per 2`. 16 entries changed: 1 tag removed, 0 added, 16 tags modified (3 relation changes, 2 changes to the disputed flag, 13 note rewrites; some tags had more than one change). No reference numbers had to change. All MT cross-references in the notes (e.g. Job 41:24 = MT 41:16, Dan 4:28 = MT 4:25, Nah 2:1 = MT 2:2, 1Kgs 5:8 = MT 5:22, 2Chr 2:7 = MT 2:6) were checked and are correct.

## Changes

- **mot**: Hos 13:14 note `'O Death, where are your plagues? O Sheol, where is your sting?'` → `... where is your destruction?'`. "Sting" comes from Paul's Greek (1 Cor 15:55), not from the Hebrew qeṭeb.
- **nabonidus**: Dan 5:2, 11, 18 (`attests`): removed `disputed: true`. That Belshazzar was the son of Nabonidus is documented, not contested, and the note already flags Daniel's "son of Nebuchadnezzar".
- **nabonidus-cylinders**: Gen 11:31-32 note `Harran and its moon-god temple, rebuilt by Nabonidus` → `Ur and Harran, moon-god cities whose temples Nabonidus restored`. The passage names both cities, and the entry's Ur cylinders are the more direct link. Genesis does not mention the temple.
- **narmer-palette**: Ps 110:5-6 note `The king shatters heads on the day of wrath` → `Kings and heads shattered (māḥaṣ) on the day of wrath; the smiting motif`. In the text the subject is "the Lord at your right hand", not the king.
- **nazareth-inscription**: Matt 28:11-15 rel `event` (disputed) → `practice` (disputed). Note `Rumour that the disciples stole Jesus' body; a link to an imperial edict proposed` → `Charge that the disciples stole Jesus' body; a link to the edict has been proposed`. The inscription's date, emperor and provenance are uncertain, so "same event" overclaims. The secure point of contact is the legal practice against tomb violation.
- **nebuchadnezzar-chronicle**: Jer 46:2 note `... in Nebuchadnezzar's accession year (605)` → `... in Nabopolassar's 21st year (605), led by crown prince Nebuchadnezzar`. ABC 5 places Carchemish before Nabopolassar's death (8 Ab), and so before Nebuchadnezzar's accession.
- **nephilim**: Ezek 32:27 note `Fallen warriors of old in Sheol (reading nōpəlîm with LXX)` → `Fallen warriors 'of old' in Sheol (LXX; MT 'of the uncircumcised'); cf. Gen 6:4`. MT already has nōpĕlîm. The LXX variant is mēʿôlām "of old" (ἀπ᾽ αἰῶνος) for MT mēʿărēlîm.
- **nineveh**: Gen 10:11-12 note `Nineveh and Calah built; 'that is the great city'` → `Nineveh among the Assyrian cities founded by Nimrod (or Asshur)`. In Gen 10:12, "the great city" refers to Calah (or Resen), not to Nineveh.
- **oaths-and-oath-formulas**: two notes.
  - Gen 24:2-9 `'Hand under the thigh: oath on the generative organ'` → `Hand under the thigh, probably touching the genitals`. This is the common interpretation, but it should not be stated as fact.
  - Amos 8:14 `Swearing by Ashimah of Samaria ...` → `Swearing by the 'guilt' (often emended to Ashima) of Samaria ...`. MT reads ʾašmat "guilt", and Ashima is an emendation.
- **oil-lamps**: Zech 4:2 note `Lampstand with seven lamps, each with spouts (lit. 'lips')` → `Seven lamps with 'seven and seven' spouts (mûṣāqôt); cf. multi-spouted lamps`. Mûṣāqôt means "spouts" or "pipes" (from yṣq "pour"). "Lips" is the NRSV rendering, not a literal one.
- **petra-and-sela**: Isa 42:11 (`setting`): added `disputed: true`. Whether selaʿ here is a place name, and which site it would be, is as uncertain as in 2Kgs 14:7, which is already marked disputed.
- **phoenician-seafaring**: 1Kgs 22:48 rel `event` → `practice`. No extrabiblical source narrates the wreck, and the entry is a concept entry about Red Sea ventures.
- **pig-avoidance**: Acts 10:9-16 note `Peter's vision abolishing food distinctions` → `Peter's vision of unclean animals, applied in Acts to Gentile inclusion`. Acts 10:28 applies the vision to people. Whether it abrogates food laws is debated.
- **plague-prayers-of-mursili**: Lam 5:7 note `Children bear the sins of the fathers ('the father's sin comes upon the son')` → `Children bear their fathers' sins; cf. Muršili's 'the father's sin comes upon the son'`. The quoted phrase is Muršili's, not Lamentations'.
- **pontius-pilate**: Luke 13:1 rel `event` (disputed) → `attests` (disputed). Note wording `..., not attested elsewhere` → `...; incident not attested elsewhere`. An incident known from no other source cannot be tagged as the same event as another source. The disputed flag is kept for the historicity question, as author_notes requests.
- **proto-sinaitic-script**: removed `Exod 17:14; 24:4; 34:27-28 | setting? | Writing in the Sinai traditions; date and relevance debated`. Linking Moses' writing in Sinai to the Serabit el-Khadim inscriptions is a fringe, mostly apologetic, argument. The two acrostic tags remain.

## Flag for expert review

- **nazareth-inscription**: even with the softer relation, Matt 28:11-15 may be too speculative to keep. The Kos-marble isotope result (2020) weakens any Palestinian context.
- **pekah, nebuchadnezzar-ii, necho-ii**: these person entries use `event` for passages that no extrabiblical source narrates (e.g. Pekah 2Kgs 15:25; 2Chr 28:5-8). I left them as they are. The project should decide whether `event` on person entries means "event in the person's career" or strictly "co-attested event".
- **nimrod**: 1Chr 1:10 is tagged `attests`, which is awkward for a biblical-only figure. It also partly duplicates Gen 10:8.
- **narmer-palette**: Josh 10:24 (`practice`, feet on necks) relies on general Egyptian trampling iconography more than on the palette itself.
- **murashu-archive**: Ezra 8:15-17 (Casiphia) is a loose fit. The Murašû texts are from Nippur, and Casiphia is unlocated.
- **mummification**: Exod 13:19 (Joseph's bones) is only marginally about embalming.
- **mizpah**: the Jaazaniah seal (2Kgs 25:23) and the attribution of the Iron II wall to Asa (1Kgs 15:22) are both correctly marked disputed. The Nebi Samwil alternative identification is noted only in author_notes.
- **nephilim**: 1 Enoch and Jubilees tags were not checked (text unavailable).
