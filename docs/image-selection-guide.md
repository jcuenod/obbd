# Image selection guide

Images are chosen per entry from Wikimedia Commons candidates, then downloaded with
full attribution by `./obbd media-fetch`. This guide applies to people and to AI agents.

## Inputs

`./obbd media-candidates` writes `.cache/candidates/<entry-id>.json`, containing the entry's
title, type, scope, search query, and `candidates`: freely licensed Commons files, each with
`title`, `description`, `artist`, `license_short`, `width`/`height`, `categories`, `thumb`
(a 1600 px URL), and `sources`. `wp-lead` means the file is the lead image of the
entry's Wikipedia article, `wp-article` means it appears in that article, and
`commons-search` means it came from a keyword search. Files with non-free licenses have
already been removed.

To search further, use `./obbd media-search "query"`. It prints JSON lines with license
metadata. `./obbd media-info "File:Name.jpg"` checks a specific file.

To look at a candidate before choosing, download a small version (replace `/1600px-`
in the `thumb` URL with `/400px-`) and view it.

## What to choose

For each entry, pick **one primary image** and, optionally, **up to two gallery images**
where they add real information (another face of the object, a legible detail, a drawing
or squeeze of an inscription, a site plan).

Order of preference:

1. **Artefacts**: a photograph of the actual object in its current collection. A cast or replica is acceptable only if the original is unavailable, and the caption must say so. A clear line drawing of the inscription makes a good gallery image.
2. **Texts and corpora**: a photograph of the best-known manuscript or tablet.
3. **Sites**: a photograph of the archaeological remains (aerial or overview preferred), not modern city scenes or maps. A plan may go in the gallery.
4. **Persons**: an ancient depiction (relief, statue, coin) of that person. Do not use modern artistic imaginings.
5. **Deities and concepts**: an ancient artefact that illustrates the topic (e.g. Nut arched over Geb for cosmology; a Lamassu for cherubim). Modern paintings, diagrams, and reconstructions are acceptable only when no ancient image fits, and the caption must say what they are. If nothing good exists, choose nothing.

Reject images that are:

* watermarked, heavily cropped, blurred, or smaller than about 640 px on the long side (unless nothing else exists);
* of the wrong object, such as another statue of Gudea when the entry is about one specific statue, a different stele from the same site, or a museum gallery view where the object is hard to see;
* modern art, maps, or diagrams when a photograph of the real thing is available;
* collages that include unrelated images.

## Captions

One sentence, factual, in this shape: **what it is, material/date if known, (holding
institution or site)**. For example:

* "The Mesha Stele, basalt, c. 840 BCE (Musée du Louvre, Paris)."
* "Tel Lachish from the southwest, showing the Iron Age city mound."

Only state facts that are in the file description or that you are certain of. Do not
invent accession numbers.

## Output format

Selections go into a YAML file, keyed by entry id:

```yaml
mesha-stele:
  - file: "File:Mesha stele (Louvre, AO 5066).jpg"
    caption: "The Mesha Stele, basalt, c. 840 BCE (Musée du Louvre, Paris)."
    role: primary
  - file: "File:Mesha Stele drawing.jpg"
    caption: "Drawing of the inscription after the 1870 reconstruction."
    role: gallery
lachish-reliefs:
  - file: "File:Lachish relief, British Museum 1.jpg"
    caption: "..."
    role: primary
    depicts: [sennacherib-campaign-701, assyrian-siege-warfare]   # other entries this image also illustrates
some-entry-with-nothing-suitable: []   # reason: only modern maps available
```

Then run `./obbd media-fetch <file>`. It re-checks every license against Commons,
downloads at most 1600 px wide, writes `media/<id>.yaml` with attribution, and links the
image to the entry (and to any `depicts` entries).
