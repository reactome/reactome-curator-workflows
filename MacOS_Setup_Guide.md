# Reactome Curator Workflows — macOS Setup Guide

This guide walks you through setting up Claude Code and the Reactome curator workflow skills on a Mac, starting from scratch. No prior experience with the Terminal is assumed.

**Time to complete:** approximately 20–30 minutes (first time only).

---

## What You Are Setting Up

| Component | What it is |
| :---- | :---- |
| **Terminal** | The text-based window where you type commands to control your Mac |
| **Git** | A tool that downloads and updates code from GitHub |
| **Node.js** | A software platform required by Claude Code |
| **Claude Code** | The AI assistant that runs in your Terminal |
| **reactome-curator-workflows** | The Reactome skill library — curation tools powered by Claude Code |
| **Python 3 \+ packages** | Required by two skills: `/generate-doi-batch` and `/reactome-qa-tracker` |

---

## Before You Start

You need:

- A Mac running **macOS Ventura (13) or later**. To check: Apple menu → About This Mac.  
- An **Anthropic API key** issued from the Reactome organizational account.  
  - Contact the repo maintainer (Marc Gillespie) to receive your key.  
  - Log in at **platform.anthropic.com** → **API Keys** → **Create Key**.  
  - Copy it immediately — it looks like `sk-ant-api03-...` and will not be shown again.  
  - See the *Reactome API Key Setup Guide* for full instructions on obtaining and securing your key.

**API key vs. Claude.ai Pro:** The Reactome organizational API key bills against the shared AI for Science credit pool. Your personal Claude.ai Pro subscription (if you have one) is separate and unaffected. Always use the organizational key for Reactome pipeline work.

---

## Step 1 — Open Terminal

Terminal is a program already on your Mac. It lets you type commands instead of clicking buttons.

**To open Terminal:**

1. Press `Command (⌘) + Space` to open Spotlight Search.  
2. Type **Terminal** and press `Return`.

A window opens with a prompt that looks something like:

yourname@MacBook-Pro \~ %

The `~` symbol means you are in your **Home folder**. The `%` is where you type commands.

**How to use this guide:** When you see a command in a grey box, click anywhere in the box to select it, copy it (`Command-C`), paste it into Terminal (`Command-V`), and press `Return` to run it. Run one command at a time and wait for each to finish.

---

## Step 2 — Create the Developer Folder

Code projects live by convention in a `Developer` folder in your Home folder. Run this command to create it:

mkdir \-p \~/Developer

Nothing visible happens if it works — that is normal.

---

## Step 3 — Install Git

Check whether Git is already installed:

git \--version

If you see a version number, Git is installed — skip to Step 4\. If you see `command not found`, run:

xcode-select \--install

A dialog will appear asking you to install the Command Line Tools. Click **Install**, then **Agree**. This takes a few minutes. When it finishes, run `git --version` again to confirm.

Set your Git identity (required for commits):

git config \--global user.name "Your Name"

git config \--global user.email "your@email.com"

---

## Step 4 — Install Node.js

Claude Code requires Node.js 18 or higher. Check whether it is already installed:

node \--version

If you see `v18.x.x` or higher, skip to Step 5\. If you see an older version or `command not found`, install Node.js using the official installer:

1. Go to [**https://nodejs.org**](https://nodejs.org) and download the **LTS** release. The site auto-detects whether you have Apple Silicon (M1/M2/M3/M4) or Intel and offers the correct package — you do not need to choose.  
2. Run the downloaded `.pkg` file and follow the prompts.

Verify after installation:

node \--version

You should see `v20.x.x` or similar.

---

## Step 5 — Install Claude Code

Claude Code is installed with a single command:

curl \-fsSL https://claude.ai/install.sh | bash

Verify:

claude \--version

You should see a version number like `1.x.x`.

---

## Step 6 — Set Your Anthropic API Key

Add your Reactome organizational API key to your shell configuration so it is available every time you open Terminal. Replace `your-key-here` with the actual key you obtained in the *Before You Start* section above.

echo 'export ANTHROPIC\_API\_KEY="your-key-here"' \>\> \~/.zshrc

source \~/.zshrc

Verify the key is set:

echo $ANTHROPIC\_API\_KEY

You should see your key printed. If you see a blank line, repeat the two commands above and confirm you replaced `your-key-here` with the real key.

**Authentication note:** Claude Code offers two login methods — a Claude.ai subscription (OAuth, no per-token charges) and the Anthropic Console (API key, pay-as-you-go). For Reactome work, always use the API key method so usage bills to the shared organizational credit pool. When `ANTHROPIC_API_KEY` is set in your environment, it takes priority automatically. Run `/status` inside Claude Code at any time to confirm which credentials are active.

**Security:** Your key is stored only on your local Mac in `~/.zshrc`. Never commit it to GitHub or share it in chat or email.

**Quick verification** — confirm the key is active and billing to the Reactome account:

curl https://api.anthropic.com/v1/messages \\

  \-H "x-api-key: $ANTHROPIC\_API\_KEY" \\

  \-H "anthropic-version: 2023-06-01" \\

  \-H "content-type: application/json" \\

  \-d '{"model": "claude-haiku-4-5-20251001", "max\_tokens": 32,

       "messages": \[{"role": "user", "content": "Hello"}\]}'

A JSON response containing `"type": "message"` confirms your key is working.

---

## Step 7 — Clone the Reactome Repository

Before cloning, Marc must add you as a collaborator on GitHub. You will receive an email invitation — accept it before running this command.

git clone https://github.com/reactome/reactome-curator-workflows.git \\

    \~/Developer/reactome-curator-workflows

