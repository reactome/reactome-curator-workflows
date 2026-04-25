---
name: extract-reactions
description: Extract a reaction graph for a named pathway from one or more medical/biology review PDFs, and emit a CSV (Title, Input, Output, Catalyst, Regulators, Source1..Source5). Supports gaps and parallel branches. Use when a curator wants a first-pass reaction list from literature before drafting Reactome entries.
---

# Extract Reactions Skill

## Purpose

Given one or more review-article PDFs and the name or description of a pathway,
build a reaction graph for that pathway and write it to a CSV suitable for
seeding manual Reactome curation. Disconnected graphs, missing intermediate
steps, and parallel branches are all permitted — gaps are marked, not fixed.
This is a pre-curation convenience skill — the output is a draft, not a
curated entry.

## Required Inputs

Before doing anything else, ask the curator for, and do not proceed until you have both:

 1. The pathway name or short description
    (e.g. "classical complement activation", "glycolysis from glucose to pyruvate").

 2. Absolute paths to one or more review-article PDFs.

Do not ask about species (assume Homo sapiens), output path (auto-generated from
the pathway name), or any schema options.

## Invocation

 /extract-reactions

No arguments. The skill will prompt for the two inputs above.

## Reading the PDFs

- Read every supplied PDF in full, including figures. Pathway structure lives in
  the diagrams — read the images themselves, not just the figure captions.
- Build the full reaction graph in your head (or scratch notes) before writing
  anything to disk.
- If two PDFs describe the same step differently, prefer the most recent publication.
- If the pathway has no coverage at all in the supplied PDFs — no pathway
  figure anywhere, no reaction-level description — stop and report. Partial
  coverage is fine: proceed and mark gaps per the rules below.

## Reaction Model

Each reaction is one CSV row with these fields:

 - **Title** — short verb-phrase describing the step
   (e.g. "Hexokinase phosphorylates glucose to glucose-6-phosphate").
 - **Input** — PhysicalEntities consumed.
 - **Output** — PhysicalEntities produced.
 - **Catalyst** — the single catalytic PhysicalEntity, if the reaction is
   enzyme-catalysed. Blank otherwise. (Just the entity — no GO MF term.)
 - **Regulators** — positive and negative regulators, prefixed `+` or `-`
   (e.g. `+ AMP [cytosol] | - ATP [cytosol]`). Blank if none.
 - **Source1 … Source5** — up to five separate source citations for the
   reaction, one per column. Each cell holds a single source — either a PDF
   reference (e.g. `Smith2024.pdf, Fig. 3`) or a PubMed / PMC URL
   (e.g. `https://pubmed.ncbi.nlm.nih.gov/12345678/`). Fill `Source1` first
   and leave the rest blank if you have fewer than five. **Never combine
   multiple sources into one cell.** If a reaction has more than five
   sources, keep the five most informative (originating review PDF first,
   then primary references in order of relevance) and silently drop the
   rest.

## Entity Rules

- **Text labels only** — no UniProt / ChEBI / GO ID resolution. Write entities
  as they appear in the review, normalized to a single form per entity.
- **Compartments are mandatory** and written in square brackets after the name:
  `glucose [cytosol]`, `ATP [mitochondrial matrix]`, `Ca2+ [endoplasmic reticulum lumen]`.
- **Complexes** use colon notation: `A:B`, `A:B:C`. If the complex has a
  well-known name, use the name instead of the subunit list
  (e.g. `RNA polymerase II [nucleoplasm]`, not the 12-subunit colon string).
- **Stoichiometry** as a leading integer: `2 ATP [cytosol]`.
- **Multiple entities in one field** are pipe-delimited with spaces around the pipe:
  `glucose [cytosol] | ATP [cytosol]`.

## Graph Rules

**Connectivity is not required.** Disconnected graphs are allowed. Include
every reaction the PDFs describe, even if its Inputs do not trace back to any
earlier reaction's Output.

**Gaps are marked with parentheses.** Use parentheses to flag anything the
PDFs imply but do not spell out:

 - An **Input** that ought to come from an upstream reaction but whose
   upstream reaction is not in the PDFs: wrap the entity in parens,
   e.g. `(fructose-1,6-bisphosphate [cytosol])`.
 - An **Output** that is clearly consumed further downstream but whose
   downstream reactions are not in the PDFs: same treatment,
   e.g. `(acetyl-CoA [mitochondrial matrix])`.
 - An **entire inferred bridging reaction** that the curator should be aware
   is missing from the literature but needed to connect two described steps:
   emit a row with a fully parenthesized Title
   (e.g. `(Unknown step: F6P → F1,6BP)`) and parenthesized entities in Input
   and Output. Leave Catalyst, Regulators, and the Source columns blank, or
   set `Source1` to the PDF section that implies the gap.

