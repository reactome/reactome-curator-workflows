# Reactome Curator Workflows

## What This Repository Is

This repository contains shared Claude Code workflow skills for Reactome curation
and release operations. Skills are markdown-based instruction files that Claude Code
reads directly — any curator with Claude Code installed can clone this repo and
immediately run any skill. No build process, no dependencies beyond Claude Code itself
(and Python 3 + pandas for the DOI batch skill).

Skills are added incrementally as we identify and vet repeatable workflows.
This repo is curator-driven; if you develop a workflow worth sharing, open a PR.

---

## Repository Structure

```
reactome-curator-workflows/
├── CLAUDE.md                                              ← you are here
├── README.md                                              ← setup instructions for new users
├── Reactome_CuratorWorkflows_ClaudeCode_Guide_v1_3.docx  ← full onboarding guide
├── .gitignore
├── chrome-extensions/
│   └── pmid-tagger/                                      ← Chrome extension: prefix PDF downloads with PMID-<id>_
│       ├── manifest.json
│       ├── background.js
│       └── content.js
└── .claude/
    ├── settings.json                                      ← Claude Code host/network allowlist
    └── skills/
        ├── internal-module-review/
        │   ├── SKILL.md                                   ← /internal-module-review
        │   ├── Reactome_InternalReview_PROMPT_v1_4.docx   ← source prompt spec
        │   ├── Reactome_InternalReview_TEMPLATE.docx      ← companion output template
        │   ├── Claude_ReactomeDataModelGlossary_V95_Final.docx.pdf  ← data model reference
        │   ├── Curator_Guide_V94.pdf                      ← authoritative curation standard
        │   ├── EWAS_name_rules.docx                       ← EWAS (protein/peptide) naming rules
        │   ├── Rules_for_automatic_reaction_typing.docx   ← event/reaction naming rules
        │   ├── ptm_lookup.xlsx                            ← PSI-MOD ID → PTM prefix table (source)
        │   ├── ptm_prefixes.md                            ← PTM prefix table in plain text (auto-loaded)
        │   ├── Small_molecule_renaming.xlsx               ← canonical small molecule name lookup
        │   └── bau060.pdf                                 ← naming conventions reference paper
        ├── annotate-pathway-from-reviews-or-topic_name/
        │   ├── SKILL.md                                   ← /annotate-pathway-from-reviews-or-topic_name
        │   ├── README.md                                  ← full workflow, citation block format, species/chimeric rules
        │   └── Reactome_RLE_Annotation_Reference_V94.md  ← condensed RLE annotation rules (V94 Curator Guide + V90 Glossary)
        ├── extract-reactions/
        │   ├── SKILL.md                                   ← /extract-reactions
        │   └── (extract-reactions.zip — archived copy in parent skills/ dir)
        ├── generate-doi-batch/
        │   ├── SKILL.md                                   ← /generate-doi-batch
        │   └── generate_crossref_xml.py                  ← DOI batch XML generator script
        └── update-gdrive-readme/
            ├── SKILL.md                                   ← /update-gdrive-readme
            └── update_drive_readme.py                    ← Team Drive README regenerator script
```

---

## The Reactome Curation Context

**What Reactome is:** A free, open-source, curated and peer-reviewed pathway
database. Human pathways are manually curated and then computationally inferred
across ~15 other species. The knowledgebase is used by researchers worldwide for
pathway analysis, drug target identification, and systems biology.

**Institutional homes:** OICR (Toronto), EMBL-EBI (Hinxton),
NYU Grossman School of Medicine (New York), St. John's University (New York).

**Key public resources:**
- Reactome website: https://reactome.org
- GitHub org: https://github.com/reactome
- Pathway Browser: https://reactome.org/PathwayBrowser/
- RESTful API: https://reactome.org/ContentService/
- OLS4 (GO term lookup): https://www.ebi.ac.uk/ols4/

---

## Curation Model

Reactome curates human biology at the reaction level. Each reaction encodes:
- Input and output PhysicalEntities (proteins, complexes, small molecules, DNA/RNA)
- Catalyst activity (GO molecular function + catalytic PhysicalEntity)
- Regulation (positive/negative regulators)
- Literature references (PubMed IDs)
- Species (human by default; inferred for others)

Reactions are grouped into Pathways, which are grouped into higher-level Pathways.
Every curated entity has a stable DB_ID and a human-readable ST_ID
(e.g., R-HSA-XXXXXXX for human reactions/pathways).

