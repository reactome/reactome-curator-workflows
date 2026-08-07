# Reactome EHLD Builder — Figma plugin

A Figma plugin that builds an EHLD skeleton from an **approved placement plan**,
using only art fetched live from the **Reactome Icon Library**, and exports it
with the settings the EHLD spec requires. It is the Figma-side companion to the
`/curation-build-illustration` skill.

> **Status: untested against a live Figma instance.** Every piece that can be
> checked outside Figma has been (JSON/JS syntax, plan validation, label
> sanitising, build structure with a stubbed Figma API, CORS on all three
> Reactome endpoints). The Figma Plugin API calls themselves — `createNodeFromSvg`,
> `rescale`, `exportAsync` — have not been exercised in the real editor. Expect to
> shake out small issues on first run; see **Known risks** below.

---

## Why a plugin, and where it sits in the workflow

The skill already composes a spec-compliant SVG directly. This plugin does not
replace that — it replaces the **hand-tuning step**. The skill's own Limitations
section says automatic placement "will need hand-tuning in Illustrator"; this
makes Figma an alternative surface for that, with the EHLD scaffolding built for
you and the export settings pre-wired.

The division of responsibility is deliberate:

| Concern | Owner | Why |
|---|---|---|
| Resolving an entity → an icon | `reactome_icons.py map` / `search` | Deterministic, auditable, offline for accessions |
| Curator approval of the icon choices | Phase 1 Icon Map (**unchanged**) | The human gate stays where it is |
| Checking the plan before it is built | `reactome_icons.py check-plan` | Catches a fabricated R-ICO id before it reaches the canvas |
| Layout / hand-tuning | **this plugin** | What Figma is actually good at |
| Spec compliance of the result | `reactome_icons.py validate` | Closes the loop on the export |

**The plugin cannot invent an icon.** It has no icon-resolution logic of its
own: an `R-ICO-######` id arrives in the plan (or from an explicit Icon Library
search hit) or nothing is drawn. A plan icon that fails to download is reported
as a gap and skipped — never substituted with a drawn shape.

---

## Install

1. In Figma: **Menu → Plugins → Development → Import plugin from manifest…**
2. Select `manifest.json` in this directory.
3. Run it from **Plugins → Development → Reactome EHLD Builder**.

No build step — `code.js` is plain ES2017 JavaScript, not TypeScript, so there
is nothing to compile. The manifest declares `networkAccess` for
`https://reactome.org` only; Figma will show that domain when you install.

**Use the Figma desktop app if you can.** The spec requires **Arial Bold**,
which is a system font: available to the desktop app on macOS/Windows, but not
to the browser editor unless you have installed the Figma font helper. The
plugin falls back to Helvetica then Inter and *tells you it did* — it will not
silently ship a non-spec font.

---

## Use

### 1 · Build from an approved plan

Paste the placement plan JSON (see `example-plan.json`) and press **Build EHLD**.
The plugin downloads each distinct icon once, then builds:

```
<frame R-HSA-#######>            1366x768, no background fill
  ├─ CELL                        compartment icons (back)
  ├─ REGION-R-HSA-#######        one per subpathway
  │    ├─ <entity icons>         named by R-ICO id
  │    ├─ ANALINFO               #C6C6C6 box + "XXX/YYY", group opacity 0.01
  │    └─ OVERLAY-R-HSA-#######  label box ONLY (#0F82BC, r8, Arial Bold 12, white UPPERCASE)
  ├─ ARROWS                      empty, for you to draw into
  └─ TEXT                        empty, for you to draw into
```

Labels are uppercased and Greek letters spelled out (`α` → `ALPHA`) per spec.
`ANALINFO` uses `opacity="0.01"`, matching production EHLDs — see the note in
`../SKILL.md`.

**Check the plan first**, from the skill's directory:

```sh
python3 reactome_icons.py check-plan <plan>.json --online
```

`--online` confirms every `R-ICO` id resolves to a real icon. A well-formed but
fabricated id like `R-ICO-999999` passes every offline check and is only caught
here.

