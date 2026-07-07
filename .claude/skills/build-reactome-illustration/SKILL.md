---
name: build-reactome-illustration
description: Build a new biological pathway illustration in Reactome's Enhanced High-Level Diagram (EHLD) style from a curator's written description or an example image/sketch. Every biological image part comes SOLELY from the Reactome Icon Library (searched and downloaded live via ContentService); the assistant composes a labelled 1366x768 SVG with pathway and subpathway labels following the official EHLD specification. Use when a curator wants a publication- or browser-ready pathway figure assembled from sanctioned Reactome icons rather than drawn from scratch.
---

# Build Reactome Illustration Skill

## Purpose

Produce a **new biological illustration in Reactome's EHLD (Enhanced High-Level
Diagram) style** from either a written description or an example image / sketch
the curator supplies. The illustration represents one or more pathways and
subpathways and is labelled accordingly.

**The single most important rule:** every *biological* image part — every
protein, complex, small molecule, cell, cell element, receptor, ion channel and
tissue — must be an actual icon fetched live from the **Reactome Icon Library**.
The library is the sole source of biological art. You may add only *style
scaffolding* around those icons (subpathway label boxes, `ANALINFO` boxes,
`<text>` labels, connecting arrows/lines, and invisible clickable-area shapes) as
defined by the EHLD spec below — but **not** a full-canvas background. You
may **never** hand-draw a biological entity, invent an icon id, or substitute a
generic shape for an entity that has no library icon. When the library has no
suitable icon, that is a **gap** to be surfaced to the curator, not filled.

This is a pre-figure convenience skill. The output SVG is a faithful,
attributed, EHLD-compatible draft that the curator refines in Adobe Illustrator
(or equivalent) and, if it is to be ingested by the Pathway Browser, finalises
against the live pathway hierarchy.

## Invocation

    /build-reactome-illustration

No arguments. The skill prompts for the inputs below.

## Two entry modes

The skill opens by determining how the curator is specifying the image:

- **Mode A — Written description.** The curator describes the desired image in
  words (the biology, the entities, the flow, the groupings). Proceed directly
  to Phase 1 with that description.

- **Mode B — Example image or sketch.** The curator uploads a reference image,
  hand sketch, whiteboard photo, or an existing figure. Read the image
  carefully — identify every biological entity, its type, the compartments, the
  directional flow, and how entities are grouped into subpathways. Restate your
  interpretation and proceed to Phase 1. You are re-creating the *content and
  structure* of the reference using Reactome icons and Reactome style — not
  tracing or copying the reference's own artwork.

Modes can be combined (a sketch plus clarifying words).

## Required inputs — ask before doing anything else

Do not proceed until you have:

1. **A working directory for this illustration request (keeps the repo clean).**
   To keep this repository clean, every input and output for this run lives in one
   dedicated directory — **never scattered into the repo.** Ask the curator
   **where** it should live and **what** to name it, then **create it if it does
   not exist.** This directory is where the curator drops any sample / reference
   images (the Mode B image/sketch), and it is where every output artefact is
   written (the SVG, manifest, gaps file, and `icons/` — see Outputs). Use one
   directory per request so each illustration's inputs and outputs stay together
   and self-contained.
   - **Where:** default is the gitignored `illustrations/<slug>/` (git already
     ignores `illustrations/`, so outputs are never committed), or any absolute
     path outside the repo (e.g. `~/reactome-work/<slug>/`).
   - **What to name it:** suggest `<slug>` — the pathway name lowercased with
     non-alphanumerics collapsed to single hyphens — if the curator has none.
   - In **Mode B**, confirm the sample image(s) are in this directory (or ask the
     curator to place them there) and read them from it.
2. **The image specification** — the Mode A description and/or the Mode B
   image/sketch (the sample image(s) in the project directory from step 1).
3. **The pathways and subpathways to represent and label** — the exact names as
   they should appear on the figure. Ask for the Reactome hierarchy names where
   they exist; a subpathway label should match the name in the Reactome
   hierarchy.
4. **(Optional) target Reactome pathway ST_IDs.** If the illustration is meant
   to become the EHLD for existing pathway(s), collect the `R-HSA-#######`
   ST_ID(s). These drive the output filename and the mandatory region `id`
   attributes (see EHLD spec). If the curator has no ST_ID yet (brand-new
   pathway), use placeholder tokens `R-HSA-PLACEHOLDER-<n>` and tell the curator
   to replace them before Pathway Browser ingestion.