**Curator Guide:** V94 (current). Governs naming conventions, complex/set
representation, evidence codes, cross-reference standards (UniProt, ChEBI,
NCBI Gene, Ensembl, GO), disease pathway structure, and orthology inference rules.
A copy is in `.claude/skills/internal-module-review/Curator_Guide_V94.pdf`.

**Data Model Glossary:** V95 (current). Reference for data model terms, entity
types, and relationship semantics used in curation and review.
A copy is in `.claude/skills/internal-module-review/Claude_ReactomeDataModelGlossary_V95_Final.docx.pdf`.

---

## Release Cycle

Reactome releases approximately 3–4 times per year. Each release involves:
- Curation of new pathways and updates to existing ones
- Internal peer review of new content (using `/internal-module-review`)
- DOI assignment via CrossRef batch XML submission, schema 5.3.1
  (using `/generate-doi-batch`)
- Species inference pipeline
- Data export and QC
- Public release and announcement

**DOIs.xlsx** (maintained in the Reactome Team Drive, not in this repo) tracks
DOIs across release versions with curator and reviewer assignments.
The `generate-doi-batch` skill reads it from a local path specified at runtime.

---

## Available Skills

### `/internal-module-review`
Formal structured internal review of a Reactome pathway report against
Curator Guide V94 standards. Produces a prioritized review DOCX with
seven sections. Requires the pathway report DOCX and Curator Guide PDF
to be uploaded to the conversation before invoking.
Supports optional modifiers: `disease`, `drug`, `large` (50+ reactions).

Reference materials in skill directory:
- `Curator_Guide_V94.pdf` — authoritative curation standard
- `Reactome_InternalReview_PROMPT_v1_4.docx` — structured review prompt spec
- `Reactome_InternalReview_TEMPLATE.docx` — output template
- `Claude_ReactomeDataModelGlossary_V95_Final.docx.pdf` — data model glossary
- `EWAS_name_rules.docx` — EWAS (protein/peptide) naming rules (Section 7)
- `Rules_for_automatic_reaction_typing.docx` — reaction/event naming rules (Section 7)
- `ptm_prefixes.md` — PTM prefix lookup in plain text, auto-loaded (Section 7)
- `Small_molecule_renaming.xlsx` — canonical small molecule names (Section 7)
- `bau060.pdf` — naming conventions reference paper (Section 7)

---

### `/annotate-pathway-from-reviews-or-topic_name`
AI-assisted pre-curation workflow (v1.3, April 2026). Proposes a complete Reactome
pathway hierarchy — pathway names, subpathway names, and reaction names — and verifies
primary literature citations using a mandatory ten-step PMID verification protocol.

Requires claude.ai Projects (Pro/Team/Enterprise) or the Claude API. PubMed and
PMC MCP servers are recommended for live PMID verification and full-text fetch.

**Two entry modes:**

- **Mode A** — Curator supplies references (PMIDs, DOIs, or uploaded PDFs);
  assistant reads the papers and proceeds directly to Phase 1.
- **Mode B** — Curator supplies a biological topic; assistant performs live web
  searches for primary literature, presents a ranked candidate reference list,
  and waits for curator confirmation before proceeding.

**Session workflow:**

```
Session opening
    │
    ├── Mode A: Curator supplies references
    │       └── Assistant reads papers → proceeds to Phase 1
    │
    └── Mode B: Curator supplies a topic
            │   Assistant searches → presents ranked reference list
            └── STOP — curator confirms or modifies list
                    └── Curator replies "proceed"

Phase 1 — Hierarchy proposal
    Proposed pathway / subpathway / reaction names
    Evidence species flags (human / non-human / chimeric)
    Non-human and chimeric reactions paired with inferred human reactions
    Proceeds immediately to Phase 2 — no approval gate

Phase 2 — Literature verification
    Ten-step PMID verification protocol per reaction
    PMC full-text fetch and verbatim evidence sentence extraction
    Standard or inferred-human citation blocks
    Subpathway by subpathway — no stops between subpathways

STOP — full output presented for curator review
```

**Ten-step PMID verification protocol** (mandatory for every reaction in Phase 2):

1. Search each PMID individually and confirm the PubMed record exists
2. Match all five identifying fields: first author surname, journal, year, key
   title words, specific experimental claim
3. Flag any unverified PMID explicitly — never present an unverified PMID as correct
4. Confirm the paper contains direct evidence for the specific reaction; if it is a
   review, trace to the underlying primary paper