### 2 · Browse the Icon Library

A live search over the ContentService for spot inserts while laying out. Results
show the icon, its name, its `R-ICO` id and its categories. This is a
convenience for browsing — the sanctioned path for anything that ends up in the
figure is still the approved Icon Map, so that the manifest CSV can record how
each icon was resolved.

### 3 · Export

**Export EHLD as SVG** exports the selected frame with:

| Setting | Value | Why |
|---|---|---|
| `svgIdAttribute` | `true` | Layer names become SVG ids. **Load-bearing** — without it `REGION-`/`OVERLAY-`/`ANALINFO` are lost and the EHLD is not interactive in the Pathway Browser. Equivalent to Illustrator's *Object IDs = Layer Names*. |
| `svgOutlineText` | `false` | **Load-bearing.** Figma outlines text by default; the spec explicitly forbids converting text to shapes. Equivalent to Illustrator's *Font = SVG*. |
| `svgSimplifyStroke` | `false` | Leaves the library art's strokes alone. |

Then validate the export:

```sh
python3 reactome_icons.py validate <exported>.svg
```

Fix every error before the file goes to a curator.

---

## Plan format

```jsonc
{
  "pathway":  { "stId": "R-HSA-109581", "name": "Apoptosis" },
  "canvas":   { "width": 1366, "height": 768 },        // optional; this is the default
  "compartments": [                                     // drawn first, behind everything
    { "icon": "R-ICO-013570", "name": "cell",
      "category": "cell_element", "x": 90, "y": 90, "width": 560 }
  ],
  "subpathways": [                                      // two or more — that is what makes it an EHLD
    { "stId": "R-HSA-109606",
      "label": "Intrinsic Pathway for Apoptosis",       // uppercased automatically
      "labelPos": { "x": 120, "y": 620 },
      "entities": [
        { "icon": "R-ICO-014273", "name": "BAX/BAK pore", "category": "protein",
          "accession": "Q07812", "db": "UNIPROT",       // provenance, for the manifest CSV
          "x": 300, "y": 200, "width": 70 }
      ] }
  ]
}
```

- Coordinates are top-left origin in canvas user units.
- `width` **or** `height` scales the icon proportionally from its own `viewBox`;
  `scale` sets a factor directly. Omit all three for 1:1.
- `accession`/`db` are carried for the manifest CSV, not used for drawing.
- ST_IDs may be `R-HSA-PLACEHOLDER-<n>` for a pathway that does not exist yet —
  `validate` will remind you to replace them before ingestion.

---

## Known risks

Things to check on the first real run, and what to do about them:

- **Arial.** In the browser editor you will get the Inter fallback and a warning.
  Fix the font family before final export, or use the desktop app.
- **`createNodeFromSvg` fidelity.** Figma re-interprets SVG into its own node
  model on import. Gradients, clip-paths and masks in the library art generally
  survive, but a round trip is not guaranteed byte-identical — unlike
  `reactome_icons.py place`, which copies path data verbatim. **If exact
  preservation of the library art matters more than layout convenience, use
  `place` and skip Figma.** This is the real trade-off of the Figma route.
- **Mode A (modifying a published EHLD).** Importing a published EHLD into Figma
  and re-exporting rewrites the whole file, which conflicts with the skill's
  "preserve the base verbatim" rule. **Do not use this plugin for Mode A** — use
  `place --into` + `validate`, which are additive by construction.
- **No LOGO or ICON legend.** These are standard Reactome furniture; the plugin
  creates neither rather than fabricating them. Copy them in from a Reactome
  template. `validate` warns when they are missing.
- **Arrows.** Draw them in the `ARROWS` layer, never inside an `OVERLAY-` group —
  `validate` treats that as an error.

## Licence / attribution

Icons are from the Reactome Icon Library, **CC-BY 4.0**. Any figure using them
must credit Reactome and the icon designers; the skill's manifest CSV captures
per-icon designer, curator and ORCID for that credit line.
