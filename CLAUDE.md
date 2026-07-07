# Reactome Curator Workflows

## What This Repository Is

Shared Claude Code workflow skills for Reactome curation and release operations.
Skills are markdown instruction files Claude Code reads directly — any curator with
Claude Code can clone this repo and run any skill. No build process, no dependencies
beyond Claude Code itself (plus Python 3 for a few skills).

Skills are added incrementally as we vet repeatable workflows. This repo is
curator-driven; if you develop a workflow worth sharing, open a PR.

> **How to read this file.** CLAUDE.md is the orientation index — what the repo is,
> how it's laid out, and a short pointer to each skill. Full instructions for a skill
> live in its own `SKILL.md` (and companion files), which Claude Code loads when the
> skill runs. Don't duplicate skill internals here; link to them.

---

## Repository Structure

```
reactome-curator-workflows/
├── CLAUDE.md                      ← you are here (orientation index)
├── README.md                      ← setup instructions for new users
├── Reactome_CuratorWorkflows_ClaudeCode_Guide.docx   ← full onboarding guide
├── chrome-extensions/pmid-tagger/ ← Chrome extension (see Chrome Extensions)
└── .claude/
    ├── settings.json              ← Claude Code host/network allowlist
    └── skills/
        ├── review-internal/                     ← /review-internal
        ├── annotate-pathway-from-reviews-or-topic_name/← /annotate-pathway-from-reviews-or-topic_name
        ├── extract-reactions/                          ← /extract-reactions
        ├── release-doi-batch/                         ← /release-doi-batch
        ├── admin-drive-readme/                       ← /admin-drive-readme
        ├── release-qa-tracker/                        ← /release-qa-tracker
        ├── analysis-graphdb-setup/                   ← /analysis-graphdb-setup
        └── curation-build-illustration/                ← /curation-build-illustration
```

Each skill directory holds its own `SKILL.md` plus any scripts, templates, and
reference documents it needs (PDFs, lookup tables, helpers). Open a skill's
directory to see its bundled materials.

---

## The Reactome Curation Context

Reactome is a free, open-source, peer-reviewed pathway database. Human pathways are
manually curated and computationally inferred across ~15 other species; researchers
use it for pathway analysis, drug-target identification, and systems biology.
Institutional homes: OICR (Toronto), EMBL-EBI (Hinxton), NYU Grossman (New York),
St. John's University (New York).

Key public resources:
- Website / GitHub: https://reactome.org · https://github.com/reactome
- Pathway Browser: https://reactome.org/PathwayBrowser/
- ContentService (REST API): https://reactome.org/ContentService/
- OLS4 (ontology term lookup): https://www.ebi.ac.uk/ols4/

---

## Curation Model

Reactome curates human biology at the **reaction** level. Each reaction encodes its
input/output PhysicalEntities (proteins, complexes, small molecules, DNA/RNA),
catalyst activity (GO molecular function + catalytic entity), regulation, literature
references (PubMed IDs), and species (human by default; inferred for others).
Reactions group into Pathways and higher-level Pathways. Every curated entity has a
stable DB_ID and a human-readable ST_ID (e.g. `R-HSA-XXXXXXX`).

Authoritative standards (copies bundled in `review-internal/`):
- **Curator Guide V94** — naming, complex/set representation, evidence codes,
  cross-reference standards (UniProt, ChEBI, NCBI Gene, Ensembl, GO), disease
  pathway structure, orthology inference. → `Curator_Guide_V94.pdf`
- **Data Model Glossary V95** — data model terms, entity types, relationship
  semantics. → `Claude_ReactomeDataModelGlossary_V95_Final.docx.pdf`

---

## Release Cycle

Reactome releases ~3–4 times per year: curation of new/updated pathways → internal
peer review (`/review-internal`) → DOI assignment via CrossRef batch XML,
schema 5.3.1 (`/release-doi-batch`) → species inference → export and QC → public
release. **DOIs.xlsx** (in the Team Drive, not this repo) tracks DOIs per release
with curator/reviewer assignments; `/release-doi-batch` reads it from a local path.

---

## Available Skills

One-line orientation per skill; see each skill's `SKILL.md` for full instructions,
inputs, and options.

- **`/review-internal`** — Formal structured review of a pathway report
  against Curator Guide V94; outputs a prioritized seven-section review DOCX.
  Requires the report DOCX + Curator Guide PDF in the conversation. Modifiers:
  `disease`, `drug`, `large` (50+ reactions).