5. Present all PMIDs as clickable hyperlinks (`https://pubmed.ncbi.nlm.nih.gov/[PMID]/`)
6. Fetch primary paper full text via PMC where available
7. Locate and quote the specific experimental evidence sentence, including method,
   proteins, cell type or system, and figure number
8. Flag evidence quality mismatches (overexpression only, murine only, mixed species,
   indirect evidence)
9. For review inputs: trace the review reference number to the underlying primary
   paper and verify the PMID matches
10. Flag evidence relevance mismatches if the paper does not directly support the
    specific mechanistic claim

**Citation block formats:**

Standard (direct or indirect evidence):
```
Reaction name:    [name from hierarchy]
Primary PMID:     https://pubmed.ncbi.nlm.nih.gov/[PMID]/
Primary PMC URL:  https://pmc.ncbi.nlm.nih.gov/articles/PMCXXXXXXX/
Authors/Year:     [First author et al., Year, Journal]
Primary evidence: "[verbatim sentence from primary paper including method,
                  proteins, cell type or system, and figure number]"
Evidence type:    DIRECT / INDIRECT / OVEREXP ONLY
Species:          [human / murine / other]
Flags:            [mismatches, gaps, curator actions required]
```

Inferred human reaction:
```
Reaction name:    [inferred human reaction name]
Evidence type:    INFERRED FROM NON-HUMAN / INFERRED FROM CHIMERIC
Species:          Homo sapiens (inferred)
inferredFrom:     [paired non-human or chimeric reaction name]
Primary PMID:     https://pubmed.ncbi.nlm.nih.gov/[PMID]/
Authors/Year:     [same as paired evidence reaction]
Flags:            No independent human experimental evidence. Curator should
                  confirm human orthology is supported before submission.
```

**Species and chimeric reaction logic:**

| Experimental situation | Reaction type | isChimeric | Inferred human required |
|---|---|---|---|
| Human proteins/cells only | Human reaction | FALSE | No |
| Single non-human species only | Non-human reaction | FALSE | Yes |
| ≥2 species mixed in same assay | Chimeric reaction | TRUE | Yes |

Non-human proteins use initial capitalisation (Jak2); human proteins use ALL-CAPS (JAK2).

**Evidence classification:**

| Class | Reaction type | Examples |
|---|---|---|
| DIRECT | Reaction | co-IP, in vitro reconstitution, SPR/ITC, NMR, crystallography, direct enzymatic or cleavage assay |
| INDIRECT | BlackBoxEvent (provisional) | KO, rescue, overexpression, inhibitor treatment, domain deletion |
| INSUFFICIENT | Do not annotate | Microarray alone, bulk proteomics alone, ChIP-seq alone, computational prediction alone, review statement without primary citation |

