---
name: curation-update-from-paper
description: >
  Turn a newly published primary paper into a curation update proposal for an
  EXISTING Reactome pathway. Given a paper (PDF, PMID, or DOI) plus the curator's
  exported event report for the pathway it affects, work out what the paper adds
  or changes, and write a single formatted DOCX "curation update" covering the
  logic, the gap analysis against what is already curated, every proposed new
  PhysicalEntity and ReactionLikeEvent with full anatomy, draft summations,
  required ontology terms, a verified reference list, open questions, and a
  pre-submission checklist. Every PMID is resolved against NCBI E-utilities,
  never from training data. Checks the live gk_central copy (via the gk-central
  MCP server) for entities and events that already exist, so the proposal reuses
  rather than duplicates. Use when a curator says "what would this paper add to
  <pathway>", "draft a curation update for this paper", "we need to update
  <pathway> for this new Science/Nature paper", or hands over a paper plus an
  event export. Produces a proposal for curator review — it does NOT write to
  the database.
---

## ON INVOCATION — PRINT THIS FIRST

Before asking for inputs, show the curator what this run has to work with, as a
short block. Check which MCP tools are actually present and say so; do not
claim a server that is not there.

```
/curation-update-from-paper — reference material for this run

Reference documents — all bundled in this skill directory, nothing to upload:
  Reactome_RLE_Annotation_Reference_V94.md   START HERE. Condensed V94 RLE
      rules — naming, compartments, evidence classes, catalyst/regulation,
      species and chimeric handling.
  Curator_Guide_V94_Extract.md               The Guide sections the RLE
      reference does NOT cover: updating existing content, evidence and
      inference, host-pathogen species/relatedSpecies/compartment rules, and
      retiring released events. Read §3 before any infection pathway.
  data_model_slots.md                        Which slots real events actually
      carry, measured across released gk_central content. Settles "does an RLE
      normally have this?" with a number. GO BP is a pathway slot, not a
      reaction slot.
  ptm_prefixes.md                            PSI-MOD -> EWAS name prefix, 70
      rows. Needed for any modified-protein entity.

In the full repo only (too large to bundle; absent from a zipped copy):
  ../review-internal/Curator_Guide_V94.pdf   283pp, 17MB. The authority. Open
      for a question the extract does not answer — disease pathway structure
      (pp.148-218), drug curation (pp.226-236), orthology.
  ../review-internal/bau060.pdf              Jupe et al. 2014, the published
      controlled vocabulary. Cite this, not the extract.
  ../review-internal/Small_molecule_renaming.xlsx   Preferred small-molecule
      names — the 'small molecules' sheet.
  ../review-internal/Claude_ReactomeDataModelGlossary_V95_Final.docx.pdf
  ../review-internal/EWAS_name_rules.docx    Mutant EWAS naming only.

Live servers:
  gk-central   <present/absent>  Existing entities, compartments, the branch's
      species convention, and release status. Not knowable from the export.
  ols          <present/absent>  Confirms every GO/ChEBI term is real, current
      and correctly labelled before it is written down.

Not bundled: the pathway's event export and the paper. Supply both.
```

> **The three bundled files are the working set.** They are sized to be read,
> and between them they cover everything this skill routinely needs. The
> repo-only documents overlap them heavily by generation — the RLE reference
> was derived from the Curator Guide and the Glossary, and both restate
> `bau060.pdf`, so reaction-class naming appears in four places and EWAS/PTM
> naming in four. Open a repo-only document for a specific question or for a
> citation, not to read through.
>
> **A zipped copy of this skill has only the three bundled files.** That is by
> design — the Guide alone is 17 MB. If you are running from a zip and need
> something the extract does not cover, say so rather than guessing; the
> curator can supply the page.
>
> **One trap.** `Small_molecule_renaming.xlsx` has a `PSI_MOD Mapping` sheet
> that shares 36 MOD IDs with `ptm_prefixes.md` but gives different strings —
> `MOD:00046` is `P` there and `p-` here. They are different vocabularies
> (diagram labels vs EWAS name prefixes) and neither file says so. For entity
> names always use `ptm_prefixes.md`. That sheet's `Nature_abbreviations` tab
> is *Leishmania* metabolic-model identifiers, not Reactome content — ignore it.
>
> **Deliberately not listed:** `Rules_for_automatic_reaction_typing.docx` is a
> near-verbatim extract of `bau060.pdf` and says of its own transferase
> look-up that it "requires updating"; `ptm_lookup.xlsx` is a row-for-row
> duplicate of `ptm_prefixes.md` (same 70 MOD IDs, nothing either way). Neither
> adds anything this skill needs — use the sources above instead.

