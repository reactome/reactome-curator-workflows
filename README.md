# reactome-curator-workflows

Shared Claude Code workflow skills for Reactome curation and release operations.

## What This Is

This repository contains Claude Code skills — markdown-based instruction files that Claude Code reads directly. Any curator with Claude Code installed can clone this repo and immediately run any skill. No build process, no configuration beyond cloning.

Skills are added incrementally as we identify and vet repeatable workflows. See CLAUDE.md for full project context.

## Documentation

Full setup and usage instructions are in:

**[Reactome_CuratorWorkflows_ClaudeCode_Guide_v1_2.docx](./Reactome_CuratorWorkflows_ClaudeCode_Guide_v1_2.docx)**

This covers one-time prerequisites, cloning the repository, running each skill, and how to add new skills. Start here if you are setting up for the first time.

## Setup (Quick Reference)

### 1. Prerequisites (one-time)

Install Git: https://git-scm.com/downloads

Install Node.js (LTS): https://nodejs.org

Install Claude Code:

```bash
mkdir -p ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.zshrc
source ~/.zshrc
npm install -g @anthropic-ai/claude-code
```

Set your Anthropic API key (add to ~/.zshrc):

```bash
export ANTHROPIC_API_KEY=your-key-here
```

Install Python dependencies (use pip3 on macOS):

```bash
pip3 install pandas openpyxl
```

If you see a PATH warning after installing, add this to ~/.zshrc
(replace 3.9 with the version number shown in your warning):

```bash
export PATH="/Users/[you]/Library/Python/3.9/bin:$PATH"
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

Claude Code automatically reads CLAUDE.md and loads all skills at session start.

### 4. Keep up to date

```bash
cd ~/Developer/reactome-curator-workflows
git pull
```

## Available Skills

**`/curation-review`**

Formal structured internal review of a Reactome pathway report against Curator Guide V94 standards. Produces a prioritized review DOCX with seven sections. Upload the pathway report DOCX and Curator Guide PDF to the conversation before invoking. Optional modifiers: `disease`, `drug`, `large`.

```
/curation-review "HHV8 Infection" R-HSA-9521541 "Lisa Matthews" 2026-04-15
```

**`/generate-doi-batch`**

Generates a CrossRef DOI batch XML file for a release using DOIs.xlsx. Requires DOIs.xlsx locally (from Team Drive) and Python 3 + pandas.

```
/generate-doi-batch V94
```

**`/extract-reactions`**

Extracts a reaction graph for a named pathway from one or more medical/biology review PDFs. Writes two artefacts: `<pathway-slug>_reactions.csv` with columns Title, Input, Output, Catalyst, Regulators, Reviews, Source1, Source2, Source3, Source4, Source5; and a companion `<pathway-slug>_references.html` listing every cited primary reference as a link. Reviews holds pipe-delimited supplied-PDF basenames. Each Source cell holds exactly one URL chosen by a PubMed → PMC → DOI → publisher ladder; one source per cell, any 6th or further sources dropped. Text labels with mandatory compartments; inserts transport reactions on compartment changes; emits reversible reactions as forward+reverse rows. Connectivity is not required — gaps are flagged with parenthesized entries and parallel branches get `##` subtitle rows. Uses one batched call to NCBI idconv to resolve DOIs to PMIDs; otherwise offline. Pre-curation draft, not a curated entry. The skill will prompt for the pathway name and the PDF paths.

```
/extract-reactions
```

## Prerequisites by Skill

| Skill | Requirements |
|---|---|
| curation-review | Active internet connection; pathway report DOCX and Curator Guide PDF uploaded to conversation |
| generate-doi-batch | DOIs.xlsx from Team Drive; Python 3 with pandas and openpyxl (`pip3 install pandas openpyxl`) |
| extract-reactions | One or more review-article PDFs available locally (absolute paths); internet access to `eutils.ncbi.nlm.nih.gov` for NCBI E-utilities PMID resolution: a batched ESearch + ESummary pair for DOI-bearing refs and a per-ref title+author ESearch fallback (strict single-match only) for refs with no DOI. On Claude Code the `.claude/settings.json` in this repo allowlists the host. On claude.ai (browser), add `eutils.ncbi.nlm.nih.gov` to **Settings → Capabilities → Domain allowlist**, otherwise the calls fail and refs fall through the ladder to DOI URLs or blanks (PMIDs are *never* recovered from training data) |

## Contributing a Skill

1. Create a directory under `.claude/skills/` named for your skill
2. Add `SKILL.md` with YAML frontmatter (name, description) and instructions
3. Add any supporting files (templates, scripts, reference docs)
4. Test it locally with Claude Code
5. Open a PR with a brief description of what the skill does and when to use it

See the full guide for detailed instructions on writing and committing a new skill.

## Using skills in Desktop browser (claude.ai)

1. Take your `~/.claude/skills/skill-name/` folder
2. ZIP it up: `zip -r skill-name.zip skill-name/`
3. Go to **Customize > Skills > Upload ZIP** in the Desktop app

## Repository Structure

```
README.md                                             ← this file
CLAUDE.md                                             ← project context for Claude Code
Reactome_CuratorWorkflows_ClaudeCode_Guide_v1_2.docx  ← full setup guide
.gitignore
.claude/
└── skills/
   ├── curation-review/
   │   ├── SKILL.md
   │   ├── Reactome_InternalReview_PROMPT_v1_4.docx
   │   ├── Reactome_InternalReview_TEMPLATE.docx
   │   └── Curator_Guide_V94.pdf
   ├── extract-reactions/
   │   └── SKILL.md
   └── generate-doi-batch/
       ├── SKILL.md
       └── generate_crossref_xml.py
```

## Contact

Repo maintainer: Marc Gillespie (NYU / SJU)
For curation standards questions: Reactome curator Slack channel
