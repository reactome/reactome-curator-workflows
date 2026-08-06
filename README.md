# reactome-curator-workflows

Shared Claude Code workflow skills for Reactome curation and release operations.

## What This Is

This repository contains Claude Code skills — markdown-based instruction files that
Claude Code reads directly. Any curator with Claude Code installed can clone this repo
and immediately run any skill. No build process, no configuration beyond cloning.

Skills are added incrementally as we identify and vet repeatable workflows.
See `CLAUDE.md` for full project context.

---

## Documentation

Full setup and usage instructions are in:

**[Reactome_CuratorWorkflows_ClaudeCode_Guide.docx](./Reactome_CuratorWorkflows_ClaudeCode_Guide.docx)**

This covers one-time prerequisites, cloning the repository, running each skill, and
how to add new skills. Start here if you are setting up for the first time.

For administering the Reactome Anthropic API organization and API-key billing
(workspaces, spend limits, key rotation, cost controls), see
**[API_Billing_Best_Practices.md](./API_Billing_Best_Practices.md)**.

---

## Setup (Quick Reference)

### 1. Prerequisites (one-time)

Install Git: https://git-scm.com/downloads

Install Claude Code:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

Set your Anthropic API key (add to `~/.zshrc`):

```bash
export ANTHROPIC_API_KEY=your-key-here
```

Install Python dependencies (use `pip3` on macOS):

```bash
pip3 install pandas openpyxl
```

### 2. Clone the repository

```bash
git clone https://github.com/reactome/reactome-curator-workflows.git ~/Developer/reactome-curator-workflows
cd ~/Developer/reactome-curator-workflows
```

### 3. Run Claude Code

```bash
cd ~/Developer/reactome-curator-workflows
claude
```

Claude Code automatically reads `CLAUDE.md` and loads all skills at session start.
The `.claude/settings.json` file allowlists external hosts (e.g., NCBI E-utilities)
required by certain skills.

### 4. Keep up to date

```bash
cd ~/Developer/reactome-curator-workflows
git pull
```

---

## Available Skills

### `/review-internal`

Formal structured internal review of a Reactome pathway report against Curator Guide
V94 standards. Produces a prioritized review DOCX with seven sections. Upload the
pathway report DOCX and Curator Guide PDF to the conversation before invoking.
Optional modifiers: `disease`, `drug`, `large`.

**Sections:**

| Section | What it covers |
|---|---|
| 1 | Reaction connectivity, including Input→Output entity chain verification |
| 2 | GO Biological Process assignments |
| 3 | Literature references |
| 4 | Grammar, clarity, and summation quality |
| 5 | General curation quality |
| 6 | Prioritized issue summary (consolidated table, all sections) |
| 7 | Entity and event name conventions |

Section 7 checks every entity and event name against the Reactome controlled vocabulary
(Jupe et al. 2014) and associated naming rules. Five subsections cover EWAS/peptide names
(gene symbol, coordinates, PTM prefixes), reaction/event names (all 11 CV classes), small
molecule names, complex names (colon separator, square bracket hierarchy notation), and
set names (comma separator, candidate member notation). Naming convention reference files
are automatically loaded — no additional uploads required.

```
/review-internal "HHV8 Infection" R-HSA-9521541 "Lisa Matthews" 2026-04-15
```

---

### `/annotate-pathway-from-reviews-or-topic_name`

AI-assisted pre-curation workflow (v1.3, April 2026). Proposes a complete Reactome
pathway hierarchy — pathway names, subpathway names, and reaction names — and verifies
primary literature citations using a mandatory ten-step PMID verification protocol.

Requires claude.ai Projects (Pro/Team/Enterprise) or the Claude API. PubMed and PMC
MCP servers are recommended for live PMID verification and full-text fetch.

**Two entry modes:**

- **Mode A** — Curator supplies references (PMIDs, DOIs, or uploaded PDFs); assistant
  reads the papers and proceeds directly to Phase 1.
- **Mode B** — Curator supplies a biological topic; assistant performs live web searches
  for primary literature, presents a ranked candidate reference list, and waits for
  curator confirmation before proceeding.

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

**Citation block formats:**

