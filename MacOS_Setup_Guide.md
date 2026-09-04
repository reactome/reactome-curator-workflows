# Reactome Curator Workflows — macOS Setup Guide

This guide walks you through setting up Claude Code and the Reactome curator workflow skills on a Mac, starting from scratch. No prior experience with the Terminal is assumed.

**Time to complete:** approximately 20–30 minutes (first time only).

---

## What You Are Setting Up

| Component | What it is |
| :---- | :---- |
| **Terminal** | The text-based window where you type commands to control your Mac |
| **Git** | A tool that downloads and updates code from GitHub |
| **Claude Code** | The AI assistant that runs in your Terminal |
| **reactome-curator-workflows** | The Reactome skill library — curation tools powered by Claude Code |
| **Python 3 + packages** | Required by two skills: `/release-doi-batch` and `/release-qa-tracker` |
| **Node.js** *(optional)* | Only needed for `/analysis-graphdb-setup` (the Neo4j MCP server) — not for the base install |

---

## Before You Start

You need:

- A Mac running **macOS Ventura (13) or later**. To check: Apple menu → About This Mac.
- An **Anthropic API key** issued from the Reactome organizational account.
  - Contact the repo maintainer (Marc Gillespie) to receive your key.
  - Log in at **console.anthropic.com** → **API Keys** → **Create Key**.
  - Copy it immediately — it looks like `sk-ant-api03-...` and will not be shown again.
  - See **[API_Billing_Best_Practices.md](./API_Billing_Best_Practices.md)** for how the
    Reactome organization, workspaces, spend limits, and key rotation are managed.

**API key vs. Claude.ai Pro:** The Reactome organizational API key bills against the shared
Reactome organizational credit balance (the Console API org). Your personal Claude.ai Pro
subscription (if you have one) is separate and unaffected. Always use the organizational key
for Reactome pipeline work. (Note: some subscription-only features such as Claude Code
**Remote Control** do not work with API-key access — see `API_Billing_Best_Practices.md`.)

---

## Step 1 — Open Terminal

Terminal is a program already on your Mac. It lets you type commands instead of clicking buttons.

**To open Terminal:**

1. Press `Command (⌘) + Space` to open Spotlight Search.
2. Type **Terminal** and press `Return`.

A window opens with a prompt that looks something like:

```
yourname@MacBook-Pro ~ %
```

The `~` symbol means you are in your **Home folder**. The `%` is where you type commands.

**How to use this guide:** When you see a command in a code box, copy it, paste it into
Terminal (`Command-V`), and press `Return` to run it. Run one command at a time and wait for
each to finish.

---

## Step 2 — Create the Developer Folder

Code projects live by convention in a `Developer` folder in your Home folder. Run this command to create it:

```bash
mkdir -p ~/Developer
```

Nothing visible happens if it works — that is normal.

---

## Step 3 — Install Git

Check whether Git is already installed:

```bash
git --version
```

If you see a version number, Git is installed — skip to Step 4. If you see `command not found`, run:

```bash
xcode-select --install
```

A dialog will appear asking you to install the Command Line Tools. Click **Install**, then **Agree**. This takes a few minutes. When it finishes, run `git --version` again to confirm.

Set your Git identity (required for commits):

```bash
git config --global user.name "Your Name"
git config --global user.email "your@email.com"
```

---

## Step 4 — Install Node.js *(optional — only for `/analysis-graphdb-setup`)*

**You do not need Node.js for the base setup.** Claude Code (Step 5) installs as a standalone
binary and does not require Node. Skip this step unless you plan to use
`/analysis-graphdb-setup`, which needs Node.js for the `neo4j-mcp` server.

If you do need it, check whether it is already installed:

```bash
node --version
```