**If prompted for a password:** use a personal access token, not your GitHub account password. Generate one at [**https://github.com/settings/tokens**](https://github.com/settings/tokens) with the `repo` scope selected. Paste the token where Terminal asks for your password.

Navigate into the folder:

cd \~/Developer/reactome-curator-workflows

Confirm you are in the right place:

ls

You should see files including `CLAUDE.md`, `README.md`, and a `.claude/` directory.

---

## Step 8 — Install Python Dependencies

Two skills (`/generate-doi-batch` and `/reactome-qa-tracker`) require Python 3 and two packages. Python 3 is already on modern Macs. Install the packages:

pip3 install pandas openpyxl

If you see a permissions error, try:

pip3 install \--user pandas openpyxl

If you see a PATH warning after installing, add the path to your shell config (replace `3.x` with the version number shown in the warning):

echo 'export PATH="/Users/\[you\]/Library/Python/3.x/bin:$PATH"' \>\> \~/.zshrc

source \~/.zshrc

---

## Step 9 — Launch Claude Code

Every time you want to use the Reactome skills, open Terminal and run:

cd \~/Developer/reactome-curator-workflows

claude

The first line moves you into the Reactome repo folder. The second starts Claude Code, which automatically reads `CLAUDE.md` and loads all skills. You will see a welcome message and a prompt where you can start typing.

To confirm everything loaded correctly, ask Claude:

"What do you know about this project?"

Claude should describe Reactome, the team, and the available skills.

**Important:** Always launch Claude Code from inside the `reactome-curator-workflows` folder, not from another directory. Some skills (particularly `/extract-reactions`) rely on `.claude/settings.json` in the repo root for domain allowlisting.

**Mac app note:** The Claude for Mac desktop app's `</>` Claude Code button runs in a cloud/OAuth-only context and does not read `ANTHROPIC_API_KEY` from your shell. Always launch Claude Code from Terminal for Reactome work.

---

## Step 10 — Run Your First Skill

Type a skill name at the Claude Code prompt to invoke it. For example:

/internal-module-review

Claude Code will guide you through the required inputs. See the *Reactome Curator Workflows — Claude Code Usage Guide* (in this repository) for full documentation on each skill.

---

## Keeping the Repository Up to Date

New skills and updates are published to GitHub. Pull the latest version before each session:

cd \~/Developer/reactome-curator-workflows

git pull

New or updated skills are available immediately after pulling — no restart of Claude Code is needed if it is already running.

---

## Quick Reference

| What you want to do | Command |
| :---- | :---- |
| Open Terminal | `Command (⌘) + Space`, type "Terminal", press `Return` |
| Go to the Reactome repo | `cd ~/Developer/reactome-curator-workflows` |
| Start Claude Code | `claude` |
| Check active credentials | `/status` (inside Claude Code) |
| Check session token usage | `/cost` (inside Claude Code) |
| Update the repo | `git pull` |
| Exit Claude Code | Type `/exit` or press `Control-C` |

---

## Troubleshooting

**`claude: command not found`** Claude Code is not on your PATH. Close Terminal, reopen it, and try again. If the problem persists, run `curl -fsSL https://claude.ai/install.sh | bash` again.

**`Error: Invalid API key`** Your key is not set or is incorrect. Run `echo $ANTHROPIC_API_KEY` to check. If blank, repeat Step 6\. Confirm the key in `~/.zshrc` has no extra spaces or quotation marks inside the key itself.

**Claude Code uses my Claude.ai account instead of the API key** Check that `ANTHROPIC_API_KEY` is exported: `echo $ANTHROPIC_API_KEY`. If blank, the variable is not set. Run `/status` inside Claude Code to confirm the active authentication method.

**`git: command not found`** Git is not installed. Repeat Step 3\.

**Python package import errors when running a skill** Run `pip3 install pandas openpyxl` again. If you get a permissions error, use `pip3 install --user pandas openpyxl`.

**GitHub prompts for a password during clone** Use a personal access token, not your GitHub password. See Step 7\.

**PMID resolution returns blanks in `/extract-reactions`** Make sure you launched Claude Code from inside the `reactome-curator-workflows` folder (Step 9), not from another directory.

---

## Repository Layout

\~/Developer/reactome-curator-workflows/

├── CLAUDE.md                          ← project context (read automatically by Claude Code)

├── README.md                          ← skill documentation and prerequisites table

├── MacOS\_Setup\_Guide.md               ← this file

├── Reactome\_CuratorWorkflows\_ClaudeCode\_Guide\_v2.docx  ← skill usage guide

├── Reactome\_API\_Key\_Setup.docx        ← API key setup and credit management

├── .gitignore

├── chrome-extensions/

│   └── pmid-tagger/                   ← Chrome extension: prefix downloads with PMID-\<id\>\_

└── .claude/

    ├── settings.json                  ← host allowlist (eutils.ncbi.nlm.nih.gov, etc.)

    └── skills/

        ├── internal-module-review/    ← /internal-module-review

        ├── annotate-pathway-from-reviews-or-topic\_name/  ← /annotate-pathway-from-reviews-or-topic\_name

        ├── extract-reactions/         ← /extract-reactions

        ├── generate-doi-batch/        ← /generate-doi-batch

        ├── update-gdrive-readme/      ← /update-gdrive-readme

        ├── reactome-qa-tracker/       ← /reactome-qa-tracker

        └── reactome-neo4j-ols-setup/  ← /reactome-neo4j-ols-setup

---

## Contact

- Repo maintainer: Marc Gillespie (SJU)  
- Curation standards questions: consult Curator Guide V94  
- Repo or skill questions: open a GitHub issue at [https://github.com/reactome/reactome-curator-workflows/issues](https://github.com/reactome/reactome-curator-workflows/issues)

