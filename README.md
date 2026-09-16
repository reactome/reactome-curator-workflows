# reactome-curator-workflows

Shared Claude Code workflow skills for Reactome curation and release operations.

## What This Is

[Reactome](https://reactome.org) is a free, open-source, peer-reviewed pathway
database. Human pathways are manually curated at the **reaction** level and
computationally inferred across ~15 other species.

This repository holds the Claude Code **skills** curators use for that work —
markdown instruction files that Claude Code reads directly. Any curator with Claude
Code installed can clone this repo and run any skill. There is no build step and no
dependency beyond Claude Code itself, plus Python 3 for a few skills.

Skills are added incrementally as we vet repeatable workflows. Each skill's full
instructions live in its own `.claude/skills/<name>/SKILL.md`, which is the
authoritative source for how that skill behaves; this file covers what each one is
for and what you need to run it. See `CLAUDE.md` for repo conventions and how to
add a skill.

---

## Setup

### 1. Prerequisites

- macOS Ventura (13) or later, or Linux.
- **Git.** Check with `git --version`. On macOS, if it is missing, run
  `xcode-select --install` and click **Install**.
- **An Anthropic API key from the Reactome organization.** Contact the repo
  maintainer to be added, then create your own key at **console.anthropic.com →
  API Keys → Create Key**. Copy it immediately — it is shown only once.
- **Repository access.** The maintainer must add you as a collaborator; accept the
  emailed invitation before cloning.
- Node.js is **not** needed for the base install — only for
  `/analysis-graphdb-setup`.

Install Claude Code:

```bash
curl -fsSL https://claude.ai/install.sh | bash
claude --version
```

### 2. Set your API key

```bash
echo 'export ANTHROPIC_API_KEY="your-key-here"' >> ~/.zshrc
source ~/.zshrc
echo $ANTHROPIC_API_KEY        # should print your key
```

Use the **organizational** key for Reactome work so usage bills to the shared
Reactome credit pool; a personal Claude.ai subscription is separate and
unaffected. When `ANTHROPIC_API_KEY` is set, Claude Code prefers it automatically —
run `/status` inside a session to confirm which credentials are active.

Your key lives only in `~/.zshrc` on your own machine. **Never** commit it, paste it
into a skill or script, or share it in chat or email. If a key is ever exposed,
revoke and rotate it immediately — exposure is the trigger, not misuse.

### 3. Clone the repository

```bash
git clone https://github.com/reactome/reactome-curator-workflows.git \
    ~/Developer/reactome-curator-workflows
cd ~/Developer/reactome-curator-workflows
```

If Git prompts for a password, use a [personal access
token](https://github.com/settings/tokens) with the `repo` scope — not your GitHub
account password.

### 4. Install Python dependencies

Several skills need Python 3 and a few packages. Versions are pinned in
`requirements.txt` so every curator gets the same set:

```bash
pip3 install --user -r requirements.txt
```

If pip reports `externally-managed-environment` (PEP 668), use a virtual environment
instead — see the notes at the top of `requirements.txt`. If pip prints a PATH
warning, add the directory it names to your shell config:

```bash
echo 'export PATH="$HOME/Library/Python/3.x/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### 5. Run Claude Code

```bash
cd ~/Developer/reactome-curator-workflows
claude
```

**Always launch from inside the repository folder.** Claude Code reads `CLAUDE.md`
and loads all skills from the directory you start it in, and `.claude/settings.json`
in the repo root is what allowlists the external hosts some skills need
(`eutils.ncbi.nlm.nih.gov`, `reactome.org`). Launched elsewhere, those skills fail.

The Claude for Mac desktop app's `</>` Claude Code button runs in an OAuth-only
context and does not read `ANTHROPIC_API_KEY` from your shell — launch from Terminal
for Reactome work.

### 6. Keep up to date

```bash
cd ~/Developer/reactome-curator-workflows
git pull
```

New and updated skills are available immediately — no restart needed if Claude Code
is already running.

---

## Available Skills

Invoke a skill by typing its name at the Claude Code prompt. Claude will prompt you
for anything it needs.

### `/review-internal`

Formal structured internal review of a pathway report against Curator Guide V94,
producing a prioritized seven-section review DOCX. Upload the pathway report DOCX and
the Curator Guide PDF to the conversation before invoking. Optional modifiers:
`disease`, `drug`, `large` (50+ reactions).

```
/review-internal "HHV8 Infection" R-HSA-9521541 "Lisa Matthews" 2026-04-15
```

### `/annotate-pathway-from-reviews-or-topic_name`

AI-assisted pre-curation. From supplied references (Mode A: PMIDs, DOIs, or PDFs) or
a biological topic (Mode B), proposes a complete pathway → subpathway → reaction
hierarchy and verifies primary literature via a mandatory ten-step PMID verification
protocol, applying the species/chimeric framework. Produces a first-pass draft for
curator review — it does not touch the database, and ontology/UniProt accessions are
left marked **PENDING CURATOR VERIFICATION**.

```
/annotate-pathway-from-reviews-or-topic_name
```

### `/extract-reactions`

Extracts a reaction graph for a named pathway from one or more review PDFs. Writes
`<pathway-slug>_reactions.csv` (Title, Input, Output, Catalyst, Regulators, Reviews,
Source1–Source5) plus `<pathway-slug>_references.html`. Each Source cell holds one URL
chosen by a PubMed → PMC → DOI → publisher ladder; PMIDs are resolved live against
NCBI E-utilities and never recovered from training data. Pre-curation draft.

```
/extract-reactions "Wnt Signaling Pathway"
```

### `/release-doi-batch`

Generates a CrossRef DOI batch XML file (schema 5.3.1) for a release from DOIs.xlsx.

```
/release-doi-batch V97
```

### `/release-qa-tracker`

Turns QA comparison output into a multi-sheet curator tracker workbook with per-row
Status dropdowns (`Not Done` / `Fixed` / `Skipped`) and a Comments column. Runs
`compare_dirs.sh` against two QA output directories, or starts from an existing Google
Sheets URL / `.xlsx` / `.csv`. Pauses for curator approval of the included-vs-skipped
file list before building the workbook.

```
/release-qa-tracker
```

### `/curation-build-illustration`

Builds or extends an EHLD-style pathway illustration (1366×768 SVG). The preferred
mode is **modifying an existing published EHLD** fetched by ST_ID (Mode A) — it
describes the base diagram back to you for confirmation, then adds new elements and
writes `<ST_ID>_modified.svg`, never overwriting the published diagram. It can also
build a new EHLD from a written description (Mode B) or an example image (Mode C).

Every biological image part comes from the **Reactome Icon Library** — nothing is
hand-drawn or invented, and anything the library does not cover is surfaced as a gap.
Icons resolve deterministically by accession where you have one (offline, from bundled
tables) and by live name search otherwise. The skill stops for approval of the icon
map before composing. Outputs go to a per-request project directory
(`illustrations/<slug>/`, git-ignored): the SVG, an icon manifest with CC-BY 4.0
attribution, a gaps file, and the downloaded icons.

```
/curation-build-illustration
```

### `/admin-drive-readme`

Regenerates the Reactome Team Drive README as a formatted Google Doc from the live
folder inventory. Supports `--dry-run` (preview, no write) and `--depth N` (inventory
depth, default 2).

```
/admin-drive-readme --dry-run
```

### `/spotlight-article-drafter`

Drafts a candidate Reactome "Research Spotlight" article from a paper that used
Reactome data or tools, producing both forms at once: the short one-paragraph homepage
teaser and the expanded long-form version. Drafts text only — final HTML/Joomla
formatting is a separate step, after a curator approves the wording and publish date.

```
/spotlight-article-drafter
```

### `/analysis-graphdb-setup`

A one-time setup guide and quarterly update SOP, not a command you invoke during
curation. Walks through running a local Reactome Neo4j database connected to Claude
Desktop via `neo4j-mcp`, plus the EBI OLS MCP server for ontology lookups. Once
configured, you query the Reactome graph in plain English and get live GO/HP/ChEBI/EFO
lookups instead of hallucinated accessions. Follow it once, then use Claude Desktop
directly.

---

## Prerequisites by Skill

| Skill | Requirements |
|---|---|
| `/review-internal` | Internet access; pathway report DOCX and Curator Guide PDF uploaded to the conversation |
| `/annotate-pathway-from-reviews-or-topic_name` | claude.ai Pro/Team/Enterprise (Projects) or the Claude API; PubMed and PMC MCP servers recommended; internet access for Mode B |
| `/extract-reactions` | One or more review-article PDFs; internet access to `eutils.ncbi.nlm.nih.gov` |
| `/release-doi-batch` | DOIs.xlsx from the Team Drive; Python 3 with `pandas` and `openpyxl` |
| `/release-qa-tracker` | Python 3 with `openpyxl`; two QA output directories, or an existing comparison file |
| `/curation-build-illustration` | Python 3 (stdlib only); network access to `reactome.org` for name search and icon/EHLD download (accession lookup works offline); a base-EHLD ST_ID for Mode A, or a sample image for Mode C |
| `/admin-drive-readme` | Python 3; Google API client libraries (in `requirements.txt`); OAuth credentials at `~/.config/reactome/credentials.json` |
| `/spotlight-article-drafter` | The candidate paper (PDF, DOI, or URL) |
| `/analysis-graphdb-setup` | Claude Desktop (Pro plan); Docker Desktop; Node.js; `neo4j-mcp` binary; `uv` package manager |

> **Host allowlisting.** In Claude Code launched from the repo root,
> `.claude/settings.json` allowlists `eutils.ncbi.nlm.nih.gov` (`/extract-reactions`)
> and `reactome.org` (`/curation-build-illustration`) automatically. In claude.ai
> (browser), add both manually via **Settings → Capabilities → Domain allowlist**.
> Without them, PMID resolution and icon search fail rather than falling back to
> fabricated values.

---

## Using Skills Outside Claude Code

To use a skill in the claude.ai desktop app, zip its directory and upload it via
**Customize → Skills → Upload ZIP**:

```bash
zip -r review-internal.zip .claude/skills/review-internal/
```

---

## Quick Reference

| What you want to do | Command |
|---|---|
| Go to the repo | `cd ~/Developer/reactome-curator-workflows` |
| Start Claude Code | `claude` |
| Check active credentials | `/status` (inside Claude Code) |
| Check session token usage | `/cost` (inside Claude Code) |
| Update the repo | `git pull` |
| Exit Claude Code | `/exit` or `Control-C` |

---

## Troubleshooting

**`claude: command not found`** — Claude Code is not on your PATH. Close and reopen
Terminal. If it persists, re-run the install command.

**`Error: Invalid API key`** — Run `echo $ANTHROPIC_API_KEY`. If blank, redo Setup
step 2. Check for stray spaces or quotation marks inside the key in `~/.zshrc`.

**Claude Code uses my Claude.ai account instead of the API key** — `ANTHROPIC_API_KEY`
is not exported. Check with `echo $ANTHROPIC_API_KEY`, and run `/status` inside Claude
Code to see the active method.

**Python import errors when running a skill** — Re-run
`pip3 install --user -r requirements.txt` from the repo root. If pip reports
`externally-managed-environment`, use the virtual-environment route in Setup step 4.

**GitHub prompts for a password during clone** — Use a personal access token with the
`repo` scope, not your account password.

**PMID resolution returns blanks, or icon search fails** — You launched Claude Code
from outside the repository folder, so the host allowlist in `.claude/settings.json`
never loaded. Restart from `~/Developer/reactome-curator-workflows`.

---

## Repository Structure

```
reactome-curator-workflows/
├── CLAUDE.md                      ← repo conventions + "Adding a New Skill" SOP
├── README.md                      ← this file
├── requirements.txt               ← pinned Python dependencies for all skills
├── .gitignore
├── illustrations/                 ← generated illustration outputs (git-ignored)
└── .claude/
    ├── settings.json              ← host allowlist (eutils.ncbi.nlm.nih.gov, reactome.org)
    └── skills/
        ├── review-internal/                             ← + Curator Guide V94, Data Model
        │                                                  Glossary V95, naming-rule files
        ├── annotate-pathway-from-reviews-or-topic_name/  ← + RLE annotation reference
        ├── extract-reactions/
        ├── release-doi-batch/                           ← + generate_crossref_xml.py
        ├── release-qa-tracker/                          ← + compare_dirs.sh
        ├── curation-build-illustration/                 ← + EHLD/Icon Library specs,
        │                                                  icon_mappings/, reactome_icons.py
        ├── admin-drive-readme/                           ← + update_drive_readme.py
        ├── spotlight-article-drafter/
        └── analysis-graphdb-setup/                       ← + update_reactome.sh
```

Each skill directory holds its own `SKILL.md` plus the scripts, templates, and
reference documents it needs. Open a skill's directory to see its bundled materials.

---

## Contributing

Skills are added by pull request — see **Adding a New Skill** in `CLAUDE.md` for the
checklist. Suggestions and bug reports are welcome as GitHub issues. When proposing a
change to a curation standard or reference file, cite the specific section of the
Curator Guide or Data Model Glossary that supports it, and note the guide version.

---

## Contact

- Repo maintainer: Marc Gillespie (SJU) — open a GitHub
  [issue](https://github.com/reactome/reactome-curator-workflows/issues) for repo or
  skill questions
- Curation standards questions: consult Curator Guide V94