Standard (direct or indirect evidence):
```
Reaction name:    [name from hierarchy]
Primary PMID:     https://pubmed.ncbi.nlm.nih.gov/[PMID]/
Primary PMC URL:  https://pmc.ncbi.nlm.nih.gov/articles/PMCXXXXXXX/
Authors/Year:     [First author et al., Year, Journal]
Primary evidence: "[verbatim sentence including method, proteins, cell type, figure]"
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
| DIRECT | Reaction | co-IP, in vitro reconstitution, SPR/ITC, NMR, crystallography, direct enzymatic assay |
| INDIRECT | BlackBoxEvent (provisional) | KO, rescue, overexpression, inhibitor treatment, domain deletion |
| INSUFFICIENT | Do not annotate | Microarray alone, bulk proteomics alone, ChIP-seq alone, computational prediction alone |

**What is out of scope** — handled separately by the curator using database tooling:
Neo4j/gk_central queries, OLS ontology verification, UniProt REST API verification,
GtoPdb drug checks, full annotation table population, disease flag resolution, and
pathway diagram drawing. All such fields are marked **PENDING CURATOR VERIFICATION**.

**Key limitations:**

- **PMID fabrication risk.** The ten-step protocol catches fabricated PMIDs, but
  curators should independently confirm all PMIDs before database submission.
- **Full-text access.** PMC full text fetched for open-access papers only; paywalled
  papers fall back to web search and are flagged if unavailable.
- **Knowledge cutoff.** Mode B performs live searches, but curators should verify that
  the most recent relevant primary papers have been captured.
- **Ontology accessions.** GO, ChEBI, MONDO, and UniProt accessions are not resolved
  in this workflow — all marked PENDING CURATOR VERIFICATION.

For the full workflow documentation, citation block reference, species/chimeric rules,
and version history, see
`.claude/skills/annotate-pathway-from-reviews-or-topic_name/README.md`.

```
/annotate-pathway-from-reviews-or-topic_name
```

---

### `/release-doi-batch`

Generates a CrossRef DOI batch XML file for a release using DOIs.xlsx. Requires
DOIs.xlsx locally (from Team Drive) and Python 3 + pandas.

```
/release-doi-batch V94
```

---

### `/extract-reactions`

Extracts a reaction graph for a named pathway from one or more medical/biology review
PDFs. Writes two artefacts:

- `<pathway-slug>_reactions.csv` — columns: Title, Input, Output, Catalyst,
  Regulators, Reviews, Source1–Source5
- `<pathway-slug>_references.html` — every cited primary reference as a link

Reviews holds pipe-delimited supplied-PDF basenames. Each Source cell holds exactly
one URL chosen by a PubMed → PMC → DOI → publisher ladder; any 6th or further sources
are dropped. Pre-curation draft, not a curated entry.

```
/extract-reactions
```

---

### `/admin-drive-readme`

Regenerates the Reactome Team Drive README as a richly formatted Google Doc. On every
run: clears the existing doc, walks the live Team Drive folder inventory via the Drive
API, and rewrites the doc with styled headings, linked folder tables, a contacts table,
and a live folder inventory tree.

Requires Python 3 and the Google API client libraries. Uses OAuth user credentials by
default — credentials are stored at `~/.config/reactome/` on each user's local machine
and are never committed to the repo. Supports `--dry-run` (preview, no write) and
`--depth N` (inventory depth, default 2).

```
/admin-drive-readme
/admin-drive-readme --dry-run
/admin-drive-readme --depth 3
```

---

### `/analysis-graphdb-setup`

One-time setup guide and quarterly update SOP for running a local Reactome Neo4j
database connected to Claude Desktop via MCP, plus the EBI OLS MCP server for live
ontology lookups. Covers Docker setup, `neo4j-mcp` binary installation, Claude Desktop
config, and the update script for each quarterly Reactome release.

**What you get once configured:**

- Query the Reactome graph in plain English — Claude translates to Cypher automatically
- Live ontology lookups (GO, HP, ChEBI, EFO, 300+ ontologies) without hallucinated accessions

**Requirements:** Claude Desktop (Pro plan), Docker Desktop, Node.js, `neo4j-mcp` binary,
`uv` Python package manager.

See the skill for the full step-by-step install, Claude Desktop config file, troubleshooting
table, and example queries.

This skill is a one-time setup guide, not a command you invoke during curation — follow it
once, then use Claude Desktop directly for all Neo4j and OLS queries thereafter.

---

### `/release-qa-tracker`

Runs `compare_dirs.sh` against two QA output directories (old version vs. new
slice), filters out developer-only and backlog sections using a curator-vetted
skip list, presents a per-category intermediate review for approval, and produces
a polished multi-sheet `.xlsx` curator tracker with Status dropdowns
(`Not Done` / `Fixed` / `Skipped`), color-coded fill, and a Comments column on
every data row.

Can also start from an existing comparison file — supply a Google Sheets URL or
an uploaded `.xlsx` / `.csv` instead of running the script.

**Workflow:**

1. Provide `OLD_DIR` and `NEW_DIR` — version labels are taken from the directory
   basenames. Handles directory alias mapping (`command-line-runner` →
   `commandlinerunner`, `diagram-converter` → `diagram-qa`).
2. `compare_dirs.sh` (included in the skill directory) runs once per QA tool
   subdirectory; output is captured to `/tmp/<tool>_comparison.txt`.
3. **Intermediate review** — the skill pauses and presents a summary of included
   vs. skipped files per tool category and waits for curator confirmation before
   building the workbook.
4. Skip rules remove developer-only files and backlogs. Curator-actionable files
   retained by default: `Mandatory_Attributes`, `DT701-ReactionParticipantsMismatch`,
   `GT037-LiteratureReferenceRelationshipDuplication`,
   `GT090-CatalystActivityCompartmentDoesNotMatchReactionCompartment`,
   `Entities_With_CoV_Species_Without_Corresponding_Disease`,
   `ReactionlikeEvent_Regulations_Not_Reviewed`, `Review_Status`.
5. Output: `<NewVersion>_QA_Curator_Tracker.xlsx` — one sheet per tool group
   plus an Overview with a status legend and sheet directory.

```
/release-qa-tracker
```

---

### `/curation-build-illustration`

Builds or extends a biological pathway illustration in Reactome's **EHLD**
(Enhanced High-Level Diagram) style. The **preferred, primary mode is modifying
an existing published Reactome EHLD** (**Mode A**) — fetching that EHLD by ST_ID
(`reactome_icons.py fetch-ehld`) and adding newly described elements to it,
preserving the original verbatim and writing a new `<ST_ID>_modified.svg` (never
overwriting the published diagram). It can also build a **new** EHLD from scratch
from a written description (**Mode B**) or an example image / sketch (**Mode C**)
when there is no suitable EHLD to extend. In Mode A the skill first fetches the
EHLD, describes its biology back to the curator for confirmation, then asks what
to add and where. Every biological image part — proteins, complexes, small
molecules, cells, organelles, receptors, ion channels, tissues — is an actual
icon from the **Reactome Icon Library**. The skill never hand-draws or invents an
entity; anything the library does not cover is surfaced as a **gap**, not filled.

Icons are resolved two ways, deterministic-first:

- **`map` (preferred) — deterministic accession → icon.** If you have an
  accession (UniProt, ChEBI, GO, CL, UBERON, Complex Portal, …), the skill maps
  it straight to the exact icon via bundled offline tables (~2,300 mappings). No
  network, no fuzzy matching, no name-guessing — the most accurate,
  hallucination-proof path, and curators usually have these ids already.
- **`search` (fallback) — name-based** via live ContentService, when no
  accession is available.

The skill follows the **official Reactome specs**, which are bundled in the skill
directory and treated as authoritative: `EHLD_Specs_and_Guidelines.pdf` (canvas,
active regions, labels, mandatory `ANALINFO` boxes, text/colour rules, no
full-canvas background, export settings) and `Icon_Library_Guidelines.pdf` (the
seven icon categories). Layout, compartment placement, and membrane/transport
conventions distilled from the 217-diagram production EHLD corpus are captured in
`EHLD_layout_reference.md`.

**Per-request project directory.** The skill asks for (and creates) one
directory per illustration request. Drop your sample / reference images there;
all outputs are written back to the same directory, so each figure's inputs and
outputs stay together. Suggested layout: `illustrations/<slug>/`.

**Workflow:**

1. Interpret the spec (Mode B description and/or Mode C image, or the additions
   for a Mode A base EHLD); identify
   compartments, subpathways, entities (with their compartments), and flow.
2. Resolve an icon per entity/compartment — `map` by accession first, `search`
   by name otherwise — and present an **Icon Map** table for approval, including
   an **Accession (DB)** column, a **Gaps** list, and a layout sketch. **STOP**
   for curator approval (this is where icon-mismatch risk lives).
3. After approval: fetch approved icons, compose one EHLD SVG (1366×768 authoring
   artboard) — compartments as library icons, entities placed inside their
   compartment, membrane proteins straddling the bilayer, subpathway
   `REGION-`/`OVERLAY-` active regions, mandatory `ANALINFO` boxes, and Arial-Bold
   `#0F82BC` pathway labels — per the official EHLD specification.

