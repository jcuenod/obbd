# Passage-tag verification: batch 7

Checked 83 entries (qedarite-silver-bowl through taanach-cult-stand; list in `.cache/digests/verify-7.txt`) against the WEB text with `./obbd check-passages --per 2`. All MT/English versification notes in the batch were checked and are correct. Nine entries were changed: 10 tags changed, 1 removed, none added.

## Changed entries

- **rabbah**: `2Sam 12:26-31` note "David captures Rabbah, the 'city of waters', and Milcom's crown" → "... and the crown of malkām ('their king' or Milcom)". MT reads *malkām* "their king". Milcom is a reading based on the LXX, and the old note presented it as the text.
- **royal-steward-inscription**: `Josh 6:26` note "Curse on whoever undoes a site" → "Curse on whoever rebuilds Jericho: the same 'cursed be the man who...' formula". The verse curses whoever *rebuilds* Jericho. The old note misdescribed it and did not say what the language link is (*ʾārûr hāʾîš ʾăšer*).
- **sabbatical-year**: `1Macc 6:49, 53` rel `event` → `practice`. The entry is about an institution, and the verses are evidence that it was observed. No source in the entry narrates the same event.
- **satan-the-adversary**: `Wis 2:24` note "...; first link to Gen 3" → "...; probably an early identification of Eden's serpent". The verse does not name the serpent. Whether it is the *first* such link (compare the Enochic traditions) cannot be shown, so "first" overclaimed.
- **seven-day-patterns**: `Gen 8:10-12` note "Dove sent out at seven-day intervals; cf. Gilgamesh XI" → "...; cf. Gilgamesh XI, birds released on the seventh day". In Gilgamesh XI the birds are not sent out at seven-day intervals. Utnapishtim releases the dove when the seventh day arrives. The note now says where the parallel actually lies.
- **shurpu**: `Deut 27:15-26` note "Curses on secret offences: parents dishonoured, boundaries moved, neighbour's wife" → "... parents dishonoured, boundaries moved, a neighbour struck in secret". Deut 27:15-26 has no curse about a neighbour's wife (v. 20 concerns the *father's* wife). Striking a neighbour "in secret" (v. 24) is the apt secret-offence example.
- **slavery**: `Jer 34:8-22` rel `event` → `practice`. This is the same reasoning as for sabbatical-year: the entry is about a practice, not a source narrating the event.
- **soleb-shasu-inscription**: `Deut 33:2`, `Judg 5:4-5` and `Hab 3:3` now have `disputed: true`. The `Deut 33:2` note "Shasu lands lie in this southern region" → "the Shasu of Yhw are often located in this region". Where "Shasu-land Yhw" lay is contested (some place it in Seir/Edom, others further north, e.g. Astour), so the link to southern-origin texts is not settled. This now matches the parallel `shasu` entry, which already marks these tags `concept?`.
- **stele-of-the-vultures**: removed `Deut 19:14 | practice | Respect for boundaries; the stele concerns a disputed border`. A law against moving a neighbour's landmark has no meaningful connection to a war between city-states over a border, so the tag was trivially weak.

## Flag for expert review

- **qos** `2Chr 25:14-15` (`attests`): the passage speaks of "the gods of the people of Seir" but does not name Qos. `attests` may overstate the link, and `setting` or a note such as "presumably including Qos" might be better.
- **rassam-cylinder** `Ezra 4:9-10` (`event`): Osnappar = Ashurbanipal is standard. The annals narrate the sack of Susa, but not the resettlement in Samaria that Ezra mentions. `attests` may fit better than `event`.
- **sefire-treaties** `Mic 1:4` (`imagery`): Sefire I A's wax-burning curse is a ritual simile, and "melting like wax" is a common biblical theophany image (cf. Ps 68:2; 97:5). This is a weak connection. Kept.
- **samaritan-origins** `Ezra 4:1-5`, `Neh 13:28`, `2Macc 6:2` (`event`): `event` is used for a people entry where no external source is in view. This is consistent with the entry's historical scope, but `setting` may be more accurate. Whether the Ezra 4 "adversaries" are proto-Samaritans is also debated.
- **royal-annals-and-historiography** `1Kgs 14:25-26` (`event`): the same rel question for a concept entry. The note points to the Karnak list, so the tag was kept.
- **shalmaneser-iii** `1Kgs 16:29-34`: the range includes Hiel's rebuilding of Jericho (v. 34), which is irrelevant. `1Kgs 16:29-33` would be tighter. Kept, because the unit is Ahab's regnal introduction.
- **samaria-ostraca** `2Kgs 14:23-29`: the dating of the ostraca to Jeroboam II is the majority view, but some prefer Joash or Menahem. The note says "probably".