- **`/annotate-pathway-from-reviews-or-topic_name`** — AI-assisted pre-curation
  (v1.4). From a topic (Mode B) or supplied references/PMIDs/DOIs/PDFs (Mode A),
  proposes a full pathway → subpathway → reaction hierarchy and verifies primary
  literature via a mandatory ten-step PMID protocol, applying the species/chimeric
  framework. Does **not** touch the database or resolve ontology/UniProt IDs (those
  are flagged PENDING CURATOR VERIFICATION). Needs claude.ai Projects or the API;
  PubMed + PMC MCP servers recommended.

- **`/extract-reactions`** — Extracts a reaction graph for a named pathway from
  review PDFs; writes a reactions CSV (inputs/outputs/catalysts/regulators + a
  PubMed>PMC>DOI>publisher source ladder) and an HTML reference list. PMID
  resolution via NCBI E-utilities (`eutils.ncbi.nlm.nih.gov`); never from training
  data. Pre-curation draft.

- **`/release-doi-batch`** — Runs `generate_crossref_xml.py` to produce a CrossRef
  DOI batch XML for a release. Requires DOIs.xlsx locally and Python 3 + pandas.

- **`/admin-drive-readme`** — Regenerates the Team Drive README as a formatted
  Google Doc from the live folder inventory. Python 3 + Google API client libraries;
  OAuth credentials at `~/.config/reactome/`. Supports `--dry-run`, `--depth N`.

- **`/release-qa-tracker`** — Turns QA comparison output (via `compare_dirs.sh`, or
  an existing Sheets/xlsx/csv) into a multi-sheet curator tracker workbook with
  per-row Status dropdowns and Comments, after a curator-approval review gate.
  Needs Python 3 + `openpyxl`.

- **`/analysis-graphdb-setup`** — One-time setup guide + quarterly update SOP for a
  local Reactome Neo4j database connected to Claude Desktop via `neo4j-mcp`, plus the
  EBI OLS MCP server for ontology lookups. A setup guide, not a curation command.

- **`/curation-build-illustration`** — Builds an EHLD-style pathway illustration
  (1366×768 SVG) from a description (Mode A) or example image (Mode B). All art comes
  from the Reactome Icon Library — never hand-drawn or invented; icons resolved
  deterministically by accession (bundled `icon_mappings/` + the helper's `map`)
  first, live name `search` otherwise. Follows the bundled official Reactome specs
  (`EHLD_Specs_and_Guidelines.pdf`, `Icon_Library_Guidelines.pdf`). Needs Python 3
  and network access to `reactome.org` (name search + download; `map` is offline).

---

## Chrome Extensions

**`pmid-tagger`** (`chrome-extensions/pmid-tagger/`) — Prefixes PDF downloads with
`PMID-<id>_` when started from a PubMed/PMC article page, keeping downloaded papers
matched to their references. Install: `chrome://extensions/` → enable Developer mode
→ Load unpacked → select the extension folder. Active immediately, no config.

---

## Claude Code Configuration

`.claude/settings.json` holds the host/network allowlist Claude Code reads on launch
from the repo root. It allowlists `eutils.ncbi.nlm.nih.gov` (for `/extract-reactions`)
and `reactome.org` (for `/curation-build-illustration`).

> **claude.ai (browser) users:** the allowlist file does not apply — add those hosts
> manually via **Settings → Capabilities → Domain allowlist**, or PMID resolution and
> icon search/download will fail (values are never fabricated from training data).

---

## Team

Marc Gillespie (SJU, repo maintainer) · Lisa Matthews (NYU) · Joel Weiser
(OICR) · Guanming Wu (OHSU) · Adam Wright (OICR).

Curation-standards questions: consult Curator Guide V94.
Repo/skill questions: open a GitHub issue.

---

## Adding a New Skill

1. Create a directory under `.claude/skills/` named for your skill.
2. Add `SKILL.md` with YAML frontmatter (`name`, `description`) and step-by-step
   instructions.
3. Add any supporting files the skill references (scripts, templates, reference docs).
4. Open a PR describing what the skill does and when to use it.

Keep skills focused on a single repeatable workflow, and keep their full
documentation in the skill directory — this file only needs a one-line pointer.
See existing `SKILL.md` files for the expected format and level of detail.

---

## What This Repo Is Not

- Not a replacement for the Curator Guide (canonical version in the Team Drive).
- Not a place for raw data files (DOIs.xlsx, release databases, pathway reports).
- Not a code repository — production scripts belong in the appropriate `reactome/*`
  repos. Scripts here are workflow helpers used directly by curators via Claude Code.
