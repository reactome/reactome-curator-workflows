---
name: extract-reactions
description: Extract a reaction graph for a named pathway from one or more medical/biology review PDFs and emit (1) a CSV (Title, Input, Output, Catalyst, Regulators, Reviews, Source1..Source5 — Source cells use a PubMed > PMC > DOI > publisher URL ladder) and (2) a companion HTML reference list. Supports gaps and parallel branches. Use when a curator wants a first-pass reaction list from literature before drafting Reactome entries.
---

# Extract Reactions Skill

## Purpose

Given one or more review-article PDFs and the name or description of a pathway,
build a reaction graph for that pathway and write two artefacts: a CSV of
reactions for seeding manual Reactome curation, and a companion HTML page
listing every primary reference cited in support of those reactions.
Disconnected graphs, missing intermediate steps, and parallel branches are
all permitted — gaps are marked, not fixed. This is a pre-curation
convenience skill — the output is a draft, not a curated entry.

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
- As you identify each reaction, also capture the in-text citation markers
  in the supporting PDFs that vouch for it (numeric `[12]`, `(12, 13)`,
  superscript; or author-year `(Smith et al., 2024)`). For each marker,
  look up only the cited entry in **that PDF's** references list and
  record what you find. Do not parse any PDF's bibliography exhaustively;
  capture refs opportunistically. See the **References & Source Resolution**
  section below for the full workflow.
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
 - **Reviews** — pipe-delimited list of supplied-PDF basenames whose text
   or diagram blurb supports this reaction (e.g.
   `Smith2024.pdf | Jones2023.pdf`). Basename only, no paths and no figure
   references. Each name must match one of the PDFs the curator passed in.
   Order by relevance (most-cited PDF first). Subtitle and gap rows leave
   this blank. **PDF filenames go here, never in Source columns.**
 - **Source1 … Source5** — up to five primary-reference URLs for the
   reaction, one per column. Each cell holds exactly one URL chosen by the
   following ladder, falling through to the next rung when the upper one
   is unavailable:
     1. PubMed: `https://pubmed.ncbi.nlm.nih.gov/<PMID>/`
     2. PMC: `https://www.ncbi.nlm.nih.gov/pmc/articles/PMC<id>/`
     3. DOI: `https://doi.org/<doi>`
     4. Publisher URL — only when the reference printed one inline.
     5. Empty — only if none of the above can be obtained.
   Fill `Source1` first. **Never combine multiple URLs into one cell**,
   never fabricate a URL, and never put PDF filenames or plain-text
   citations here. Triage to ≤5 sources per reaction (see below).

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
   and Output. Leave Catalyst, Regulators, and the Source columns blank.
   Set `Reviews` to the PDF that implies the gap so the curator can find
   the context — Source columns stay blank because no primary reference
   can be cited for an inferred missing reaction.

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
Output `<entity> [Y]`. Leave Catalyst blank if unknown; set `Reviews` to the
PDF that implies the compartment change and append `(transporter unknown)`
to the Title if so. The Source columns can be filled if the review cites a
primary reference for the transport step, otherwise they stay blank.
These inferred transport rows are policy inferences, not gaps — do not
parenthesize them.