Parentheses are reserved for gap markers. Do not use them for anything else
(notes and qualifiers in the Title go without parens, except the explicit
`(transporter unknown)` annotation defined below).

**Parallel branches use subtitle rows.** When a pathway has parallel branches
(e.g. classical vs alternative complement activation, canonical vs non-canonical
arms, redundant isoform-specific routes), emit a subtitle row before each
branch: Title is `## <branch name>`, all other fields blank. Reactions within
each branch follow in best-effort topological order. Use a single top-level
`## <branch name>` row per branch — do not nest subtitles.

**Compartment changes demand transport reactions.** If a species appears in
compartment X as an output of one reaction and is then consumed in compartment Y
by another reaction (whether or not they are connected in the graph), insert
an explicit transport reaction — even when the review does not name a
transporter and even when the transporter is unknown. Title such rows
`Translocation of <entity> from <X> to <Y>`, with Input `<entity> [X]` and
Output `<entity> [Y]`. Leave Catalyst blank if unknown; set `Source1` to the
PDF section that implies the compartment change and append `(transporter
unknown)` to the Title if so. These inferred transport rows are policy
inferences, not gaps — do not parenthesize them.

**Reversible reactions.** Emit two rows — one forward, one reverse — with
swapped Input and Output and titles reflecting direction
(e.g. "Phosphoglucose isomerase converts G6P to F6P" and "Phosphoglucose
isomerase converts F6P to G6P"). The forward row comes first.

**Ordering.** Within each branch (or the whole CSV if there are no parallel
branches), output reactions in best-effort topological order: upstream before
downstream. Reversible pairs: forward first, then reverse, placed at the
forward reaction's topological position. Cycles and disconnected components
are permitted; order disconnected pieces by their appearance in the PDFs.

## Writing the CSV

 - Column order:
   `Title,Input,Output,Catalyst,Regulators,Source1,Source2,Source3,Source4,Source5`
 - Always emit all ten columns in every row, even when the trailing Source
   columns are empty (so subtitle and gap rows look like
   `## Canonical arm,,,,,,,,,`).
 - One source per Source cell. Never combine multiple citations with `;`,
   commas, or any other separator. Drop any 6th and beyond.
 - Filename: slugify the pathway name (lowercase, non-alphanumerics → single
   hyphen, trim leading/trailing hyphens) and write to
   `<pathway-slug>_reactions.csv` in the current working directory.
   Example: "Classical Complement Activation" →
   `classical-complement-activation_reactions.csv`.
 - RFC 4180 quoting: wrap any field containing a comma, double quote, or
   newline in double quotes; escape embedded double quotes by doubling them.
   The pipe `|` does not require quoting on its own.
 - UTF-8 encoding, LF line endings, no BOM, no trailing blank line.

## After Writing

Report to the curator, briefly:

 - The absolute path to the CSV.
 - Counts: total reactions, parallel branches (subtitle rows), inferred
   transport reactions, reversible pairs, and gap markers (parenthesized
   entities or inferred bridging reactions).
 - Any pathway segments where the evidence was thin or where you resolved a
   conflict between PDFs by taking the most recent.
 - Any place you inferred a transport reaction with an unknown transporter.
 - A short list of the most important gaps, so the curator can decide which
   to chase down in the primary literature.

## Example Rows

Illustrative only — do not copy verbatim.

 Title,Input,Output,Catalyst,Regulators,Source1,Source2,Source3,Source4,Source5
 ## Canonical arm,,,,,,,,,
 Hexokinase phosphorylates glucose,glucose [cytosol] | ATP [cytosol],glucose-6-phosphate [cytosol] | ADP [cytosol],hexokinase [cytosol],- glucose-6-phosphate [cytosol],"Smith2024.pdf, Fig. 2",https://pubmed.ncbi.nlm.nih.gov/12345678/,https://pubmed.ncbi.nlm.nih.gov/23456789/,,
 "(Unknown step: F6P → F1,6BP)",(fructose-6-phosphate [cytosol]),(fructose-1,6-bisphosphate [cytosol]),,,"Smith2024.pdf, Fig. 2 (step implied, not described)",,,,
 Translocation of pyruvate from cytosol to mitochondrial matrix,pyruvate [cytosol],pyruvate [mitochondrial matrix],,,"Smith2024.pdf, §3.2 (transporter unknown)",,,,
 ## Alternative arm,,,,,,,,,
 Glucose-6-phosphate dehydrogenase oxidises G6P,glucose-6-phosphate [cytosol] | NADP+ [cytosol],6-phosphogluconolactone [cytosol] | NADPH [cytosol],glucose-6-phosphate dehydrogenase [cytosol],,"Jones2023.pdf, Fig. 1",,,,