If you see `v18.x.x` or higher, you are set. Otherwise install the **LTS** release from
[**https://nodejs.org**](https://nodejs.org) (the site auto-detects Apple Silicon vs. Intel),
run the downloaded `.pkg`, and verify:

```bash
node --version
```

---

## Step 5 — Install Claude Code

Claude Code is installed with a single command:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

Verify:

```bash
claude --version
```

You should see a version number like `1.x.x`.

---

## Step 6 — Set Your Anthropic API Key

Add your Reactome organizational API key to your shell configuration so it is available every time you open Terminal. Replace `your-key-here` with the actual key you obtained in the *Before You Start* section above.

```bash
echo 'export ANTHROPIC_API_KEY="your-key-here"' >> ~/.zshrc
source ~/.zshrc
```

Verify the key is set:

```bash
echo $ANTHROPIC_API_KEY
```

You should see your key printed. If you see a blank line, repeat the two commands above and confirm you replaced `your-key-here` with the real key.

**Authentication note:** Claude Code offers two login methods — a Claude.ai subscription (OAuth, no per-token charges) and the Anthropic Console (API key, pay-as-you-go). For Reactome work, always use the API key method so usage bills to the shared organizational credit pool. When `ANTHROPIC_API_KEY` is set in your environment, it takes priority automatically. Run `/status` inside Claude Code at any time to confirm which credentials are active.

**Security:** Your key is stored only on your local Mac in `~/.zshrc`. Never commit it to GitHub or share it in chat or email.

**Quick verification** — confirm the key is active and billing to the Reactome account:

```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model": "claude-haiku-4-5-20251001", "max_tokens": 32,
       "messages": [{"role": "user", "content": "Hello"}]}'
```

A JSON response containing `"type": "message"` confirms your key is working.

---

## Step 7 — Clone the Reactome Repository

Before cloning, the maintainer must add you as a collaborator on GitHub. You will receive an email invitation — accept it before running this command.

```bash
git clone https://github.com/reactome/reactome-curator-workflows.git \
    ~/Developer/reactome-curator-workflows
```

**If prompted for a password:** use a personal access token, not your GitHub account password. Generate one at [**https://github.com/settings/tokens**](https://github.com/settings/tokens) with the `repo` scope selected. Paste the token where Terminal asks for your password.

Navigate into the folder:

```bash
cd ~/Developer/reactome-curator-workflows
```

Confirm you are in the right place:

```bash
ls
```

You should see files including `CLAUDE.md`, `README.md`, and a `.claude/` directory.

---

## Step 8 — Install Python Dependencies

Several skills (`/release-doi-batch`, `/release-qa-tracker`, `/admin-drive-readme`, and the
reaction-table output of `/annotate-pathway-from-reviews-or-topic_name`) require Python 3 and a
handful of packages. Python 3 is already on modern Macs. The package versions are pinned in the
repo's `requirements.txt` so every curator gets the same set — install from there, running this
from inside the `reactome-curator-workflows` folder you cloned in Step 7:

```bash
pip3 install --user -r requirements.txt
```

If pip refuses with `externally-managed-environment` (PEP 668 — common with Homebrew- or
uv-managed Pythons), use a virtual environment instead:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

...then run skill scripts with `.venv/bin/python3` rather than `python3`. See the notes at the top
of `requirements.txt` for details.

If you see a PATH warning after installing, add the path to your shell config (replace `3.x` with the version number shown in the warning, and `[you]` with your username):

```bash
echo 'export PATH="/Users/[you]/Library/Python/3.x/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

> `requirements.txt` already includes the Google API client libraries that `/admin-drive-readme`
> needs, so there is nothing extra to install for that skill.

---

## Step 9 — Launch Claude Code

Every time you want to use the Reactome skills, open Terminal and run:

```bash
cd ~/Developer/reactome-curator-workflows
claude
```

The first line moves you into the Reactome repo folder. The second starts Claude Code, which automatically reads `CLAUDE.md` and loads all skills. You will see a welcome message and a prompt where you can start typing.

To confirm everything loaded correctly, ask Claude:

> "What do you know about this project?"

Claude should describe Reactome, the team, and the available skills.

**Important:** Always launch Claude Code from inside the `reactome-curator-workflows` folder, not from another directory. Some skills (particularly `/extract-reactions` and `/curation-build-illustration`) rely on `.claude/settings.json` in the repo root for domain allowlisting (`eutils.ncbi.nlm.nih.gov` and `reactome.org`).

**Mac app note:** The Claude for Mac desktop app's `</>` Claude Code button runs in a cloud/OAuth-only context and does not read `ANTHROPIC_API_KEY` from your shell. Always launch Claude Code from Terminal for Reactome work.

---

## Step 10 — Run Your First Skill

Type a skill name at the Claude Code prompt to invoke it. For example:

```
/review-internal
```

Claude Code will guide you through the required inputs. See the *Reactome Curator Workflows — Claude Code Usage Guide* (`Reactome_CuratorWorkflows_ClaudeCode_Guide.docx`, in this repository) and the top-level `README.md` for full documentation on each skill.

---

## Keeping the Repository Up to Date

New skills and updates are published to GitHub. Pull the latest version before each session:

```bash
cd ~/Developer/reactome-curator-workflows
git pull
```

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

**`Error: Invalid API key`** Your key is not set or is incorrect. Run `echo $ANTHROPIC_API_KEY` to check. If blank, repeat Step 6. Confirm the key in `~/.zshrc` has no extra spaces or quotation marks inside the key itself.

**Claude Code uses my Claude.ai account instead of the API key** Check that `ANTHROPIC_API_KEY` is exported: `echo $ANTHROPIC_API_KEY`. If blank, the variable is not set. Run `/status` inside Claude Code to confirm the active authentication method.

**`git: command not found`** Git is not installed. Repeat Step 3.

**Python package import errors when running a skill** Run `pip3 install --user -r requirements.txt` again from inside the `reactome-curator-workflows` folder. If pip reports `externally-managed-environment`, use the virtual-environment route in Step 8.

**GitHub prompts for a password during clone** Use a personal access token, not your GitHub password. See Step 7.

**PMID resolution returns blanks in `/extract-reactions`, or icon search fails in `/curation-build-illustration`** Make sure you launched Claude Code from inside the `reactome-curator-workflows` folder (Step 9), not from another directory — the host allowlist lives in the repo's `.claude/settings.json`.

---

## Repository Layout

```
~/Developer/reactome-curator-workflows/
├── CLAUDE.md                                            ← project context (read automatically by Claude Code)
├── README.md                                            ← skill documentation and prerequisites table
├── MacOS_Setup_Guide.md                                 ← this file
├── API_Billing_Best_Practices.md                        ← API key & org-billing management
├── skill_running_questions.md                           ← team run-mode / governance discussion doc
├── Reactome_CuratorWorkflows_ClaudeCode_Guide.docx      ← skill usage guide
├── .gitignore
├── illustrations/                                       ← generated illustration outputs (git-ignored)
├── chrome-extensions/
│   └── pmid-tagger/                                     ← Chrome extension: prefix downloads with PMID-<id>_
└── .claude/
    ├── settings.json                                    ← host allowlist (eutils.ncbi.nlm.nih.gov, reactome.org)
    └── skills/
        ├── review-internal/                             ← /review-internal
        ├── annotate-pathway-from-reviews-or-topic_name/ ← /annotate-pathway-from-reviews-or-topic_name
        ├── extract-reactions/                           ← /extract-reactions
        ├── release-doi-batch/                           ← /release-doi-batch
        ├── admin-drive-readme/                          ← /admin-drive-readme
        ├── release-qa-tracker/                          ← /release-qa-tracker
        ├── analysis-graphdb-setup/                      ← /analysis-graphdb-setup
        └── curation-build-illustration/                 ← /curation-build-illustration
```

---

## Contact

- Repo maintainer: Marc Gillespie (SJU)
- Curation standards questions: consult Curator Guide V94
- Repo or skill questions: open a GitHub issue at [https://github.com/reactome/reactome-curator-workflows/issues](https://github.com/reactome/reactome-curator-workflows/issues)