**Reversible reactions.** Emit two rows — one forward, one reverse — with
swapped Input and Output and titles reflecting direction
(e.g. "Phosphoglucose isomerase converts G6P to F6P" and "Phosphoglucose
isomerase converts F6P to G6P"). The forward row comes first.

**Ordering.** Within each branch (or the whole CSV if there are no parallel
branches), output reactions in best-effort topological order: upstream before
downstream. Reversible pairs: forward first, then reverse, placed at the
forward reaction's topological position. Cycles and disconnected components
are permitted; order disconnected pieces by their appearance in the PDFs.

## References & Source Resolution

A four-step process woven around reaction extraction. Steps 1–2 happen
during reading; step 3 is the only network call; step 4 is local assembly.

**1. Capture citations during reading (no network).** As you identify each
reaction, capture which in-text citation markers in the supporting PDFs
vouch for it: numeric (`[12]`, `(12, 13)`, superscript) or author-year
(`(Smith et al., 2024)`). For each marker, look up the matching entry in
**only that PDF's references list** — do not parse other PDFs'
bibliographies, and never parse a bibliography exhaustively. Record just
enough to identify the cited paper:

    { pdf, marker, authors, year, title, journal, doi?, pmid?, pmcid?,
      publisher_url? }

**2. Maintain a dedup table (no network).** Keep a single internal
`seen_refs` table, keyed by best-available identifier in this priority:
PMID > DOI > PMC > normalized first-author + year + title. The same paper
cited from many reactions becomes one entry. Track which PDFs each ref was
seen in (for the HTML deliverable's audit annotation). Also classify each
ref as `primary research`, `meta-analysis`, or `review/editorial/commentary`
— the triage step needs this.

**3. One batched DOI→PMID lookup (one network call).** After all reactions
are extracted, collect the unique DOIs in `seen_refs` whose entries have
no PMID. Make **one** GET request to NCBI's idconv:

    https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids=<doi1,doi2,...>&idtype=doi&format=json

If the unique-DOI count exceeds idconv's batch limit (~200), split into
the minimum number of batches and treat them as one logical call. Merge
returned PMIDs into `seen_refs`. Do **not** issue ESearch lookups, do
**not** make a second idconv call for PMC IDs, and do **not** follow DOI
redirects to discover publisher URLs.

If the skill is offline at this step, refs that had no inline PMID simply
fall through to the next ladder rung in step 4. The deliverables still
produce.

**Platform note.** On Claude Code (local CLI) the call goes through after
the curator's first WebFetch permission prompt — and this repo ships a
`.claude/settings.json` rule (`WebFetch(domain:www.ncbi.nlm.nih.gov)`) so
even that prompt is skipped. On **claude.ai (browser)** the skill runs
inside a sandbox with a hard network allowlist that does **not** include
NCBI; the call will fail. That is expected and not a bug — every ref that
has an inline DOI will still get a `https://doi.org/<doi>` link in its
Source cell via the ladder fallback. The CSV simply contains more DOI
links and fewer PubMed links than it would on Claude Code. Run on Claude
Code if the PubMed-rich version matters.

**4. Walk the ladder for each reaction's Source slots (no network).** For
every reaction:

 - Take its cited refs.
 - Sort by ref-type priority: primary research → meta-analysis →
   review/editorial/commentary.
 - Within type, prefer newer over older when they make the same point.
 - Take the top 5; drop any 6th and beyond silently.
 - For each kept ref, walk the URL ladder and emit the first non-empty
   URL into the next Source slot:
     PubMed (`https://pubmed.ncbi.nlm.nih.gov/<PMID>/`) →
     PMC (`https://www.ncbi.nlm.nih.gov/pmc/articles/PMC<id>/`) →
     DOI (`https://doi.org/<doi>`) →
     publisher URL (only if printed inline) →
     blank.

`Source1` is the most direct primary research paper for the step. The
originating review PDFs go in the `Reviews` column, never in Source.

## Writing the CSV

 - Column order:
   `Title,Input,Output,Catalyst,Regulators,Reviews,Source1,Source2,Source3,Source4,Source5`
 - Always emit all eleven columns in every row, even when trailing cells
   are empty (so subtitle and gap rows look like
   `## Canonical arm,,,,,,,,,,`).
 - **Reviews cell.** Pipe-delimited PDF basenames with spaces around the
   pipe, e.g. `Smith2024.pdf | Jones2023.pdf`. Each filename must match a
   supplied PDF's basename. No paths, no figure refs, no notes.
 - **Source cells.** Each cell holds exactly one URL or is empty. Apply a
   pre-write URL-shape check: every non-empty Source cell must start with
   `http://` or `https://` and contain no whitespace. Cells that fail are
   blanked silently — never fabricate identifiers, the empty rung is a
   legitimate outcome.
 - One URL per Source cell. Never combine multiple URLs with `;`, commas,
   or any other separator.
 - Filename: slugify the pathway name (lowercase, non-alphanumerics →
   single hyphen, trim leading/trailing hyphens) and write to
   `<pathway-slug>_reactions.csv` in the current working directory.
   Example: "Classical Complement Activation" →
   `classical-complement-activation_reactions.csv`.
 - RFC 4180 quoting: wrap any field containing a comma, double quote, or
   newline in double quotes; escape embedded double quotes by doubling them.
   The pipe `|` does not require quoting on its own.
 - UTF-8 encoding, LF line endings, no BOM, no trailing blank line.

## Writing the References HTML

Alongside the CSV, write `<pathway-slug>_references.html` listing every
unique entry in `seen_refs`.

 - Single `<ul>`, one `<li>` per unique ref.
 - href chosen by the same ladder as the Source columns (PubMed > PMC >
   DOI > publisher URL). If none of the four is available, render the
   entry as plain text with no `<a>`.
 - Link text format: `Authors (Year). Title. Journal.` Any of these
   pieces may be missing; just join what you have.
 - After the link, append `(seen in: <pdf basenames>)` separated by
   commas, for curator audit.
 - Order entries by first-author last name, then year.
 - Minimal `<head>` with `<title>` and a small inline CSS reset; no
   external assets, no JavaScript.

## After Writing

Report to the curator, briefly:

 - The absolute paths to the CSV and the HTML.
 - Counts: total reactions, parallel branches (subtitle rows), inferred
   transport reactions, reversible pairs, and gap markers (parenthesized
   entities or inferred bridging reactions).
 - Reference counts: total unique refs in the HTML; Source cells filled
   vs. left blank; and a breakdown of filled Source cells by ladder rung
   (PubMed / PMC / DOI / publisher) so the curator can see how much of
   the linkage relied on the idconv call.
 - Any pathway segments where the evidence was thin or where you resolved a
   conflict between PDFs by taking the most recent.
 - Any place you inferred a transport reaction with an unknown transporter.
 - A short list of the most important gaps, so the curator can decide which
   to chase down in the primary literature.

## Example Rows

Illustrative only — do not copy verbatim.

 Title,Input,Output,Catalyst,Regulators,Reviews,Source1,Source2,Source3,Source4,Source5
 ## Canonical arm,,,,,,,,,,
 Hexokinase phosphorylates glucose,glucose [cytosol] | ATP [cytosol],glucose-6-phosphate [cytosol] | ADP [cytosol],hexokinase [cytosol],- glucose-6-phosphate [cytosol],Smith2024.pdf,https://pubmed.ncbi.nlm.nih.gov/12345678/,https://pubmed.ncbi.nlm.nih.gov/23456789/,https://doi.org/10.1234/example,,
 "(Unknown step: F6P → F1,6BP)","(fructose-6-phosphate [cytosol])","(fructose-1,6-bisphosphate [cytosol])",,,Smith2024.pdf,,,,,
 Translocation of pyruvate from cytosol to mitochondrial matrix (transporter unknown),pyruvate [cytosol],pyruvate [mitochondrial matrix],,,Smith2024.pdf | Jones2023.pdf,,,,,
 ## Alternative arm,,,,,,,,,,
 Glucose-6-phosphate dehydrogenase oxidises G6P,glucose-6-phosphate [cytosol] | NADP+ [cytosol],6-phosphogluconolactone [cytosol] | NADPH [cytosol],glucose-6-phosphate dehydrogenase [cytosol],,Jones2023.pdf,https://pubmed.ncbi.nlm.nih.gov/34567890/,,,,
