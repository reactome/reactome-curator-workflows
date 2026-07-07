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
scaffolding* around those icons (background canvas, subpathway region boxes,
`<text>` labels, connecting arrows/lines) as defined by the EHLD spec below. You
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

1. **A project directory for this illustration request.** Ask the curator for a
   directory path (absolute, or relative to the current working directory) that
   will hold everything for this one image generation request. **Create it if it
   does not exist.** This directory is where the curator drops any sample /
   reference images (the Mode B image/sketch), and it is where every output
   artefact is written (the SVG, manifest, gaps file, and `icons/` — see
   Outputs). Use one directory per request so each illustration's inputs and
   outputs stay together and self-contained.
   - Suggest a name if the curator has none, e.g. `./illustrations/<slug>/`
     where `<slug>` is the pathway name lowercased with non-alphanumerics
     collapsed to single hyphens.
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

Do not ask about canvas size, colours, or fonts — those are fixed by the EHLD
spec below.

## The Icon Library is the sole source of parts

All biological art is fetched with the bundled helper, which talks to the public
Reactome ContentService and static icon endpoint (no API key):

    python3 reactome_icons.py search "<entity name>" [--category CAT] [--max N]
    python3 reactome_icons.py fetch  <R-ICO-id> [--outdir ./icons] [--png]
    python3 reactome_icons.py info   "<entity name>"     # single best match + attribution

`search` returns, per candidate: the stable id (`R-ICO-######`), `iconName`,
`categories`, external `references` (e.g. UniProt), the Reactome
PhysicalEntities the icon is mapped to (`mappedEntities`), a short `summation`,
attribution (`designer`, `curator`, `curatorOrcid`), and the direct `svgUrl` /
`pngUrl`.

**Category tokens** (pass to `--category`): `protein`, `compound`, `cell_type`,
`cell_element`, `receptor`, `ion_channel`, `human_tissue`.

**Absolute no-fabrication rule.** An icon id, name, or download URL may enter the
illustration ONLY if `search`/`fetch` returned it in this run. Never emit an
R-ICO id from memory, never guess a download URL, never draw a replacement for a
missing icon. If a search returns nothing usable, record a gap.

## Workflow

### Phase 1 — Interpret and plan (build the icon map, then STOP)

1. Decompose the specification into: the list of **subpathways** (each becomes a
   labelled region), and within each, the ordered list of **biological
   entities** plus the **directional flow** / relationships between them.
2. For **each** entity, run `reactome_icons.py search` (use `--category` to
   disambiguate; try synonyms — gene symbol, protein name, common name). Choose
   the single best match, preferring an icon whose `mappedEntities` or
   `references` line up with the intended Reactome entity. Record the chosen
   `R-ICO-######`, name, category, and attribution.
3. Entities with **no** acceptable match become **gaps** — list them explicitly;
   do not invent art for them.
4. Present an **Icon Map** table for curator approval:

   | Subpathway | Entity (as described) | Chosen icon | R-ICO id | Category | Confidence | Notes |

   plus a separate **Gaps** list (entities with no library icon) and a one-line
   layout sketch (how subpathways/regions will be arranged on the canvas).

5. **STOP and wait for curator approval.** Icon selection is where mismatch and
   hallucination risk lives — do not render until the curator confirms or edits
   the Icon Map. If the curator accepts gaps as-is, they will be omitted (or
   left as a labelled empty slot) — never back-filled with drawn shapes.

### Phase 2 — Fetch and compose (after approval)

1. `fetch` every approved icon into `<project-dir>/icons/` (pass
   `--outdir <project-dir>/icons`; SVG only, add `--png` only if the curator
   wants raster previews).
2. Compose one EHLD-compliant SVG per the spec below. Embed each downloaded icon
   verbatim (see "Embedding icons"). Lay out subpathway regions, place icons,
   add connectors and labels.
3. Write every artefact into the **project directory** from step 1 of Required
   inputs (see Outputs) and report.

## EHLD style specification (authoritative — from reactome.org/icon-info/ehld-specs-guideline)

- **Format:** SVG only. No raster/bitmap content embedded (icons are vector; keep
  them vector). RGB colour mode.
- **Canvas:** **1366 px wide × 768 px high.** `viewBox="0 0 1366 768"`.
- **Filename:** the Reactome pathway ST_ID followed by `.svg`, e.g.
  `R-HSA-109581.svg`. With multiple/placeholder IDs, use the primary pathway's
  ST_ID (or `R-HSA-PLACEHOLDER-1.svg`).
- **Text:** use real `<text>` elements. Never convert text to outlined shapes.
- **Pathway / subpathway labels:** **Arial Bold**, text **white and UPPERCASE**
  when it sits inside a coloured shape, centred on a **rounded rectangle** that
  is **170 px wide × 30 px high** (use **43 px** height for two-line labels),
  filled with Reactome label blue **RGB(15, 130, 188) = `#0F82BC`**.
- **Active regions (the mechanism that makes a region clickable/overlayable in
  the Pathway Browser):** annotate SVG group `id` attributes:
  - `id="OVERLAY-R-HSA-#######"` — a group holding the subpathway's **label box**
    (the rounded rectangle + text). Selectable **and** analysis-overlayable.
    **Mandatory** for every subpathway. Must **not** contain arrows.
  - `id="REGION-R-HSA-#######"` — an (optional) larger selectable group for the
    subpathway's content; **may** include arrows pointing to/from it. When both
    are used, the `REGION-` group must **contain** the `OVERLAY-` group.
  Use the subpathway's real ST_ID; use the placeholder token if none exists yet.
- **Analysis Information Label (optional but spec'd):** Arial Bold, white text,
  rounded rectangle **8 px radius, 170 px × 20 px**, fill **RGB(198,198,198) =
  `#C6C6C6`**. Set the *group* opacity to 0% but keep inner shapes/text at 100%.
  Place it beside its pathway label, on the side away from the content.
- **Edges / cut elements:** aim to portray every element in full within the
  1366×768 space. If an element must be clipped at the canvas edge, fade it with
  a gradient so the canvas boundary stays clean.
- **Illustrator export settings** (tell the curator): Export As → SVG, Font =
  SVG, Object IDs = Layer Names — this preserves the `REGION-`/`OVERLAY-` ids.

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
  hierarchy name, styled per spec (Arial Bold, white, uppercase, `#0F82BC` box).
- A top-level pathway title may be added as a larger label; keep entity-level
  captions minimal — EHLDs communicate through icons, not dense text.
- Entity captions that sit inside a coloured icon shape are white uppercase; free
  captions on the blank canvas use a dark readable colour (`#444444`).

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
   `Subpathway, Entity, R-ICO id, Icon name, Category, References, SVG URL,
   Designer, Curator, ORCID`. This is the attribution + provenance record.
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
- The Illustrator export settings reminder (Font = SVG, Object IDs = Layer
  Names) and the note to replace any `PLACEHOLDER` ids before ingestion.
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