5. **(Strongly recommended) external accessions for the entities** — UniProt for
   proteins, ChEBI for small molecules, GO for cellular components/functions, CL
   for cell types, UBERON for tissues, Complex Portal for complexes. These let the
   skill resolve icons *deterministically* via `map` instead of guessing by name,
   which is the single biggest accuracy win. Curators normally have them already;
   ask for any that are missing.

Do not ask about canvas size, colours, or fonts — those are fixed by the EHLD
spec below.

## The Icon Library is the sole source of parts

All biological art is fetched with the bundled helper, which talks to the public
Reactome ContentService and static icon endpoint (no API key) and reads the
bundled accession→icon mapping tables:

    python3 reactome_icons.py map    "<accession>" [--db DB]     # DETERMINISTIC — prefer this
    python3 reactome_icons.py search "<entity name>" [--category CAT] [--max N]
    python3 reactome_icons.py fetch  <R-ICO-id> [--outdir ./icons] [--png]
    python3 reactome_icons.py info   "<entity name>"     # single best match + attribution

**`map` is the preferred match step — use it whenever you have an accession.** It
resolves an external id (UniProt, ChEBI, GO, CL, UBERON, Ensembl, Complex Portal,
InterPro, KEGG, MeSH, …) straight to the exact icon(s) via the bundled
`icon_mappings/<DB>2Icon.txt` tables — **no network, no fuzzy matching, no
name-guessing**. Reactome curation almost always has these accessions (UniProt for
proteins, ChEBI for small molecules, GO for cellular components/functions, CL for
cell types, UBERON for tissues), so accession lookup is both the most accurate and
the most hallucination-proof path. It accepts prefixed or bare ids (`CHEBI:16020`
or `16020`, `Q99638`) and returns a JSON array of `{db, accession, stId, iconName,
svgUrl, pngUrl}`. An empty result is a **gap**, never a licence to invent an icon.
A single accession may map to several icon variants (e.g. UBERON:0001981 → four
"Blood vessel" icons) — pick the best and note the alternatives.

`search` (name-based, live ContentService) is the fallback when no accession is
available. It returns, per candidate: the stable id (`R-ICO-######`), `iconName`,
`categories`, external `references` (e.g. UniProt), the Reactome
PhysicalEntities the icon is mapped to (`mappedEntities`), a short `summation`,
attribution (`designer`, `curator`, `curatorOrcid`), and the direct `svgUrl` /
`pngUrl`.

**Category tokens** (pass to `--category`): `protein`, `compound`, `cell_type`,
`cell_element`, `receptor`, `ion_channel`, `human_tissue`. These map to the
**seven Icon Library categories** in the official **`Icon_Library_Guidelines.pdf`**
(Cell elements, Cell types, Compounds, Human tissue, Ion channels, Proteins,
Receptors — the metadata token for a transporter-type channel is `transporter`).
Consult that PDF to understand how each icon type is drawn (e.g. proteins =
rounded rectangles; compounds = octagons/hexagons with the chemical symbol;
ion channels = funnels crossing the membrane; human tissue = simple "toy-like"
backgrounds) — it helps you pick the right category, judge match quality, and
describe a gap precisely when you request a new icon.

**Absolute no-fabrication rule.** An icon id, name, or download URL may enter the
illustration ONLY if `map`/`search`/`fetch` returned it in this run. Never emit an
R-ICO id from memory, never guess a download URL, never draw a replacement for a
missing icon. If `map`/`search` returns nothing usable, record a gap. Accession
lookup via `map` is the strongest guard here — prefer it.

## Workflow

### Phase 1 — Interpret and plan (build the icon map, then STOP)

1. Decompose the specification into: the **compartments** in play (cell,
   membranes, nucleus, organelles — each becomes a compartment layer built from a
   cell-element icon, see `EHLD_layout_reference.md`), the list of **subpathways**
   (each becomes a labelled region), and within each, the ordered list of
   **biological entities** — noting each entity's **compartment** and whether it is
   an integral-membrane / transported entity — plus the **directional flow** /
   relationships between them.
