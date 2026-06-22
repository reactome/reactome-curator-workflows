# Reactome Curator Workflows — macOS Setup Guide

This guide walks you through setting up Claude Code and the Reactome curator workflow
skills on a Mac, starting from scratch. No prior experience with the Terminal is assumed.

**Time to complete:** approximately 20–30 minutes (first time only).

---

## What You Are Setting Up

| Component | What it is |
|---|---|
| **Terminal** | The text-based window where you type commands to control your Mac |
| **Homebrew** | A tool that installs other software on your Mac (like an App Store for developers) |
| **Node.js** | A software platform required by Claude Code |
| **Git** | A tool that downloads and updates code from GitHub |
| **Claude Code** | The AI assistant that runs in your Terminal |
| **reactome-curator-workflows** | The Reactome skill library — curation tools powered by Claude Code |
| **Python 3 + packages** | Required by two skills: `/generate-doi-batch` and `/reactome-qa-tracker` |

---

## Before You Start

You need:

- A Mac running **macOS Ventura (13) or later**. To check: Apple menu → About This Mac.
- An **Anthropic account** with an **API key**.
  - Create an account at: https://console.anthropic.com
  - After signing in, go to **API Keys** and click **Create Key**. Copy it — you will need
    it in Step 5. It looks like: `sk-ant-api03-...`
  - Claude Code requires a paid Anthropic plan (or claude.ai Pro/Team).

---

## Step 1 — Open Terminal

Terminal is a program already on your Mac. It lets you type commands instead of clicking
buttons. Think of it as a direct line to your computer.

**To open Terminal:**

1. Press `Command (⌘) + Space` to open Spotlight Search.
2. Type **Terminal** and press `Return`.

A window opens with a prompt that looks something like:

```
yourname@MacBook-Pro ~ %
```

The `~` symbol means you are currently in your **Home folder** (the one with your name
in the Finder sidebar). The `%` is the cursor — this is where you type commands.

> **How to use this guide:** When you see a command in a grey box like the one below,
> click anywhere in the box to select it, copy it (`Command-C`), paste it into Terminal
> (`Command-V`), and press `Return` to run it. Run one command at a time and wait for
> each one to finish before running the next.

---

## Step 2 — Create the Developer Folder

By convention, code projects live in a folder called `Developer` in your Home folder.
Run this command to create it:

```bash
mkdir -p ~/Developer
```

Nothing visible happens if it works — that is normal. The folder now exists at
`/Users/yourname/Developer` (visible in Finder at `Home → Developer`).

---

## Step 3 — Install Xcode Command Line Tools

These are free tools from Apple that include **Git** (used to download the Reactome repo)
and other utilities needed by developer software.

Run:

```bash
xcode-select --install
```

A dialog box will appear on your screen asking you to install the Command Line Tools.
Click **Install**, then **Agree**. The download takes a few minutes.

When it finishes, verify the install worked:

```bash
git --version
```

You should see something like `git version 2.x.x`. If you do, Git is installed.

---

## Step 4 — Install Homebrew

Homebrew is a package manager — it lets you install software from the Terminal with a
single command. It is the standard way to install developer tools on a Mac.

Paste this entire command (it is one line):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

The installer will ask for your Mac **login password**. Type it and press `Return`.
(You will not see the password as you type — this is normal.)

Follow any on-screen prompts. When finished, the installer may print a message telling
you to run two additional commands to add Homebrew to your PATH. If you see that message,
run those two commands exactly as printed.

Verify:

```bash
brew --version
```

You should see `Homebrew x.x.x`.

---

## Step 5 — Install Node.js

Claude Code requires Node.js (version 18 or higher). Install it via Homebrew:

```bash
brew install node
```

Verify:

```bash
node --version
```

You should see `v20.x.x` or similar.

---

## Step 6 — Install Claude Code

Claude Code is installed as a global command-line tool via `npm` (which came with Node.js):

```bash
npm install -g @anthropic-ai/claude-code
```

Verify:

```bash
claude --version
```

You should see a version number like `1.x.x`.

---

## Step 7 — Set Your Anthropic API Key

Claude Code needs your API key to connect to the AI. You will add it to your shell
configuration file so it is available every time you open Terminal.

Run this command, replacing `your-key-here` with the API key you copied in Step 0
(it starts with `sk-ant-api03-`):

```bash
echo 'export ANTHROPIC_API_KEY="your-key-here"' >> ~/.zshrc
```

Then reload your Terminal configuration so the key takes effect immediately:

```bash
source ~/.zshrc
```

Verify:

```bash
echo $ANTHROPIC_API_KEY
```

You should see your key printed. If you see a blank line, re-run the two commands above
and check that you replaced `your-key-here` with the actual key.

> **Security note:** Your API key is stored only on your local Mac in `~/.zshrc`. It is
> never committed to GitHub and should never be shared.

---

## Step 8 — Clone the Reactome Repository