**What is out of scope** (curator's responsibility, requires database tooling):
- Neo4j / gk_central queries (duplicate detection, hierarchy placement)
- OLS ontology term verification (GO, ChEBI, MONDO, UBERON accessions)
- UniProt REST API verification (sequence length, PTM coordinates, isoform selection)
- GtoPdb drug interaction checks
- Full annotation table population in the Curator Tool
- Disease flag resolution and pathway diagram drawing

All fields requiring these steps are marked **PENDING CURATOR VERIFICATION** in output.

**Limitations:**
- **PMID fabrication risk.** The ten-step protocol is designed to catch fabricated
  PMIDs. Curators should independently confirm all PMIDs before database submission.
- **Full-text access.** PMC full text is fetched for open-access papers. Paywalled
  papers fall back to web search; unavailable papers are flagged as incomplete.
- **Knowledge cutoff.** The underlying model may not be aware of very recent
  publications. Mode B performs live web searches but curators should verify coverage.
- **Ontology accessions.** GO, ChEBI, MONDO, and UniProt accessions are not resolved;
  all marked PENDING CURATOR VERIFICATION.

**Reference materials in skill directory:**
- `SKILL.md` — invocation instructions for Claude Code
- `README.md` — full workflow documentation, citation formats, evidence table,
  limitations, version history, and contribution notes
- `Reactome_RLE_Annotation_Reference_V94.md` — condensed RLE annotation rules
  extracted from V94 Curator Guide and V90 Data Model Glossary; covers RLE
  subclasses, mandatory fields, naming conventions, compartment rules, evidence
  rules, species/chimeric rules, PhysicalEntity classes, catalyst/regulation,
  gene expression patterns, summation rules, reaction balance, disease RLE
  specifics, data model glossary, and a quick-reference table

---

### `/generate-doi-batch`
Runs `generate_crossref_xml.py` to produce a CrossRef DOI batch XML file
for a release version. Requires DOIs.xlsx locally and Python 3 + pandas.
Handles input validation, error interpretation, and post-run checklist.

---

### `/update-gdrive-readme`
Regenerates the Reactome Team Drive README as a richly formatted Google Doc.
On every run: clears the existing doc, walks the live Team Drive folder inventory
via the Drive API, and rewrites the doc with styled headings, linked folder tables,
a contacts table, and a live folder inventory tree. Requires Python 3 and the
Google API client libraries; uses OAuth user credentials by default (service account
optional). Supports `--dry-run` (preview only) and `--depth N` (inventory depth).

Credentials are stored at `~/.config/reactome/` on each user's local machine —
outside the repo — so they are never committed or shared across users.
Override the path via `GOOGLE_APPLICATION_CREDENTIALS` env var.

Reference materials in skill directory:
- `SKILL.md` — invocation instructions, prerequisites, error guide
- `update_drive_readme.py` — Team Drive README regenerator script

---

### `/extract-reactions`
Extracts a reaction graph for a named pathway from one or more medical/biology
review PDFs. Writes two artefacts:
- `<pathway-slug>_reactions.csv` — columns: Title, Input, Output, Catalyst,
  Regulators, Reviews, Source1–Source5 (Reviews lists supplied PDFs; each
  Source cell holds one URL via PubMed > PMC > DOI > publisher ladder;
  any 6th+ sources dropped)
- `<pathway-slug>_references.html` — companion link list of every cited
  primary reference

Text labels with mandatory compartments; inserts transport reactions on
compartment changes; emits reversible reactions as forward+reverse rows.
Connectivity is not required — gaps are flagged with parenthesized entries
and parallel branches get `##` subtitle rows.

PMID resolution uses NCBI E-utilities on `eutils.ncbi.nlm.nih.gov`: one
batched ESearch + one batched ESummary for DOI-bearing refs, plus a per-ref
title+author ESearch fallback (strict single-match) for refs with no DOI.
PMIDs are NEVER recovered from training data; failed/ambiguous lookups fall
through to DOI URLs or blanks. Pre-curation draft, not a curated entry.

---

## Chrome Extensions

### `pmid-tagger`  (`chrome-extensions/pmid-tagger/`)
Automatically prefixes PDF downloads with `PMID-<id>_` when initiated from
a PubMed or PMC article page. Keeps downloaded papers consistently named
with their PMID, making it easier to match PDFs to references during curation.

**Installation:**
1. Open Chrome → `chrome://extensions/`
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked** → select `chrome-extensions/pmid-tagger/`
4. Active immediately — no configuration required

---

## Claude Code Configuration

### `.claude/settings.json`
Contains the Claude Code host/network allowlist for this project.
Allowlisted hosts include `eutils.ncbi.nlm.nih.gov` (required by
`/extract-reactions` for NCBI E-utilities PMID resolution). Claude Code
reads this file automatically when launched from the repo root.

> **claude.ai users:** Add `eutils.ncbi.nlm.nih.gov` manually via
> **Settings → Capabilities → Domain allowlist**, otherwise PMID resolution
> calls will fail and refs will fall through to DOI URLs or blanks.

---

## Team

- Marc Gillespie (NYU / SJU) — repo maintainer
- Lisa Matthews (NYU)
- Joel Weiser (OICR)
- Guanming Wu (OHSU)
- Adam Wright (OICR)

For curation standards questions: consult Curator Guide V94 or the Reactome
curator Slack channel.
For questions about this repo or its skills: open an issue or contact Marc.

---

## Adding a New Skill

1. Create a directory under `.claude/skills/` named for your skill
2. Add `SKILL.md` with YAML frontmatter (`name`, `description`) and
   step-by-step instructions
3. Add any supporting files the skill references (scripts, templates,
   reference docs)
4. Open a PR with a brief description of what the skill does and when to use it

Keep skills focused on a single repeatable workflow. See existing `SKILL.md`
files for the expected format and level of detail.

---

## What This Repo Is Not

- Not a replacement for the Curator Guide (canonical version in Team Drive)
- Not a place for raw data files (DOIs.xlsx, release databases, pathway reports)
- Not a code repository — production scripts belong in the appropriate
  `reactome/*` repos. Scripts here are workflow helpers used directly by
  curators via Claude Code.