2. For **each** entity **and each compartment**, resolve an icon:
   - **If you have an accession** (UniProt, ChEBI, GO, CL, UBERON, …), run
     `reactome_icons.py map "<accession>"` first — this is deterministic and
     exact. Ask the curator for accessions if the spec is missing them; it is the
     single best way to guarantee the right icon and avoid hallucination.
   - **Otherwise** run `reactome_icons.py search` (use `--category` to
     disambiguate — `cell_element` for compartments like cell, membrane, nucleus,
     organelles; try synonyms — gene symbol, protein name, common name).
   Choose the single best match, preferring an icon whose `mappedEntities` or
   `references` line up with the intended Reactome entity. Record the chosen
   `R-ICO-######`, name, category, the accession/DB used (or search term), and
   attribution. (The canonical compartment icons are `R-ICO-013570` = cell and
   `R-ICO-013121` = nucleus — still confirm them via `map`/`search`, never emit an
   id from memory.)
3. Entities with **no** acceptable match become **gaps** — list them explicitly;
   do not invent art for them.
4. Present an **Icon Map** table for curator approval:

   | Subpathway | Entity (as described) | Compartment | Accession (DB) | Chosen icon | R-ICO id | Category | Confidence | Notes |

   The **Accession (DB)** column records the id and table that resolved the icon
   via `map` (e.g. `P60709 (UNIPROT)`), or `search:"<term>"` when name search was
   used — this makes every match auditable.

   List compartment/membrane icons as their own rows too. Note in **Notes** any
   entity that is integral-membrane or transported across a membrane, since that
   drives placement (see `EHLD_layout_reference.md` §6). Add a separate **Gaps**
   list (entities with no library icon) and a one-line layout sketch (how
   compartments and subpathways/regions will be arranged on the canvas).

5. **STOP and wait for curator approval.** Icon selection is where mismatch and
   hallucination risk lives — do not render until the curator confirms or edits
   the Icon Map. If the curator accepts gaps as-is, they will be omitted (or
   left as a labelled empty slot) — never back-filled with drawn shapes.

### Phase 2 — Fetch and compose (after approval)

1. `fetch` every approved icon into `<project-dir>/icons/` (pass
   `--outdir <project-dir>/icons`; SVG only, add `--png` only if the curator
   wants raster previews).
2. Compose one EHLD-compliant SVG per the spec below and the layer order in
   `EHLD_layout_reference.md` §2: lay down `BG`, then compartment layers, then
   entity icons placed inside their compartments (membrane proteins straddling the
   band), then `TEXT`, `ARROWS`, `LOGO`, the analysis `ICON` legend, and finally
   the `REGION-`/`OVERLAY-` subpathway groups. Embed each downloaded icon verbatim
   (see "Embedding icons").
3. Write every artefact into the **project directory** from step 1 of Required
   inputs (see Outputs) and report.

## EHLD style specification (AUTHORITATIVE — the official Reactome specs govern)

> **These are the top-level, authoritative rules for building an EHLD.** They are
> transcribed from the two official Reactome documents bundled in this skill
> directory, which supersede any other guidance here if they ever conflict:
> - **`EHLD_Specs_and_Guidelines.pdf`** — "EHLD Specs & Guidelines" (how to build a
>   Pathway-Browser-compatible EHLD; Reactome Pathway Browser v3.4+).
> - **`Icon_Library_Guidelines.pdf`** — "Icon Library Guidelines" (how the icons
>   that make up an EHLD are constructed and categorised).
>
> `EHLD_layout_reference.md` is the *empirical companion* — layout patterns
> observed in the 217-file production corpus. Where the corpus and the official
> spec differ (e.g. a full-canvas white background rect in exported files), **the
> official spec wins** and the corpus trait is treated as an export artifact.

**What an EHLD is.** An interactive SVG of a *higher-level* pathway that contains
**two or more subpathways as active regions**. An active region is a group of
shapes representing one subpathway that the user can hover, select, navigate from,
and (for the label) overlay with analysis results. Anything not annotated as an
active region is a **decorator** — purely aesthetic, non-interactive.

**Format & colour.** SVG only. Raster/bitmap content is strongly discouraged (it
bloats files and defeats resolution-independent zoom) — keep everything vector.
**RGB** colour mode.

