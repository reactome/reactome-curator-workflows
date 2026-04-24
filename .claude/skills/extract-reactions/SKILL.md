---
name: extract-reactions
description: Extract a connected reaction graph for a named pathway from one or more medical/biology review PDFs, and emit a CSV (Title, Input, Output, Catalyst, Regulators, Source). Use when a curator wants a first-pass reaction list from literature before drafting Reactome entries.
---

# Extract Reactions Skill

## Purpose

Given one or more review-article PDFs and the name or description of a pathway,
build a connected reaction graph for that pathway and write it to a CSV suitable
for seeding manual Reactome curation. This is a pre-curation convenience skill —
the output is a draft, not a curated entry.

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
- If the pathway is not substantively covered across the supplied PDFs — no
  pathway figure, no reaction-level description — stop and report which parts
  are missing. Refuse rather than fabricate reactions.

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
 - **Source** — originating PDF filename plus section or figure reference
   (e.g. `Smith2024.pdf, Fig. 3`), and when the reaction is attributable to a
   specific cited primary reference, append a PubMed or PMC URL
   (e.g. `https://pubmed.ncbi.nlm.nih.gov/12345678/`).

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

**Connectivity (core rule).** Every reaction after the first must have at least
one Input that matches (by entity name and compartment) an Output of an earlier
reaction in the CSV. Regulators and catalysts do not count — only Input↔Output
edges. If you cannot satisfy this, you are missing an intermediate reaction;
find it or, if it is not in the PDFs, refuse.

**Compartment changes demand transport reactions.** If a species appears in
compartment X as an output of one reaction and is then consumed in compartment Y
by a later reaction, you must insert an explicit transport reaction between them
— even when the review does not name a transporter and even when the
transporter is unknown. Title such rows
`Translocation of <entity> from <X> to <Y>`, with Input `<entity> [X]` and
Output `<entity> [Y]`. Leave Catalyst blank if unknown; set Source to the PDF
section that implies the compartment change and add a note in the Title if
the transporter is unknown (e.g. append `(transporter unknown)`).

**Reversible reactions.** Emit two rows — one forward, one reverse — with
swapped Input and Output and titles reflecting direction
(e.g. "Phosphoglucose isomerase converts G6P to F6P" and "Phosphoglucose
isomerase converts F6P to G6P"). The forward row comes first.

**Ordering.** Output the CSV in topological order: upstream reactions before
downstream. Reversible pairs: forward first, then reverse, placed at the
forward reaction's topological position. Cycles caused by reversibility are
expected; any other apparent cycle should be broken by source order and flagged
in the final report.

## Writing the CSV

 - Column order: `Title,Input,Output,Catalyst,Regulators,Source`
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
 - Counts: total reactions, inferred transport reactions, reversible pairs.
 - Any pathway segments where the evidence was thin, where you resolved a
   conflict between PDFs by taking the most recent, or where you inferred a
   transport reaction with an unknown transporter.
 - Any place where you had to break a non-reversibility cycle.

## Example Rows

Illustrative only — do not copy verbatim.

 Title,Input,Output,Catalyst,Regulators,Source
 Hexokinase phosphorylates glucose,glucose [cytosol] | ATP [cytosol],glucose-6-phosphate [cytosol] | ADP [cytosol],hexokinase [cytosol],- glucose-6-phosphate [cytosol],"Smith2024.pdf, Fig. 2; https://pubmed.ncbi.nlm.nih.gov/12345678/"
 Translocation of pyruvate from cytosol to mitochondrial matrix,pyruvate [cytosol],pyruvate [mitochondrial matrix],,,"Smith2024.pdf, §3.2 (transporter unknown)"