"Cloning" downloads a copy of the Reactome curator workflows repository from GitHub to
your Mac. You only do this once.

```bash
git clone https://github.com/reactome/reactome-curator-workflows.git ~/Developer/reactome-curator-workflows
```

This creates a folder at `~/Developer/reactome-curator-workflows` containing all the
skills and supporting files.

Navigate into the folder:

```bash
cd ~/Developer/reactome-curator-workflows
```

Your Terminal prompt will now show the folder name. You can confirm you are in the right
place:

```bash
ls
```

You should see files including `CLAUDE.md`, `README.md`, and a `.claude/` directory.

---

## Step 9 — Install Python Dependencies

Two skills (`/generate-doi-batch` and `/reactome-qa-tracker`) require Python 3 and
two packages. Python 3 is already on modern Macs. Install the packages:

```bash
pip3 install pandas openpyxl
```

If you see a permissions error, try:

```bash
pip3 install --user pandas openpyxl
```

---

## Step 10 — Launch Claude Code

Every time you want to use the Reactome skills, open Terminal and run:

```bash
cd ~/Developer/reactome-curator-workflows
claude
```

The first line moves you into the Reactome repo folder. The second line starts Claude
Code. You only need to run `cd` if you are not already in that folder.

When Claude Code starts, it automatically reads `CLAUDE.md` (the project context file)
and loads all skills. You will see a welcome message and a prompt where you can start
typing.

---

## Step 11 — Run Your First Skill

Type a skill name at the Claude Code prompt to invoke it. For example:

```
/internal-module-review
```

Claude Code will guide you through uploading the required files and running the review.
See the README for full skill documentation and usage examples.

---

## Keeping the Repository Up to Date

New skills and updates are published to GitHub. To pull the latest version:

```bash
cd ~/Developer/reactome-curator-workflows
git pull
```

Run this periodically (e.g., before each Reactome release) to stay current.

---

## Quick Reference — Commands You Will Use Every Day

| What you want to do | Command |
|---|---|
| Open Terminal | `Command (⌘) + Space`, type "Terminal", press `Return` |
| Go to the Reactome repo | `cd ~/Developer/reactome-curator-workflows` |
| Start Claude Code | `claude` |
| Update the repo | `git pull` |
| Exit Claude Code | Type `/exit` or press `Control-C` |

---

## Troubleshooting

**`claude: command not found`**
Node.js or Claude Code is not on your PATH. Close Terminal, reopen it, and try again.
If the problem persists, run `npm install -g @anthropic-ai/claude-code` again.

**`Error: Invalid API key`**
Your API key is not set or is incorrect. Run `echo $ANTHROPIC_API_KEY` to check.
If it is blank, repeat Step 7. Make sure the key in `~/.zshrc` does not have extra
spaces or quotation marks inside the key itself.

**`git: command not found`**
The Xcode Command Line Tools are not installed. Repeat Step 3.

**`brew: command not found`**
Homebrew is not on your PATH. Check if Homebrew printed post-install instructions
in Step 4 and run those commands.

**Python package import errors when running a skill**
Run `pip3 install pandas openpyxl` again. If you get a permissions error, use
`pip3 install --user pandas openpyxl`.

**PMID resolution returns blanks in `/extract-reactions`**
Claude Code automatically allowlists `eutils.ncbi.nlm.nih.gov` via `.claude/settings.json`
in this repo. If you see blank Source cells, make sure you launched Claude Code from
inside the `reactome-curator-workflows` folder (Step 10), not from another directory.

---

## Repository Layout (for reference)

```
~/Developer/reactome-curator-workflows/
├── CLAUDE.md                          ← project context (read automatically by Claude Code)
├── README.md                          ← skill documentation and prerequisites table
├── MacOS_Setup_Guide.md               ← this file
├── Reactome_CuratorWorkflows_ClaudeCode_Guide_v1_3.docx  ← full onboarding guide
├── .gitignore
├── chrome-extensions/
│   └── pmid-tagger/                   ← Chrome extension: prefix downloads with PMID-<id>_
└── .claude/
    ├── settings.json                  ← host allowlist (eutils.ncbi.nlm.nih.gov, etc.)
    └── skills/
        ├── internal-module-review/    ← /internal-module-review
        ├── annotate-pathway-from-reviews-or-topic_name/  ← /annotate-pathway-from-reviews-or-topic_name
        ├── extract-reactions/         ← /extract-reactions
        ├── generate-doi-batch/        ← /generate-doi-batch
        ├── update-gdrive-readme/      ← /update-gdrive-readme
        ├── reactome-qa-tracker/       ← /reactome-qa-tracker
        └── reactome-neo4j-ols-setup/  ← /reactome-neo4j-ols-setup
```

---

## Contact

- Repo maintainer: Marc Gillespie (NYU / SJU) — gillespm@stjohns.edu
- Curation standards questions: Reactome curator Slack channel
- Repo or skill questions: open a GitHub issue at https://github.com/reactome/reactome-curator-workflows/issues