**Canvas.** Create the artboard at **1366 px wide × 768 px high** (the official
authoring size). *Exported* EHLDs typically carry a 15 px bleed on each side, so
the distributed root `<svg>` is often **1396 × 798** (`viewBox="0 0 1396 798"`) —
that is an export artifact; author within 1366×768 and keep all content inside it.

**Background.** **Do not** put a background covering the whole image — Reactome
displays EHLDs in a blank, zoomable space. *Compartments and other necessary
backgrounds are allowed* (a cell, a membrane, an organelle); just avoid
"unnecessary" full-canvas fills. If a needed background is too big to fit, draw
only a small part of it with clear, well-defined boundaries (cf. the blood vessel
in the Hemostasis EHLD). (Exported corpus files may contain a white 1366×768 rect
— an Illustrator artboard artifact; do not author one deliberately.)

**Filename.** The Reactome ST_ID of the pathway diagram + `.svg`, e.g.
`R-HSA-109581.svg`. **Exactly one EHLD per high-level pathway diagram.** With
multiple/placeholder IDs, use the primary pathway's ST_ID (or
`R-HSA-PLACEHOLDER-1.svg`) and flag it.

**Text.** Use real `<text>` SVG elements — **never** convert text to groups of
shapes/outlines. Avoid Greek/Unicode characters: spell the word out in lowercase
(`alpha`, not `α`). Text colour depends on position:
- **Pathway/subpathway labels** and text **inside any coloured shape** (compound,
  protein, cell): **white, UPPERCASE**.
- **Process descriptions**, and text for a **receptor / cell element / process
  that sits outside any shape**: **black, lowercase** (receptor acronyms may keep
  their capitals).

**Pathway / subpathway labels.** Centred text, **white, UPPERCASE, Arial Bold
12 pt**, inside a **rounded rectangle, 8 px corner radius, min width 170 px,
height 30 px (single line) / 43 px (two lines)**, fill **`#0F82BC` (RGB
15,130,188)**. Use the subpathway name exactly as it appears in the Reactome
hierarchy; on any discrepancy, contact the pathway's author/curator.

**Analysis Information Label (`ANALINFO`) — MANDATORY, one per pathway label.**
Displays hit-element counts and FDR. Annotate the group id/layer name `ANALINFO`.
Put the placeholder text **`XXX/YYY`** inside. Centred, UPPERCASE, **Arial Bold
9 pt, white**. Box = rounded rectangle **8 px radius, min width 170 px, height
20 px**, fill **`#C6C6C6` (RGB 198,198,198)**. **Set the group's opacity to 0 %**
but leave the inner shapes/text at 100 %. Place it beside its pathway label, on
the side *opposite* the content (label above content → ANALINFO above the label).

**Active regions (interactivity).** Annotate via the `id` attribute of a group:
- `id="OVERLAY-R-HSA-#######"` — the group holding the subpathway's **label box**
  only. Selectable **and** analysis-overlayable. **MANDATORY** for every
  subpathway. Must **NOT** contain arrows.
- `id="REGION-R-HSA-#######"` — an **optional** larger selectable group for the
  subpathway's content; **may** include arrows pointing to/from it. If both are
  used for a subpathway, the `REGION-` group must **contain** the `OVERLAY-` group.
- Use the subpathway's real ST_ID; use a `R-HSA-PLACEHOLDER-<n>` token if none
  exists yet and flag it.

**Extending clickable area (optional).** To make a subpathway easier to select,
place a **white shape at 0 % opacity beneath** its elements to bridge gaps between
individual graphics — reduces cursor flicker and enlarges thin targets. Use with
caution; overly large invisible areas mislead users.

**Layer hierarchy.** Put all **arrows and neutral text** in a group at the **top**
of the layer hierarchy (front-most); put **decorators / background** we don't want
highlighted or clickable in a group at the **bottom**.

**Reactome logo.** Always **50 % opacity**.

**Edges / cut elements.** Portray every element in full where possible. If an
element must be cut at the canvas edge and a clean cut is hard, fade it with a
**gradient** so the canvas boundary stays clean.

