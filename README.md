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

**[Reactome_CuratorWorkflows_ClaudeCode_Guide_v1_3.docx](./Reactome_CuratorWorkflows_ClaudeCode_Guide_v1_3.docx)**

This covers one-time prerequisites, cloning the repository, running each skill, and
how to add new skills. Start here if you are setting up for the first time.

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

### `/internal-module-review`

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
/internal-module-review "HHV8 Infection" R-HSA-9521541 "Lisa Matthews" 2026-04-15
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

### `/generate-doi-batch`

Generates a CrossRef DOI batch XML file for a release using DOIs.xlsx. Requires
DOIs.xlsx locally (from Team Drive) and Python 3 + pandas.

```
/generate-doi-batch V94
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

## Prerequisites by Skill

| Skill | Requirements |
|---|---|
| `/internal-module-review` | Internet access; pathway report DOCX and Curator Guide PDF uploaded to conversation |
| `/annotate-pathway-from-reviews-or-topic_name` | claude.ai Pro/Team/Enterprise (Projects) or Claude API; PubMed and PMC MCP servers recommended; internet access for Mode B |
| `/generate-doi-batch` | DOIs.xlsx from Team Drive; Python 3 with `pandas` and `openpyxl` |
| `/extract-reactions` | One or more review-article PDFs (absolute paths); internet access to `eutils.ncbi.nlm.nih.gov` |

> **Note on `/extract-reactions` and NCBI access:** In Claude Code, `.claude/settings.json`
> allowlists `eutils.ncbi.nlm.nih.gov` automatically. In claude.ai (browser), add it manually
> via **Settings → Capabilities → Domain allowlist**. Without it, PMID resolution falls through
> to DOI URLs or blanks — PMIDs are never recovered from training data.

---

## Chrome Extensions

### `AICurator`

See https://github.com/rwst/aicurator

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
(`Reactome_CuratorWorkflows_ClaudeCode_Guide_v1_3.docx`).

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
├── Reactome_CuratorWorkflows_ClaudeCode_Guide_v1_3.docx  ← full setup guide
├── .gitignore
├── chrome-extensions/
│   └── pmid-tagger/                                      ← Chrome extension: PMID-prefix PDF downloads
│       ├── manifest.json
│       ├── background.js
│       └── content.js
└── .claude/
    ├── settings.json                                      ← Claude Code host allowlist
    └── skills/
        ├── internal-module-review/
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
        └── generate-doi-batch/
            ├── SKILL.md
            └── generate_crossref_xml.py
```

---

## Contact

Repo maintainer: Marc Gillespie (NYU / SJU) — gillespm@stjohns.edu
For curation standards questions: Reactome curator Slack channel
For repo/skill questions: open a GitHub issue
