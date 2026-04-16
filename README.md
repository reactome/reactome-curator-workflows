# reactome-curator-workflows

Shared Claude Code workflow skills for Reactome curation and release operations.

## What This Is

This repository contains Claude Code skills — markdown-based instruction files that Claude Code reads directly. Any curator with Claude Code installed can clone this repo and immediately run any skill. No build process, no configuration beyond cloning.

Skills are added incrementally as we identify and vet repeatable workflows. See CLAUDE.md for full project context.

## Setup

### 1. Install Claude Code

Claude Code requires Node.js 18 or higher.

 npm install -g @anthropic-ai/claude-code

You will need an Anthropic account and API key. Set your key:

 export ANTHROPIC_API_KEY=your-key-here

For persistent setup, add the export line to your ~/.bashrc or ~/.zshrc.

### 2. Clone This Repository

 git clone https://github.com/reactome/reactome-curator-workflows.git
 cd reactome-curator-workflows

### 3. Run Claude Code

 claude

Claude Code automatically reads CLAUDE.md and loads all skills in .claude/skills/ at session start. No additional configuration needed.

## Available Skills

 /curation-review [DB_ID or ST_ID]
 Structured internal review of a Reactome pathway or reaction against
 Curator Guide V94 standards. Produces a prioritized markdown report.
 Example: /curation-review 9985686

 /generate-doi-batch [release version]
 Builds a CrossRef DOI batch XML file for a release using DOIs.xlsx.
 Validates against CrossRef schema 5.3.1 before writing output.
 Example: /generate-doi-batch 89

## Prerequisites by Skill

 curation-review
 - Active internet connection (queries Reactome ContentService API)

 generate-doi-batch
 - DOIs.xlsx downloaded locally from the Reactome Team Drive
 - Python 3 with openpyxl: pip install openpyxl

## Keeping Skills Up to Date

 cd reactome-curator-workflows
 git pull

New or updated skills are immediately available after pulling — no restart needed if Claude Code is already running.

## Contributing a Skill

1. Create a directory under .claude/skills/ named for your skill
2. Add SKILL.md with YAML frontmatter (name, description) and step-by-step instructions
3. Add any supporting files (templates, reference XML, scripts) the skill references
4. Open a PR with a brief description of what the skill does and when to use it

See an existing SKILL.md for the expected format.

## Contact

Repo maintainer: Marc Gillespie (NYU / SJU)
For curation standards questions: Reactome curator Slack channel