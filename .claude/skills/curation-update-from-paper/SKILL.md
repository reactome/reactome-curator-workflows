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

> Companion references, reused from sibling skills in this repo — read the ones
> relevant to what you are proposing rather than all of them:
> - `../annotate-pathway-from-reviews-or-topic_name/Reactome_RLE_Annotation_Reference_V94.md`
>   — condensed V94 ReactionLikeEvent rules: naming, compartments, evidence
>   classes, catalyst/regulation, species and chimeric handling.
> - `../review-internal/Curator_Guide_V94.pdf` — the authoritative standard.
> - `../review-internal/Claude_ReactomeDataModelGlossary_V95_Final.docx.pdf` —
>   data model terms and entity-class semantics.
> - `../review-internal/EWAS_name_rules.docx` and `../review-internal/ptm_prefixes.md`
>   — EWAS naming and PTM prefix conventions, for any modified-protein entity.
> - `../review-internal/Small_molecule_renaming.xlsx` — preferred small-molecule
>   names, for any SimpleEntity you propose.
> - `../review-internal/Rules_for_automatic_reaction_typing.docx` — consult when
>   deciding Reaction vs BlackBoxEvent vs Polymerisation.

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
- **The species convention actually in use.** Do not assume. Viral-infection
  pathways in particular often annotate events as `Homo sapiens` while the
  supporting experiments are in a non-human strain and a non-human cell line,
  naming the strain and cell line in the summation instead of creating an
  inferred-from pair. **Follow the convention the pathway already uses**, and
  flag the divergence between evidence species and annotated species explicitly
  rather than silently applying the generic species/chimeric rules from
  `/annotate-pathway-from-reviews-or-topic_name`. If the pathway's convention
  and the V94 rule disagree, say so in open questions and let the curator rule.
- **ST_IDs and DB_IDs for everything you propose reusing**, so the curator can
  paste them straight in.

---

## STEP 3 — GAP ANALYSIS

For every existing event the paper bears on, record one row: the existing event,
its ST_ID, and precisely what the paper changes. Use these four verbs and no
others, so the curator can triage at a glance:

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
type, compartment, species, isChimeric, inputs, outputs, catalyst (with GO MF
label), regulators, precedingEvent, GO BP label, a **draft summation written in
the voice of the existing summations in the export** (match their register and
their habit of naming strain and cell line), evidence type, the verbatim
evidence sentence with its figure number, and the verified PMID fields.

Reaction vs BlackBoxEvent follows the standard evidence classification: direct
biophysical/biochemical demonstration gives a Reaction; knockdown, inhibitor,
or phenotype-level evidence gives a BlackBoxEvent. A step the paper proposes as
a model but does not directly demonstrate is a BlackBoxEvent at best, and the
flag must say so.

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

Requires `python-docx` (pinned in the repo's `requirements.txt`). Invoke it as
plain `python3 build_update_doc.py …` — **not** `python3 -I`, which suppresses
the user site-packages directory where `python-docx` is typically installed.

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