**Export settings (Adobe Illustrator — tell the curator).** Export As → SVG with:
**Styling = Internal CSS**, **Font = SVG**, **Images = Preserve**,
**Object IDs = Layer Names** (this preserves the `REGION-`/`OVERLAY-`/`ANALINFO`
ids), **Decimal Points = 3**, and both **Minify** and **Responsive** ticked.

## Compartments, membranes, and entity placement (from the production corpus)

These conventions were extracted from the **217 live production EHLDs** and are
detailed, with evidence, in **`EHLD_layout_reference.md`** (the layout companion
to this file). Read that file before composing. The essentials:

- **Layer stacking order** (back → front), using the corpus's real layer names:
  `BG` → **compartment layers** → **entity icons** → `TEXT` → `ARROWS` → `LOGO` →
  `ICON` (analysis legend, with `50`/`75`/`100` children) →
  `REGION-`/`OVERLAY-` subpathway groups. Emit groups in this order so
  compartments sit behind their entities and arrows/labels sit on top.

- **Compartments are library icons, not hand-drawn shapes.** The canonical ones:
  **`R-ICO-013570`** is a whole **cell** (its inner art already contains a
  `MEMBRANE` and a `CYTOPLASM`), and **`R-ICO-013121`** is the **nucleus** (drop it
  inside the cell for the nucleoplasm). Fetch them the normal way and place them as
  the compartment layer — never redraw them. For multi-cell scenes, repeat the cell
  icon (id-namespaced `R-ICO-013570_2`, `_3`, …), each in its own `membrane`/`CELLS`
  sub-group.

- **Membranes** are drawn as a three-part bilayer band: `membrane BG` (filled band)
  + `membrane LINE` (solid leaflet) + `membrane DOTED` (dotted leaflet) — or taken
  directly from the cell icon's inner `MEMBRANE`.

- **Place each entity inside the compartment icon matching its Reactome
  `[compartment]`:** nucleoplasm entities over the nucleus icon; cytosolic entities
  over the cytoplasm; organelle-lumen entities over the organelle icon;
  extracellular entities outside the outermost membrane.

- **At/across membranes (biologically meaningful placement):** receptors, ion
  channels, and transporters **straddle the membrane band** (part extracellular,
  part cytosolic, centred on the `membrane LINE`) — never floating fully in the
  cytosol or fully outside. Ligands sit extracellular touching the receptor's outer
  face; effectors sit cytosolic. **Transport across a membrane** = draw the cargo
  icon on *both* sides of the band and connect them with an arrow that crosses it
  (arrow lives in the `ARROWS` layer, never in an `OVERLAY-` group).

## Embedding icons into the composite SVG

Each downloaded icon is a standalone `<svg width height viewBox>` whose inner art
is wrapped in `<g id="R-ICO-######"><g id="ICONNAME">…</g></g>`. To place one on
the canvas without corrupting coordinates or colliding ids:

- Wrap each placed icon in a positioned, scaled group:
  `<g transform="translate(X,Y) scale(S)"> …icon inner <g>… </g>`, scaling by the
  icon's own `viewBox` so its intrinsic proportions are preserved.
- **Namespace ids to avoid collisions.** Two placements of the same icon, or two
  icons sharing an inner id, will clash. Prefix every `id` (and every
  `url(#…)` / `xlink:href="#…"` / clip-path / gradient reference) inside a placed
  icon with a per-placement token, e.g. `p03-`. Rewrite both the definitions and
  their references together so gradients/clip-paths still resolve.
- Keep the icon's own vector paths **verbatim** — do not recolour, redraw, or
  simplify the biological art. (Repositioning, uniform scaling, and id-prefixing
  are the only permitted transforms.)
- Place biological icons *inside* their subpathway's `REGION-` group so selection
  and overlay behave correctly; place the label box in the nested `OVERLAY-`
  group.

## Labelling rules

- One `OVERLAY-` label box per subpathway, text = the subpathway's Reactome
  hierarchy name, styled per spec (Arial Bold 12 pt, white, UPPERCASE, `#0F82BC`
  rounded rect). Each pathway label also gets its mandatory `ANALINFO` box (see
  spec).
- A top-level pathway title may be added as a larger label; keep entity-level
  captions minimal — EHLDs communicate through icons, not dense text.
