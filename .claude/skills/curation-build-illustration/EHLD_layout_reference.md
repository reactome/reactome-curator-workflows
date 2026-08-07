# EHLD Layout Reference — conventions learned from the production EHLD corpus

This file distils layout, compartment, and membrane conventions observed in the
**live Reactome EHLD set** (217 production diagrams, downloaded from
`reactome.org/download-data?id=118`). It is the *empirical companion* to
`SKILL.md` and to the two **authoritative** official specs bundled in this skill
directory — **`EHLD_Specs_and_Guidelines.pdf`** and
**`Icon_Library_Guidelines.pdf`**. Read it before composing an EHLD so the draft
matches how real Reactome illustrations are built.

> **Authority order.** The official PDFs govern. Where an observed corpus trait
> conflicts with them, the spec wins and the corpus trait is an export artifact.
> The clearest example: exported corpus files often contain a full-canvas white
> `1366×768` rect, but the spec says **do not author a whole-image background**
> (Reactome renders EHLDs in a blank zoomable space) — so treat that rect as an
> Illustrator artboard artifact, not a thing to reproduce. Compartment/organelle
> backgrounds are fine; unnecessary full-canvas fills are not.

> **Provenance.** Every rule below was verified against the 217-file corpus, not
> invented. Frequencies (e.g. "142/217") are counts from that corpus. The corpus
> itself is ~128 MB and is **not** committed to this repo (it lives under the
> gitignored `illustrations/` tree); these distilled rules are what we keep.

> **Authoring vs. distributed form — read this first.** The downloaded corpus is
> the *distributed* form of each EHLD: all label text has been **converted to
> outlined `<path>` shapes** and the artboard carries a bleed margin. Do **not**
> copy those two traits. When *authoring* a new EHLD you keep text as real
> editable `<text>` elements (per the EHLD spec in `SKILL.md`) and you work on the
> 1366×768 artboard. Everything else in this file — layer order, compartment
> construction, membrane depiction, entity placement — is authoring guidance you
> should follow.

---

## 1. Canvas geometry (corrects the bare "1366×768" in older guidance)

Two measurements, both real, both needed:

| Thing | Value | Evidence |
|---|---|---|
| **Authoring artboard** (create the Illustrator doc at this size; where all art + labels live) | **1366 × 768** | official spec; matches the `<rect fill="white" height="768" width="1366"/>` seen in 142/217 exported files (that rect is an artboard artifact, not a required background) |
| **Distributed `viewBox`** (artboard + 15 px bleed margin on every side) | **1396 × 798** | `viewBox="0 0 1396.000 798.000"` in 200/217 files |

So: **compose within 1366×768.** The extra 15 px on each edge (→ 1396×798) is
safe bleed that appears only after export. Keep all entities, labels, and
compartments inside the inner 1366×768 box; treat the 15 px ring as margin an
element may *bleed into* but never rely on. The handful of off-size files
(e.g. `798→806/808/820` tall) are exceptions where one element overhangs — not a
license to change the artboard.

The exported root `<svg>` typically carries `width="1396" height="798"
viewBox="0 0 1396 798"`. Exported corpus files may add a white `1366×768` rect as
the first child (the artboard), but — per the official spec — you should **not**
author a full-canvas background; keep only necessary compartment backgrounds.

> **Both sizes are live.** The bulk corpus download is mostly `1396×798`, but
> EHLDs served individually from
> `reactome.org/download/current/ehld/<ST_ID>.svg` — the Mode A fetch path — come
> back at **`1366×768`**, with no bleed. So a Mode A base may be either size.
> `reactome_icons.py validate` accepts both and rejects anything else; keep the
> base's own root `<svg>` verbatim rather than normalising it.

---

## 2. Layer / group stacking order (back → front)