# Curation Update From Paper
Version: 1.0 | Input: one primary paper + one existing-pathway event export |
Data model: V94/V95 | Output: a formatted curation update DOCX

This skill is the "a new paper landed, what do we do about it" workflow. It sits
between `/annotate-pathway-from-reviews-or-topic_name` (which builds a hierarchy
from scratch) and `/review-internal` (which reviews a finished report). Here the
pathway already exists and is already curated; the job is to work out the
**delta** a single new paper creates, and to hand the curator a document complete
enough to work from directly in the Curator Tool.

**This skill proposes. It never writes to the database.** Everything that needs a
database or ontology lookup the skill cannot authoritatively make is marked
PENDING CURATOR VERIFICATION.

---

## INPUTS

Required:
1. **The paper** — a PDF path, a PMID, or a DOI. A PDF is preferred; it is the
   only way to quote figure-level evidence reliably.
2. **The existing pathway** — either an exported event report (`.docx` from the
   Curator Tool's event export) or a pathway ST_ID. At least one is required; if
   given both, use both. The export shows the curator's own summations and
   existing regulators, which the ST_ID alone does not.

Optional:
- A release version label (e.g. `V97`) for the document header.
- A steer on scope ("only the entry steps", "ignore the host-response branch").

If the curator supplies only a paper and no pathway, ask which pathway it
affects rather than guessing — a paper often touches several.

---

## STEP 1 — READ BOTH INPUTS

**1a. Convert the event export to text.** On macOS, `textutil` is already
present and needs no dependency:

```
textutil -convert txt -output report.txt <export>.docx
```

Then map the hierarchy — every line matching `^[0-9.]+ .* \((Pathway|Reaction|BlackBoxEvent|Polymerisation|Depolymerisation|FailedReaction)\)$`
is an event. Build the numbered tree before reading any summations, so you know
the shape of what already exists.

**1b. Read the paper.** If it is a PDF and no PDF text extractor is installed,
this one-liner works on any Mac with no install (PDFKit ships with the OS):

```
cat > /tmp/pdf2txt.swift <<'EOF'
import PDFKit
let doc = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1]))!
for i in 0..<doc.pageCount { print("=== PAGE \(i+1) ==="); print(doc.page(at: i)?.string ?? "") }
EOF
swift /tmp/pdf2txt.swift <paper>.pdf > article.txt
```

Read the whole paper, not the abstract. The figure legends carry the
experimental detail (method, system, which panel) that every evidence sentence
needs, and the discussion usually states the authors' own inference chain, which
is the best raw material for the curation logic in section 2 of the output.

---

## STEP 2 — CHECK THE LIVE DATABASE (gk-central MCP)

If the `gk-central` MCP server is available, use it. It is a read-only nightly
copy of gk_central — see `/analysis-reactome-mcp` to install or enable it. If it
is not available, say so in the output's open-questions section and work from
the export alone; do not block.

Run at minimum:

```cypher
// the target pathway and its immediate children, with species
MATCH (p:Pathway {stId:$stId})-[:hasEvent]->(e)
OPTIONAL MATCH (e)-[:species]->(s)
RETURN e.stId, e.displayName, labels(e), collect(DISTINCT s.displayName)
ORDER BY e.stId
```

```cypher
// every PhysicalEntity whose name mentions the molecules the paper is about,
// so the proposal reuses existing entities instead of duplicating them
MATCH (pe:PhysicalEntity)
WHERE pe.displayName CONTAINS $token
RETURN pe.stId, pe.dbId, pe.displayName, labels(pe)
ORDER BY pe.displayName
```

What to take from this, and why each matters:

- **Compartment-specific entity instances already in the graph.** Reactome
  creates a separate entity per compartment. The chain of instances already
  curated for a process tells you exactly which compartment labels the curator
  used, and therefore which ones your new events must match.
- **The species convention actually in use — and `relatedSpecies`.** Query both
  slots, not just `species`:

  ```cypher
  MATCH (p:Pathway {stId:$stId})-[:hasEvent*]->(e:ReactionLikeEvent)
  OPTIONAL MATCH (e)-[:species]->(s)
  OPTIONAL MATCH (e)-[:relatedSpecies]->(rs)
  RETURN e.stId, e.displayName,
         collect(DISTINCT s.displayName)  AS species,
         collect(DISTINCT rs.displayName) AS relatedSpecies
  ```

  For a **host-pathogen pathway this is settled by the Guide, not a local
  convention**: `species` is the host (Homo sapiens for human curation, because
  the slot records the environment the reaction happens in) and `relatedSpecies`
  is the pathogen. See `Curator_Guide_V94_Extract.md` §3.2. An infection-pathway
  event annotated `Homo sapiens` while the experiments are in a non-human strain
  and cell line is therefore **correct and complete only if `relatedSpecies`
  carries the pathogen** — omitting it is an incomplete annotation, not a stylistic
  choice, and it is the error this skill is most likely to make. Do not flag the
  host/evidence species difference as a departure from V94; it is V94.

  The generic species/chimeric decision table in
  `/annotate-pathway-from-reviews-or-topic_name` applies to ordinary
  cross-species inference, **not** to host-pathogen events. If the branch's
  practice genuinely contradicts the Guide, say so in open questions and let the
  curator rule — but check the Guide extract before calling it a contradiction.
- **ST_IDs and DB_IDs for everything you propose reusing**, so the curator can
  paste them straight in.

---

## STEP 3 — GAP ANALYSIS

For every existing event the paper bears on, record one row: the existing event,
its ST_ID, and precisely what the paper changes. **Start the
`what_the_paper_changes` text with the verb** — "ADDS — …" — because the
renderer lifts that leading verb into its own colour-coded column. Use these
four verbs and no others, so the curator can triage at a glance:

- **ADDS** — a step with no existing event at all.
- **REFINES** — an existing event is right but under-specified; the paper gives
  mechanism, a participant, a compartment, or a regulator it lacks.
- **CONTRADICTS** — the paper's evidence is inconsistent with what is curated.
  Never silently propose replacing a curated event; state the conflict, cite
  both sides, and leave the call to the curator.
- **CONFIRMS** — independent support for something already curated. Worth a row
  because it may justify adding the new paper as an additional
  literatureReference without any structural change.

A paper that produces only CONFIRMS rows is a legitimate outcome — say so
plainly rather than manufacturing events to justify the document.

---

## STEP 4 — PROPOSE ENTITIES, THEN EVENTS

Entities first: an event cannot be specified before its participants exist.

**Entities.** For each, give proposed name, class (EWAS / Complex / DefinedSet /
CandidateSet / SimpleEntity / GenomeEncodedEntity / Polymer / OtherEntity),
compartment, and — critically — whether it **reuses** an existing entity found
in step 2 (give its ST_ID) or is genuinely new. Follow the naming conventions in
the companion references: colon-separated complex components, PTM prefixes,
ALL-CAPS human gene symbols, Capitalised non-human. Do not resolve or invent
UniProt, ChEBI, GO, or MONDO accessions — name the term and mark the accession
PENDING CURATOR VERIFICATION via OLS.

**Events.** One entry per proposed event, each carrying the full anatomy:
type, compartment, species, inputs, outputs, catalyst (with GO MF label),
regulators, precedingEvent, GO BP label, a **draft summation written in the
voice of the existing summations in the export** (match their register and
their habit of naming strain and cell line), evidence type, the verbatim
evidence sentence with its figure number, and the verified PMID fields.

Reaction vs BlackBoxEvent follows the standard evidence classification: direct
biophysical/biochemical demonstration gives a Reaction; knockdown, inhibitor,
or phenotype-level evidence gives a BlackBoxEvent. A step the paper proposes as
a model but does not directly demonstrate is a BlackBoxEvent at best, and the
flag must say so.

**Propose the container, not just the contents.** New events almost always need
a new subpathway to sit in. Give it as `proposed_subpathway` — name, parent,
GO BP, species, relatedSpecies, which events it holds, and a summation.

### Put each value in the slot curators actually use

Check `data_model_slots.md` before filling a slot you are unsure about; it
reports measured occupancy across released content rather than what a slot
means in principle. Three rules that follow from it, and that the renderer
checks:

- **GO BP goes on the subpathway, not on the reactions.** 48% of released
  pathways carry `goBiologicalProcess`; 5% of released reactions do. A
  reaction's molecular function belongs on `catalystActivity` → GO MF. Do not
  invent a GO BP label per reaction — that is how three non-existent GO terms
  entered the first rotavirus draft.
- **`relatedSpecies` on every event of a host-pathogen branch, or none.**
  `species` is the host, `relatedSpecies` the pathogen. Verify against the
  branch with the query in STEP 2.
- **`SimpleEntity` takes no species.** It does not appear on SimpleEntity in
  released content at any threshold.

Every ontology term you name must be confirmed in OLS before it is written
down — label *and* accession. A plausible-sounding GO label is not a GO label.

### What the data model cannot hold — check this before proposing an event

**A ReactionLikeEvent records a change in the set of participants or in their
compartments. Nothing else.** If the inputs and the outputs carry the same
components in the same compartments, there is no reaction to store, however
real and well-evidenced the physical change is.

Reactome has **no slot for conformation**. A step whose only product is a
differently-shaped version of the same entity in the same place cannot be
curated. "Transitions from the upright to the reversed conformation",
"refolds", "opens", "becomes membrane-inserted" — written as standalone events,
all of these are unrepresentable. A paper that resolves a mechanism into
physical sub-steps will hand you several of them; they are good science and
still not events.

What to do instead, in order of preference:

1. **Fold the state into the entity name of the step that does change
   something.** The conformational state travels as part of the name of the
   input to the next real event, so nothing is lost.
2. **Curate what the conformational change enables.** If the new shape exposes
   a binding site, the event is the binding. If it drives insertion into a
   membrane, the event is the compartment change. If it permeabilises a
   membrane, the event is the ion translocation.
3. **Say it in the summation.** The mechanism belongs in the prose of the
   event it explains, with its own literatureReference.

Never merge two such steps just to manufacture a difference between the sides.
If the paper's sub-steps collapse to one curatable event, propose one event and
say in the open questions which physical steps it covers.

`build_update_doc.py` checks this and prints a **data model check** listing any
event whose sides match, or whose name reads as a conformational change within
a single compartment. It is advisory rather than blocking, because a legitimate
event can share a compartment, but every flagged event needs an answer before
instances are created.

The same rule retires `isChimeric` from the event anatomy: it is not part of
what this skill proposes. Species and chimeric handling follow the pathway's
own convention as established in step 2.

---

## STEP 5 — VERIFY EVERY PMID (NON-NEGOTIABLE)

Resolve and verify every PMID against NCBI E-utilities
(`eutils.ncbi.nlm.nih.gov`, allowlisted for `WebFetch` in this repo's
`.claude/settings.json`). **Never** take a PMID from training data, from a
web_search snippet, or from a reference list without resolving it.

This is the same protocol `/annotate-pathway-from-reviews-or-topic_name` uses,
and the full ten steps live in that skill's "MANDATORY REFERENCE VERIFICATION
PROTOCOL" — read it there rather than relying on a summary. In brief:

1. **Batch by DOI** where the paper's reference list prints one:
   `esearch.fcgi?db=pubmed&term=<doi1>[AID]+OR+<doi2>[AID]+...&retmode=json&retmax=<N>`
   (URL-encode `/` as `%2F`).
2. **Batch ESummary** the returned ids:
   `esummary.fcgi?db=pubmed&id=<ids>&retmode=json`.
3. **Five-field match** every record: first-author surname, journal, year, key
   title words, and the specific claim. A DOI you reconstructed rather than read
   verbatim off the page is a common source of a confident wrong answer — the
   five-field check is what catches it. When it fails, re-resolve by
   title+author ESearch and adopt the result **only** if `idlist` has exactly
   one entry.
4. **Tag every PMID** with its `pmid_source`: `esummary:pmid`, `esearch:doi`,
   `esearch:title-author`, `inline:<pdf basename>`, or `null`. A PMID with any
   other origin is fabricated and forbidden. If resolution fails, ship the DOI
   and leave the PMID blank.

Report any correction you made in the open-questions section, in the form
"PMID CORRECTED: … resolved via …". A silent swap is an annotation error.

A newly published paper may have no PMC record yet; that is normal. Set the PMC
field to a short note rather than a broken link.

### The five-field check is enforced, not trusted

Doing step 3 by hand and believing the result is how a wrong PMID ships. Run it
mechanically before rendering:

```
python3 verify_references.py <spec>.json
```

It resolves every reference (and `source_paper`) against ESummary and compares
the record with the citation the spec claims on **first author surname,
initials, year, journal and title**. A title that does not overlap, or a
different first author, is an `ERROR` and exits non-zero; a year off by one
(epub ahead of print) is a `WARN`. Anything it cannot resolve is reported as
`UNCHECKED` — never as correct.

`build_update_doc.py` runs this automatically and **refuses to render** if any
reference fails. Do not reach for `--skip-ref-check` to get past a failure: it
is for working offline, and it stamps "NOT verified against PubMed" into the
document's metadata table in red.

This check exists because of a real near-miss. A DOI reconstructed from a
reference list (rather than read verbatim off the paper) resolved through
ESearch `[AID]` to PMID 24796500 — a Cav1.4 night-blindness paper — in place of
Elaid et al. 2014 on VP7 membrane permeabilisation. It was caught only by a
human comparing fields. Feed that PMID to `verify_references.py` and it fails
on both title and first author.

---

## STEP 6 — WRITE THE DOCUMENT

Build a spec JSON and render it:

```
python3 build_update_doc.py <topic-slug>_curation_update.json -o "<Topic> Curation Update.docx"
```

`build_update_doc.py` (in this skill directory) renders the formatted DOCX:
title block, metadata table, and the nine numbered sections — Summary,
Curation rationale and logic, Gap analysis, Proposed new physical entities,
Proposed new events, Ontology terms required, References, Open questions,
Pre-submission checklist. Run it with `--validate` first; it refuses a spec in
which any event carries a bare PMID without a `pmid_source`, which is the
mechanical guard against step 5 being skipped.

Sections 3–5 are rendered **landscape** and the rest portrait; the script
inserts the section breaks itself.

Requires `python-docx` and `matplotlib` (both pinned in the repo's
`requirements.txt`). Invoke it as plain `python3 build_update_doc.py …` —
**not** `python3 -I`, which suppresses the user site-packages directory where
these are typically installed. Without matplotlib the document still builds,
with full attribute tables in place of the diagrams.

### What the script checks and draws for you

| Flag | Default | Effect |
|---|---|---|
| *(none)* | on | Verifies every reference against PubMed; **refuses to render on a mismatch** |
| *(none)* | on | Asks reactome.org which ST_IDs are released, and links only those |
| `--skip-ref-check` | off | Offline only. Stamps "NOT verified against PubMed" into the metadata table |
| `--skip-link-check` | off | Skips the release probe; unreleased ST_IDs then render as links that 404 |
| `--no-graphics` | off | Omits diagrams and restores the full per-event attribute tables |
| `--keep-figures DIR` | temp | Also writes the generated PNGs to `DIR` |

**ST_IDs and links.** reactome.org serves released content only. A pathway still
being curated has `doRelease=false` in gk_central, so `/content/detail/<id>`
404s — which made every ST_ID in the first rotavirus draft a dead link. The
script probes ContentService and renders an unreleased ID as plain text marked
"(not yet released)" rather than as a link that cannot work. Expect most or all
ST_IDs in an in-progress branch to come back unreleased; that is correct.

**Reaction diagrams.** One per event in section 5, drawn by
`reaction_graphic.py`: inputs left, reaction centre, outputs right, catalyst
above, regulators below, and the preceding/following events as chips top and
bottom. Participants with an ST_ID are drawn solid and tagged with it; those
without are dashed and tagged NEW, so what the paper adds is visible against
what is reused. Because the diagram carries the participants, compartment and
chain position, those rows are dropped from the table beneath it and the rest
is laid out two pairs per row.

Keep entity strings in the shape `Name [compartment] (R-HSA-123)` — the renderer
parses all three parts. Put any rationale after an em dash
(`ARP2/3 complex — positive regulator, inferred`); the diagram shows the entity
and a `+`/`−` sign, and the prose stays in the table.

### Keep sections 1 and 2 short

These two are read first and are the easiest to overwrite. Hold them to a
budget:

- **`summary` — three paragraphs, ~200 words total.** One on what the pathway
  already curates and where the gap is, one on what the paper shows, one on the
  verdict in gap-analysis verbs. The recap of existing curation is orientation,
  not a review: name the branch, the relevant events and the gap, then stop.
  Do not retell the paper's mechanism step by step — that is section 5's job,
  and every step is already a row there.
- **`rationale` — three paragraphs, ~200 words total.** Open on the first real
  decision. Do not restate standard curation logic, and do not announce that
  you are not restating it: naming, evidence classes, compartments and the rule
  that annotation species should match the experimental support are all in
  Curator Guide V94, the reader is a curator, and a paragraph saying "the Guide
  applies" tells them nothing. Spend the words only on decisions specific to
  this paper: where the new subpathway hangs and why, how event typing follows
  this paper's evidence, and any deliberate departure from the Guide — which
  must stay, and must also appear in section 8.

### Structure the open questions

`open_questions` takes objects, not bare strings:

```json
{"priority": "HIGH", "tag": "STRUCTURAL DECISION",
 "question": "How should E6-E8 relate to the existing release events?",
 "affects": "E6-E8"}
```

`priority` is HIGH / MEDIUM / LOW / INFO and drives the colour and the sort
order; the section renders as a tickable checklist. Plain strings still work —
they are parsed for a leading ALL-CAPS tag and scored by keyword — but say the
priority rather than leaving it to be guessed.

Optionally add a `decision_flow` and the section opens with a flowchart:

```json
"decision_flow": [
  {"id": "Q1", "text": "How do E6-E8 relate to existing release events?",
   "answers": [{"label": "parallel", "to": "Q2"},
               {"label": "reference only", "to": "REF"}]},
  {"id": "REF", "text": "Add as a literatureReference only", "terminal": true}
]
```

Declare it only when the questions genuinely gate one another. Nothing is
inferred: with no `decision_flow` there is no chart, which is the right outcome
for a set of independent questions. An invented decision order is worse than
none.

A worked example of a complete spec ships alongside it as `sample_spec.json`.

Keep the spec JSON next to the DOCX. It is the reproducible record, and it is
far easier to amend and re-render than to hand-edit Word.

**Delivery.** Write locally. Do not upload. The curator uploads to the Team
Drive themselves — dragging the DOCX into Drive converts it to a Google Doc with
the formatting intact. Writing to Drive via the API would need a Docs write
scope, which is broader than any token this repo's skills hold, and
`/admin-drive-readme`'s token is read-only Drive and scoped to that skill alone.

---

## AGENTIZATION

Two parts of this workflow are worth delegating to subagents, and the rest is
not.

**Worth delegating.** Both are independent and read-heavy:

- *Gap analysis sweep* — on a large pathway (50+ events), give one subagent the
  converted `report.txt` and the paper's findings, and ask it to return only the
  gap-analysis rows. It reads a lot of summation text and returns a table.
- *Entity reuse sweep* — give one subagent the list of molecules the paper
  involves and have it run the step-2 Cypher per molecule, returning only the
  ST_ID/name/class rows that are candidate reuses.

Launch them in a single message so they run concurrently.

**Not worth delegating.** PMID verification must stay with the main agent: it is
the step where a plausible-looking fabrication does the most damage, and it
needs the five-field judgment that is hard to specify in a subagent prompt.
Summation drafting also stays — it depends on having read the existing
summations closely enough to match their voice.

---

## ALWAYS FLAG

- Evidence species or cell line differs from the annotated species — state both,
  and state which convention the pathway already uses.
- The paper's model step is inferred rather than demonstrated.
- A CONTRADICTS row — never resolve it yourself.
- In vitro reconstitution standing in for a cellular event.
- A participant whose identity, stoichiometry, or oxidation state you inferred.
- Any entity that may duplicate an existing one you could not conclusively match.
- GO BP/MF/CC, ChEBI, MONDO accessions — PENDING CURATOR VERIFICATION via OLS.
- UniProt accessions — not resolved here.
- A proposed event whose compartment label you could not match to one already in
  use in the pathway.
- Any PMID that would not resolve, and any PMID you corrected.

---

## WORKFLOW SUMMARY

| Step | Action |
|---|---|
| 1 | Read both inputs — convert the export with `textutil`, extract the PDF with the PDFKit one-liner, map the existing hierarchy |
| 2 | Query gk-central for existing events, entities, compartment labels, and the pathway's actual species convention (skip gracefully if unavailable) |
| 3 | Gap analysis — one ADDS/REFINES/CONTRADICTS/CONFIRMS row per affected event |
| 4 | Propose entities (marking reuses), then events with full anatomy and draft summations |
| 5 | Verify every PMID via batched E-utilities, five-field match, `pmid_source` tag on each |
| 6 | Build the spec JSON, `--validate`, render the DOCX, leave it locally for the curator to upload |

No approval gate between steps. One stop at the end: the curator reviews the
whole document.