- Text colour follows the official rule (see spec): text **inside a coloured
  shape** (compound/protein/cell) is **white UPPERCASE**; **process descriptions**
  and text for a **receptor/cell-element/process outside any shape** are **black
  lowercase** (receptor acronyms keep capitals). Spell out Greek letters in
  lowercase (`alpha`, not `α`).

## Gap handling

- List every entity with no acceptable library icon in a **Gaps** section of the
  final report and in the manifest.
- Do not draw a substitute. With curator agreement you may leave a labelled empty
  slot (a plain `<text>` note in the layout) marking where the missing icon would
  go — clearly not biological art.
- Gaps are candidate contributions to the Icon Library
  (reactome.org/icon-info) — mention this so the curator can request/commission
  the missing icon.

## Outputs

Write **all** artefacts into the **project directory** collected in step 1 of
Required inputs — the same directory that holds this request's sample / reference
images. Do not scatter outputs into the current working directory. (slug = the
pathway name lowercased, non-alphanumerics → single hyphen):

1. **`<project-dir>/<ST_ID-or-slug>.svg`** — the composed EHLD-style illustration
   (1366×768, `#0F82BC` labels, `REGION-`/`OVERLAY-` ids). This is the final
   image, saved alongside the sample images it was built from.
2. **`<project-dir>/<slug>_icon_manifest.csv`** — one row per placed icon:
   `Subpathway, Entity, Accession, DB, R-ICO id, Icon name, Category, References,
   SVG URL, Designer, Curator, ORCID`. `Accession`/`DB` record how the icon was
   resolved (the `map` input, or `search` + term). This is the attribution +
   provenance record.
3. **`<project-dir>/<slug>_gaps.md`** *(only if gaps exist)* — entities with no
   library icon.
4. **`<project-dir>/icons/`** — the downloaded source SVGs (and PNGs if
   requested).

## Attribution and licence

The Reactome Icon Library is **CC-BY 4.0**. Any figure reusing these icons must
credit Reactome and the icon designers. The manifest captures per-icon designer,
curator, and ORCID; include a credit line in the final report, e.g.:

> Icons from the Reactome Icon Library (reactome.org/icon-lib), CC-BY 4.0.
> Designers: <names>.

## After composing — report to the curator

- The project directory, and absolute paths to the SVG, the manifest CSV, the
  gaps file, and `<project-dir>/icons/` — all saved together in that one
  directory with the sample images.
- Counts: subpathways/regions, icons placed, unique icons, gaps.
- Canvas confirmation (1366×768) and the ST_ID(s)/placeholders used for
  `REGION-`/`OVERLAY-` ids and the filename.
- The CC-BY credit line with the designer names.
- Any entity where the icon match was low-confidence or a synonym was used, so
  the curator can double-check.
- The full Illustrator export settings reminder (Styling = Internal CSS, Font =
  SVG, Images = Preserve, Object IDs = Layer Names, Decimal Points = 3, Minify +
  Responsive) and the note to replace any `PLACEHOLDER` ids before ingestion.
- A rendering note: no SVG rasteriser is assumed to be installed, so preview the
  SVG by opening it in a browser (or in Illustrator/Inkscape). PNGs are only
  produced when `fetch --png` was used per-icon; the composite is delivered as
  SVG per the EHLD spec.

## Network / platform note

The skill reaches `reactome.org` (ContentService search + `/icon/*.svg`
download). This repo's `.claude/settings.json` allowlists `reactome.org` so the
helper's calls run without prompting in Claude Code.

> **claude.ai users:** add `reactome.org` under **Settings → Capabilities →
> Domain allowlist**, otherwise icon search and download will fail.

## Limitations

- **Layout is best-effort.** Automatic placement of icons and regions will need
  hand-tuning in Illustrator; treat the SVG as a structured starting point, not a
  final figure.
- **Icon coverage.** The library (~1,150+ icons across 7 categories) does not
  cover every entity. Missing entities are reported as gaps, never invented.
- **Match confidence.** Icon search is name-based; verify that the chosen icon's
  `mappedEntities`/`references` truly correspond to the intended entity,
  especially for ambiguous or family-level names.
- **EHLD ingestion.** A browser-ingestable EHLD requires real subpathway ST_IDs
  and validation against the live hierarchy — out of scope here; placeholders are
  flagged for the curator to resolve.