Production EHLDs are built as a fixed stack of **named** top-level groups. Emit
groups in this order (first = furthest back). Names are the real layer names
observed in the corpus — reuse them so an EHLD opened in Illustrator has familiar
layers and so `Object IDs = Layer Names` on export produces predictable ids.

1. **`BG`** — background layer. In the corpus this often holds a white `1366×768`
   rect + `TEXTURE`, but per the official spec **do not author a full-canvas
   background** (that rect is an export artifact). Use this layer only for
   *necessary* compartment/organelle backgrounds and decorators, placed at the
   bottom of the hierarchy. (Some `BG*` group is present in every file.)
2. **Compartment layers** — the cell/organelle scaffolding, built from
   cell-element icons (see §3). Common layer names, in rough back-to-front order:
   `CELL` / `CELLS`, `membrane` (+ its `membrane BG` / `membrane LINE` /
   `membrane DOTED` sub-layers — see §4), `CYTOSOL`, `NUCLEUS` / `Nucleus`,
   `ORGANELLES`, `Lysosomes`. An 81/217 subset wraps the whole content stack in a
   single **`CONTENT`** group — optional but tidy.
3. **Entity icons** — the biological actors, each an `R-ICO-######` group, often
   grouped further under a semantic name matching the entity (`CASP8`, `Wnt`,
   `CTNNB1`, …). These sit *on top of* the compartment they belong to (§5).
4. **Text** — `TEXT`, `TEXT_DM`, and `PATHWAY TEXT` layers holding entity captions
   and pathway/subpathway label text.
5. **`ARROWS`** — all connectors, flow arrows, and transport arrows. Kept in their
   own layer, never inside an `OVERLAY-` group (see §6).
6. **`LOGO`** — the Reactome logo (`LOGO` / `LOGO_2`), bottom-corner.
7. **`ICON`** (analysis legend) — one per file (exactly 217/217). Contains child
   groups `50`, `75`, `100`: the analysis-overlay expression-threshold legend.
   Reuse this structure verbatim; it is standard furniture, not content.
8. **`REGION-` / `OVERLAY-` groups** — the clickable/overlayable subpathway
   machinery (see §6). One `REGION-`+`OVERLAY-` pair per subpathway; 1165 REGION
   and 1169 OVERLAY groups across the corpus, present in 217/217 files.

---

## 3. Compartments are library icons, not hand-drawn shapes

This resolves the ambiguity in the old skill text. **Compartment scaffolding is
still icon-library art** — it does not violate the no-hand-drawing rule. The
canonical compartment icons, confirmed by fetching them:

| Icon id | What it is | Inner structure |
|---|---|---|
| **`R-ICO-013570`** | a whole **cell** | inner groups `BG`, `CYTOPLASM`, `MEMBRANE` — i.e. it *already contains* a plasma membrane and a cytoplasm region |
| **`R-ICO-013121`** | the **nucleus** | inner `Nucleus` group; drop it inside the cell to make the nucleoplasm compartment |

Because `R-ICO-013570` bundles membrane + cytoplasm, a single-cell scene often
needs just that one icon plus a nucleus icon inside it. Fetch these the normal
way (`reactome_icons.py search "cell"` / `search "nucleus" --category cell_element`),
confirm the id, and place them as the compartment layer. Never redraw them.

**Multi-cell / multi-compartment scenes:** repeat the cell icon
(`R-ICO-013570`, then id-namespaced `R-ICO-013570_2`, `_3`, …), each in its own
`membrane` / `CELLS` sub-group. The Wnt EHLD (`R-HSA-195721`) is the reference
example: three cells, each `R-ICO-013570` + a `membrane` group, plus `Lysosomes`
and `ORGANELLES` layers holding organelle icons.

---

## 4. Membrane depiction (the lipid bilayer)

When a membrane is drawn explicitly (rather than taken from `R-ICO-013570`'s inner
`MEMBRANE`), the corpus renders it as a **three-part band**, in this back-to-front
order:

1. **`membrane BG`** — a filled band giving the bilayer its thickness/colour.
2. **`membrane LINE`** (a.k.a. `Membrane LINES`) — the **solid** leaflet line.
3. **`membrane DOTED`** (sic — that spelling is used in the corpus; a.k.a.
   `Membrane DOTED`) — the **dotted / dashed** leaflet line.

Together the solid + dotted pair reads as the two leaflets of a phospholipid
bilayer. Keep the band roughly horizontal and full-width for a plasma membrane;
use shorter segments for organelle membranes. `R-HSA-168256` shows the full
stack: `MEMBRANE` → `MEMBRANE_2` → `Membrane LINES` → `Membrane DOTED` → `Nucleus`.

---

## 5. Placing entities *within* compartments

The rule: **an entity icon is placed inside (drawn on top of) the compartment icon
that matches the entity's Reactome compartment** (the `[compartment]` in its
display name). Compartment layers are emitted first (§2 step 2) so entities in
step 3 naturally stack above them.

- **Nucleoplasm / nuclear** entities (e.g. `…[nucleoplasm]`) → positioned over the
  **nucleus** icon (`R-ICO-013121`), inside its bounds.
- **Cytosolic** entities (`…[cytosol]`) → over the **cytoplasm** region of the
  cell icon (`R-ICO-013570`'s `CYTOPLASM`), between the membrane and the nucleus.
  The corpus even names such a layer `CYTOSOLIC PROTEIN`.
- **Organelle-lumen** entities (lysosome, ER, mitochondrial matrix, …) → over the
  matching organelle icon (`Lysosomes`, `ORGANELLES` layers).
- **Extracellular / secreted** entities (`…[extracellular region]`) → *outside*
  the outermost membrane, above/around the cell.

Keep the entity fully within its compartment's silhouette; don't let a cytosolic
protein spill across the membrane line unless it is a membrane protein (§6).

---

## 6. Entities at / across the membrane (transport & membrane interaction)

This is where placement carries biological meaning — handle it deliberately.

**Integral membrane proteins (receptors, ion channels, transporters):**
place the icon **straddling the membrane band** so it visibly spans the bilayer —
part of the icon sits on the extracellular side, part on the cytosolic side,
centred on the `membrane LINE`. Do not float a receptor entirely in the cytosol or
entirely outside the cell. Receptor and `ion_channel` category icons are drawn to
sit on a membrane; align their membrane axis to the band.

**Ligand / receptor interaction across the membrane:**
put the **ligand** (extracellular) touching the **extracellular face** of the
receptor; put downstream **cytosolic effectors** below the membrane, on the
cytosolic face. The interaction arrow runs from ligand → receptor across the
membrane's outer edge, not through the bilayer.

**Transport across a membrane (a molecule moving compartments):**
this mirrors the transport convention in `/extract-reactions` — a compartment
change *is* a transport step.

- Draw the transported small-molecule / entity icon **on both sides** of the
  membrane: once in the source compartment, once in the destination compartment.
- Connect them with a **transport arrow that crosses the membrane band**
  (the transporter/channel icon straddling the band is what the arrow passes
  through or beside).
- The transporter itself (the protein moving the cargo) sits in the membrane per
  the integral-membrane rule above.

**Arrows stay in the `ARROWS` layer, never in an `OVERLAY-` group** — the
`OVERLAY-` group is analysis-overlayable and must contain only the subpathway
label box (spec rule, confirmed by the corpus: `REGION-` groups may hold arrows,
`OVERLAY-` groups never do).

---

## 7. Subpathway machinery (REGION / OVERLAY) — as seen in the corpus

Every subpathway is one `REGION-R-HSA-#######` group that **contains** a nested
`OVERLAY-R-HSA-#######` group. Confirmed structure from `R-HSA-109581`:

```
REGION-R-HSA-5357769              ← selectable region; may include its arrows
  ├─ R-ICO-012706 / R-ICO-012705 / …   ← the subpathway's entity icons
  ├─ CASP8                              ← semantic entity sub-group
  ├─ ARROWS_2                           ← this region's arrows (allowed here)
  ├─ PATHWAY_LABEL                      ← the blue #0F82BC rounded-rect box
  ├─ ANALINFO                           ← the #C6C6C6 analysis-info box (group opacity 0)
  └─ OVERLAY-R-HSA-5357769             ← label box only; analysis-overlayable
```

- `REGION-` id and `OVERLAY-` id use the **same real subpathway ST_ID**
  (`R-HSA-#######`); use a `R-HSA-PLACEHOLDER-<n>` token if the ST_ID doesn't exist
  yet and flag it for the curator.
- `PATHWAY_LABEL` box: Arial-Bold, white UPPERCASE text, rounded rect
  170 × 30 px (43 px for two lines), fill `#0F82BC` (RGB 15,130,188).
- `ANALINFO` box: Arial-Bold white text, rounded rect 8 px radius, 170 × 20 px,
  fill `#C6C6C6` (RGB 198,198,198). One per subpathway (1168/217 → present for
  every subpathway).
  - **Group opacity is `0.01`, not `0`.** The spec says "0 %", but every
    `ANALINFO*` group in every corpus file checked carries `opacity="0.01"` —
    a fully transparent group can be dropped from hit-testing, which would
    disable the analysis overlay the box exists to receive. Author `0.01`;
    `reactome_icons.py validate` accepts anything ≤ 0.01.

---

## 7a. Placed icons carry their category as a CSS class

Production EHLDs tag each placed icon group with its Icon Library **category
token** as a `class`, alongside the `R-ICO` id:

```
<g class="cell_type" id="R-ICO-013570" opacity="0.8"> … </g>
<g class="protein" id="R-ICO-012706"> … </g>
<g class="receptor protein" id="…"> … </g>   ← multiple categories, space-separated
<g class="arrow" …>                          ← arrows are tagged too
```

Reproduce this: pass `--class <category>` to `reactome_icons.py place`, using the
token(s) the icon's `categories` field reported from `map`/`search`. The
`class="arrow"` marker on connectors is also what `validate` uses to detect
arrows wrongly nested inside an `OVERLAY-` group.

---

## 8. Quick checklist for a corpus-faithful draft

- [ ] Author within a `1366×768` artboard (exported `viewBox` may be `1396×798` with 15 px bleed); all art inside the inner box; **no** full-canvas background.
- [ ] Layer stack in order: `BG` → compartments → entity icons → `TEXT` → `ARROWS` → `LOGO` → `ICON` (with `50`/`75`/`100`) → `REGION`/`OVERLAY`.
- [ ] Compartments built from library icons (`R-ICO-013570` cell, `R-ICO-013121` nucleus), never hand-drawn; repeated + id-namespaced for multi-cell scenes.
- [ ] Membranes drawn as `membrane BG` + solid `membrane LINE` + dotted `membrane DOTED` (or taken from the cell icon's inner `MEMBRANE`).
- [ ] Each entity placed inside the compartment icon matching its `[compartment]`.
- [ ] Receptors / channels / transporters straddle the membrane band; ligands extracellular; effectors cytosolic.
- [ ] Transport = same cargo icon on both membrane sides + a crossing arrow in the `ARROWS` layer.
- [ ] One `REGION-`⊃`OVERLAY-` pair per subpathway, real ST_IDs (or flagged placeholders); label text kept as editable `<text>`, not outlined paths.
- [ ] Each placed icon embedded via `reactome_icons.py place` with a unique `--prefix`, and tagged `--class <category>` as production files are.
- [ ] `ANALINFO` groups at `opacity="0.01"` (see §7), inner shapes at 100%.
- [ ] `reactome_icons.py validate <file>.svg` reports **zero errors** before the file goes to the curator.