**Outputs** (all in the request's project directory):

- `<ST_ID-or-slug>.svg` — the composed EHLD illustration
- `<slug>_icon_manifest.csv` — per-icon provenance (accession/DB + CC-BY 4.0
  attribution)
- `<slug>_gaps.md` — entities with no library icon (candidate Icon Library
  contributions)
- `icons/` — the downloaded source SVGs

The Reactome Icon Library is **CC-BY 4.0**; the manifest captures per-icon
designer, curator, and ORCID for the required credit line. The SVG is a
structured, attributed draft for hand-tuning in Adobe Illustrator (export with
Styling = Internal CSS, Font = SVG, Object IDs = Layer Names to preserve the
region ids); real subpathway ST_IDs and validation against the live hierarchy are
required before Pathway Browser ingestion.

```
/curation-build-illustration
```

---

## Prerequisites by Skill

| Skill | Requirements |
|---|---|
| `/review-internal` | Internet access; pathway report DOCX and Curator Guide PDF uploaded to conversation |
| `/annotate-pathway-from-reviews-or-topic_name` | claude.ai Pro/Team/Enterprise (Projects) or Claude API; PubMed and PMC MCP servers recommended; internet access for Mode B |
| `/release-doi-batch` | DOIs.xlsx from Team Drive; Python 3 with `pandas` and `openpyxl` |
| `/extract-reactions` | One or more review-article PDFs (absolute paths); internet access to `eutils.ncbi.nlm.nih.gov` |
| `/admin-drive-readme` | Python 3; `pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client`; OAuth credentials at `~/.config/reactome/credentials.json` |
| `/release-qa-tracker` | `compare_dirs.sh` (in skill directory); Python 3 with `openpyxl`; two QA output directories (or an existing comparison file) |
| `/analysis-graphdb-setup` | Claude Desktop (Pro plan); Docker Desktop; Node.js; `neo4j-mcp` binary (github.com/neo4j/mcp/releases); `uv` Python package manager |
| `/curation-build-illustration` | Python 3 (stdlib only); network access to `reactome.org` for name `search`, icon + EHLD download (accession `map` lookup works offline from bundled tables); a project directory for the request (a base-EHLD ST_ID for Mode A; a sample image for Mode C) |

> **Note on `/extract-reactions` and NCBI access:** In Claude Code, `.claude/settings.json`
> allowlists `eutils.ncbi.nlm.nih.gov` automatically. In claude.ai (browser), add it manually
> via **Settings → Capabilities → Domain allowlist**. Without it, PMID resolution falls through
> to DOI URLs or blanks — PMIDs are never recovered from training data.

> **Note on `/curation-build-illustration` and Reactome access:** In Claude Code,
> `.claude/settings.json` allowlists `reactome.org` automatically. In claude.ai (browser),
> add it manually via **Settings → Capabilities → Domain allowlist**. Without it, icon search
> and download will fail — icons are never fabricated from training data.

---

## Chrome Extensions

### `AICurator`

Install from https://chromewebstore.google.com/detail/aicurator/jkdcmghlpgfilhdlngmopljpocpbnhdc

Go to a fresh Google Sheet then open the extension:

1. **Main** — pick or create a project (a folder under
   `<Downloads>/aicurator/`) bound to a Google Sheet, configure the AI
   provider, manage settings.
2. **Extract** — feed review-article PDFs and a pathway name to an LLM,
   resolve PMIDs against PubMed, write a 12-column reaction table to the
   sheet.
3. **Summate** — for each row, send the cited PMID-prefixed PDFs and the
   row context to an LLM, draft a Reactome-style summation paragraph,
   write it to column B.
4. **Canonize** — replace protein/gene mentions in columns A–F with their
   canonical UniProt-confirmed (human-only, reviewed-first) gene symbols.


---

## Using Skills in the claude.ai Desktop App

1. Locate your skill folder: `.claude/skills/<skill-name>/`
2. ZIP it: `zip -r skill-name.zip skill-name/`
3. Go to **Customize → Skills → Upload ZIP** in the Desktop app

---

## Contributing a Skill

1. Create a directory under `.claude/skills/` named for your skill
2. Add `SKILL.md` with YAML frontmatter (`name`, `description`) and instructions
3. Add any supporting files (templates, scripts, reference docs)
4. Test it locally with Claude Code
5. Open a PR with a brief description of what the skill does and when to use it

For detailed instructions on writing and committing a new skill, see the full guide
(`Reactome_CuratorWorkflows_ClaudeCode_Guide.docx`).

Suggestions for improving `annotate-pathway-from-reviews-or-topic_name` — including
changes to the system prompt or the RLE annotation reference file — are welcome via
GitHub Issues. When proposing changes to the reference file, cite the specific section
of the Curator Guide or Data Model Glossary that supports the change, and note the
guide version.

---

## Repository Structure

```
reactome-curator-workflows/
├── CLAUDE.md                                              ← project context for Claude Code
├── README.md                                              ← this file
├── Reactome_CuratorWorkflows_ClaudeCode_Guide.docx       ← full setup guide
├── .gitignore
└── .claude/
    ├── settings.json                                      ← Claude Code host allowlist
    └── skills/
        ├── review-internal/
        │   ├── SKILL.md
        │   ├── Reactome_InternalReview_PROMPT_v1_4.docx
        │   ├── Reactome_InternalReview_TEMPLATE.docx
        │   ├── Claude_ReactomeDataModelGlossary_V95_Final.docx.pdf
        │   ├── Curator_Guide_V94.pdf
        │   ├── EWAS_name_rules.docx                       ← EWAS naming rules (Section 7)
        │   ├── Rules_for_automatic_reaction_typing.docx   ← reaction/event naming rules (Section 7)
        │   ├── bau060.pdf                                 ← Jupe et al. 2014 CV paper (Section 7)
        │   ├── ptm_lookup.xlsx                            ← PSI-MOD → PTM prefix table (source)
        │   ├── ptm_prefixes.md                            ← PTM prefix table, plain text (auto-loaded)
        │   └── Small_molecule_renaming.xlsx               ← canonical small molecule names (Section 7)
        ├── annotate-pathway-from-reviews-or-topic_name/
        │   ├── SKILL.md
        │   ├── README.md
        │   └── Reactome_RLE_Annotation_Reference_V94.md
        ├── extract-reactions/
        │   └── SKILL.md
        ├── release-doi-batch/
        │   ├── SKILL.md
        │   └── generate_crossref_xml.py
        ├── admin-drive-readme/
        │   ├── SKILL.md
        │   └── update_drive_readme.py
        ├── release-qa-tracker/
        │   ├── SKILL.md
        │   └── compare_dirs.sh
        ├── analysis-graphdb-setup/
        │   ├── SKILL.md                                   ← /analysis-graphdb-setup
        │   └── update_reactome.sh                         ← quarterly DB update script
        └── curation-build-illustration/
            ├── SKILL.md                                   ← /curation-build-illustration
            ├── EHLD_Specs_and_Guidelines.pdf              ← official Reactome EHLD spec (authoritative)
            ├── Icon_Library_Guidelines.pdf                ← official Reactome Icon Library spec (authoritative)
            ├── EHLD_layout_reference.md                   ← layout/compartment/membrane conventions (from the production EHLD corpus)
            ├── icon_mappings/                             ← accession→icon tables (<DB>2Icon.txt) powering deterministic `map` lookup
            └── reactome_icons.py                          ← Icon Library helper: map (accession→icon), search, fetch
```

> Generated illustration outputs live under `illustrations/<slug>/` (one directory
> per request, holding sample images, the composed SVG, manifest, gaps file, and
> downloaded icons). That directory is git-ignored — outputs are never committed.

---

## Contact

Repo maintainer: Marc Gillespie (SJU)
For curation standards questions: consult Curator Guide V94
For repo/skill questions: open a GitHub issue
