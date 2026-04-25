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

 CLAUDE.md                                    <- you are here
 README.md                                    <- setup instructions for new users
 .claude/
 └── skills/
     ├── curation-review/
     │   ├── SKILL.md                         <- /curation-review
     │   ├── Reactome_InternalReview_PROMPT_v1_4.docx   <- source prompt spec
     │   ├── Reactome_InternalReview_TEMPLATE.docx      <- companion output template
     │   └── Curator_Guide_V94.pdf            <- authoritative curation standard
     ├── extract-reactions/
     │   └── SKILL.md                         <- /extract-reactions
     └── generate-doi-batch/
         ├── SKILL.md                         <- /generate-doi-batch
         └── generate_crossref_xml.py         <- DOI batch XML generator script

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
A copy is in .claude/skills/curation-review/Curator_Guide_V94.pdf.

---

## Release Cycle

Reactome releases approximately 3-4 times per year. Each release involves:
- Curation of new pathways and updates to existing ones
- Internal peer review of new content (using /curation-review)
- DOI assignment via CrossRef batch XML submission, schema 5.3.1
 (using /generate-doi-batch)
- Species inference pipeline
- Data export and QC
- Public release and announcement

**DOIs.xlsx** (maintained in the Reactome Team Drive, not in this repo) tracks
DOIs across release versions with curator and reviewer assignments.
The generate-doi-batch skill reads it from a local path specified at runtime.

---

## Available Skills

 /curation-review
 Formal structured internal review of a Reactome pathway report against
 Curator Guide V94 standards. Produces a prioritized review DOCX with
 seven sections. Requires the pathway report DOCX and Curator Guide PDF
 to be uploaded to the conversation before invoking.
 Supports optional modifiers: disease, drug, large (50+ reactions).

 /generate-doi-batch
 Runs generate_crossref_xml.py to produce a CrossRef DOI batch XML file
 for a release version. Requires DOIs.xlsx locally and Python 3 + pandas.
 Handles input validation, error interpretation, and post-run checklist.

 /extract-reactions
 Extracts a reaction graph for a named pathway from one or more medical/biology
 review PDFs and writes it to <pathway-slug>_reactions.csv (Title, Input,
 Output, Catalyst, Regulators, Source). Text labels with mandatory compartments;
 inserts transport reactions on compartment changes; emits reversible reactions
 as forward+reverse rows. Connectivity is not required — gaps are flagged with
 parenthesized entries and parallel branches get ## subtitle rows. Pre-curation
 draft, not a curated entry.

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

1. Create a directory under .claude/skills/ named for your skill
2. Add SKILL.md with YAML frontmatter (name, description) and step-by-step instructions
3. Add any supporting files the skill references (scripts, templates, reference docs)
4. Open a PR with a brief description of what the skill does and when to use it

Keep skills focused on a single repeatable workflow. See existing SKILL.md files
for the expected format and level of detail.

---

## What This Repo Is Not

- Not a replacement for the Curator Guide (canonical version in Team Drive)
- Not a place for raw data files (DOIs.xlsx, release databases, pathway reports)
- Not a code repository — production scripts belong in the appropriate reactome/* repos.
 Scripts here are workflow helpers used directly by curators via Claude Code.
