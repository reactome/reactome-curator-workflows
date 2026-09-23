---
name: analysis-reactome-mcp
description: Set up and manage the two read-only Reactome MCP servers — gk-central (a nightly-refreshed copy of the gk_central editing database on the curator server) and ols (EBI Ontology Lookup Service) — for Claude Code and Claude Desktop. Three functions, chosen from an opening menu — (1) install both servers, explaining how they work and exactly what changes on the curator's computer; (2) enable or disable them; (3) update them when the curator asks (password or endpoint change, new server versions, checking that the nightly gk_central refresh has run). Passwords are held in the macOS Keychain and never in the repo, a Claude config file, or the chat. Use when a curator wants database or ontology access in Claude, wants to turn it on or off, or something has changed. /review-internal and /release-doi-batch use these servers when present.
---

# Reactome MCP servers

Written September 2026. Platforms: macOS (tested), Windows (same commands, less
tested — see Notes).

This skill does three things, and the curator picks one when it starts:

1. **Install** — set up both servers, explain how they work, and show exactly
   what changes on the computer.
2. **Enable / disable** — turn the servers on or off for Claude.
3. **Update** — refresh the setup when something has changed. Nothing updates
   automatically; the curator starts it.

| Server | What it gives Claude | Needs |
|---|---|---|
| `gk-central` | Read-only queries against Guanming Wu's Neo4j copy of **gk_central**, the editing database, on the curator server, refreshed nightly. Includes unreleased curation. Mostly human (R-HSA) plus other species' directly curated pathways, e.g. *Arabidopsis*, rice, *Drosophila*; no computationally inferred events, which are generated at release. | The connection card and shared password from the curation team |
| `ols` | Live lookups in the EBI Ontology Lookup Service: GO, ChEBI, HP, EFO and 300+ others. | Internet only |

Other skills in this repo (`/review-internal`, `/release-doi-batch`) use the
servers when they're on and run as before when they're off.

---

## Ground rules — Claude must follow these

1. **Never ask for, accept, or repeat a password in the chat.** The curator types
   it into their own terminal (`set-password`), where it goes straight into the
   Keychain. If a curator pastes a password into the conversation anyway, do not
   echo it, write it to any file, or pass it to any command; point them at
   `set-password` instead.
2. **Connection details stay out of the repo.** The repo is public. The gk_central
   host, ports and password belong only in `~/.config/reactome/mcp/` and the
   Keychain — never in a file under this repository, a commit, an issue, or a PR.
   Never add a `.mcp.json`.
3. **Register at user scope only** (`claude mcp add --scope user`, which the helper
   does). Never `--scope project`: that writes `.mcp.json` into the repo.
4. **Read-only, always.** gk-central runs `mcp-neo4j-cypher --read-only`, which
   removes the write tool entirely. gk_central reports read-write access
   server-side, so this client-side flag is what actually protects it. Never
   remove it, and never run a write query by any other route.
5. **Don't print secrets while debugging.** No `claude mcp get`, `security ... -w`,
   `env`, or `cat` of a secrets file in the transcript. `status` reports whether a
   password is stored, never what it is.
6. **Say what will change before changing it.** Every function below tells the
   curator what it's about to do and waits for a go-ahead before the first
   command that changes their computer.

---

## The helper

Every function runs through one standard-library Python script, from the repo root:

    python3 .claude/skills/analysis-reactome-mcp/reactome_mcp.py <command>

| Command | Does | Function |
|---|---|---|
| `status` | What's installed, configured, stored and registered; warns about plain-text passwords in Claude config | all |
| `install-server` | Installs the pinned `mcp-neo4j-cypher` with `uv`; copies the launcher to `~/.config/reactome/mcp/` | 1 |
| `install-ols` | Installs the pinned OLS MCP server with `uv` | 1 |
| `configure gk-central --bolt URL --http URL` | Saves the connection details (owner-only file) | 1, 3 |
| `set-password gk-central` | **Curator runs this in their own terminal.** Stores the password in the Keychain | 1, 3 |
| `test <server>` | Live read-only check: Pathway count, newest edit in the copy, APOC | 1, 3 |
| `enable <server>` | Registers the server with Claude Code (user scope) and Claude Desktop | 1, 2 |
| `disable <server>` | Removes the registration; keeps password and settings | 2 |
| `update-server` | Reinstalls the pinned server versions and refreshes the launcher | 3 |
| `run <server>` | Internal: what Claude Code and Desktop execute. Not for curators | — |

`enable` and `disable` accept `--code-only` or `--desktop-only`.

---

## Opening dialogue

When the skill starts:

1. **Run `status` first**, without comment, so you know what's already in place.

2. **If `$ARGUMENTS` names a function** (`install`, `enable`, `disable`, `on`,
   `off`, `update`), go straight to it, but still say in one sentence what it will
   do.

3. **Otherwise, offer the three functions.** Use the AskUserQuestion tool if it's
   available; otherwise a short numbered list. Put a one-line explanation under
   each, and mark the one that fits `status` as recommended:

   | Option | Explanation | Recommend when |
   |---|---|---|
   | **Install the servers** | First-time setup of gk-central and ols. I'll explain how they work and list everything that changes on your computer before doing anything. | Nothing, or not everything, is installed |
   | **Enable or disable a server** | Turn gk-central or ols on or off for Claude. Nothing is uninstalled; switching back is instant. | Both are installed |
   | **Update the setup** | Something changed — a new password, a new server address, new software versions — or you want to check that the nightly gk_central refresh has run. | Installed and `status` flags something (launcher out of date, plain-text password, failed test) |

4. **Report the relevant part of `status` in plain words** alongside the menu —
   e.g. "gk-central is installed and on; ols isn't installed yet" — not the raw
   output.

---

## Function 1 — Install the servers

### Explain how it works first

Before any command, tell the curator in a few sentences:

- **What the servers are.** Small programs on their own computer that Claude
  starts when it needs them. The gk-central one connects out to Guanming's
  database on the curator server and passes Claude's queries through, read-only.
  The ols one calls the public EBI OLS website. Neither holds a copy of the data.
- **What Claude can then do.** Answer plain-English questions by running
  read-only Cypher against gk_central ("which reactions in R-HSA-XXXX lack a
  literature reference?"), and look up real ontology IDs instead of guessing.
- **How the password stays private.** The Claude config files don't contain it.
  They start a small launcher that reads the password from the macOS Keychain at
  the moment the server starts and hands it straight to the server.
- **Read-only.** The gk-central server is started without any write tool. Claude
  can't change gk_central through it.

### Show what will change on the computer

Then show this list and ask for a go-ahead. Nothing goes into the repository.

| Location | Change |
|---|---|
| `~/.local/bin/` | `uv` adds two programs: `mcp-neo4j-cypher` and `ols-mcp-server` (with their own private Python environments under `~/.local/share/uv/tools/`) |
| `~/.config/reactome/mcp/` | New folder, readable only by the curator: the launcher script and `config.json` (the gk_central connection details) |
| macOS login Keychain | One new item: service `reactome-mcp`, account `gk-central` — the password |
| `~/.claude.json` | Two entries added under `mcpServers` (`gk-central`, `ols`) — Claude Code's user-level MCP list |
| Claude Desktop's `claude_desktop_config.json` | The same two entries added; everything else in the file is kept. A timestamped, owner-only backup is made first |

Everything is reversible: Function 2 removes the Claude entries, and `uv tool
uninstall` removes the programs.

### Prerequisites

| Tool | For | Install |
|---|---|---|
| Python 3.9+ | the helper | macOS ships `/usr/bin/python3`; Windows: python.org |
| `uv` | installing the servers | macOS: `curl -LsSf https://astral.sh/uv/install.sh \| sh`; Windows (PowerShell): `irm https://astral.sh/uv/install.ps1 \| iex` |
| Claude Code and/or Claude Desktop | using the servers | claude.com/download |

No Node.js, no Homebrew, no `sudo`.

### Steps

gk-central is interim: its ports are open to the internet with a shared
password, and Guanming Wu plans to replace it with an https MCP endpoint at
`curator.reactome.org`. If that has happened, see Function 3, "https endpoint is
live", instead of steps 1–5.

**1. Connection card.** The curator needs Guanming's "Setting Up the Reactome MCP
Server" card: bolt URL, browser (http) URL, username, password. It's deliberately
not in this repo; a curation-team colleague can forward it. Ignore the card's
Claude Desktop JSON block — it puts the password in plain text in the config file.
This skill does that step instead.

**2. Install both programs and the launcher:**

    python3 .claude/skills/analysis-reactome-mcp/reactome_mcp.py install-server
    python3 .claude/skills/analysis-reactome-mcp/reactome_mcp.py install-ols

**3. Save the connection details** from the card. The curator can give Claude the
two URLs; they're private but not secret. Never write them into the repo.

    python3 .claude/skills/analysis-reactome-mcp/reactome_mcp.py configure gk-central \
      --bolt bolt://<host>:<bolt-port> --http http://<host>:<http-port>

**4. Store the password — the curator does this themselves.** Ask them to open a
separate Terminal window (not the Claude Code `!` prompt), `cd` to the repo and
run:

    python3 .claude/skills/analysis-reactome-mcp/reactome_mcp.py set-password gk-central

macOS asks for the password twice and puts it in the login Keychain. The script
refuses to run without a real terminal, so it can't be driven from the chat. Wait
for the curator to say it's done.

**5. Test both:**

    python3 .claude/skills/analysis-reactome-mcp/reactome_mcp.py test gk-central
    python3 .claude/skills/analysis-reactome-mcp/reactome_mcp.py test ols

Expect `connected. Pathway count = ...` (5,821 in September 2026, about 3,900 of
them human; gk_central has no computationally inferred events), the date of the newest edit, `APOC schema
procedure: present`, and `OLS reachable`.

**6. Turn both on:**

    python3 .claude/skills/analysis-reactome-mcp/reactome_mcp.py enable gk-central
    python3 .claude/skills/analysis-reactome-mcp/reactome_mcp.py enable ols

**7. Verify in Claude.** Start a **new** Claude Code session, and fully quit and
reopen Claude Desktop (closing the window isn't enough). `claude mcp list` should
show both as connected. Ask *"What gk-central tools do you have?"* — expect
`get_neo4j_schema` and `read_neo4j_cypher`, and **no** `write_neo4j_cypher`. If a
write tool appears, stop and run `disable gk-central`.

**8. Close with a summary** for the curator: what was installed, that both are on,
how to turn them off (Function 2), and when they'd need Function 3.

---

## Function 2 — Enable or disable a server

Ask which server (`gk-central`, `ols`, or both) and which direction, if not given.
Say what will happen, then run:

    python3 .claude/skills/analysis-reactome-mcp/reactome_mcp.py disable gk-central
    python3 .claude/skills/analysis-reactome-mcp/reactome_mcp.py enable gk-central

| | What it does | What it leaves alone |
|---|---|---|
| `disable` | Removes the server from Claude Code's and Claude Desktop's MCP lists. Claude no longer sees its tools | The installed programs, the connection details, the Keychain password |
| `enable` | Adds it back | — (no reinstall, no password prompt) |

Use `--code-only` or `--desktop-only` to switch just one app.

Things to tell the curator:

- **When it takes effect:** Claude Code at the next new session; Claude Desktop
  after a full quit and reopen.
- **Why disable:** to keep a session to the documents alone, to stop Claude
  starting a server that will fail (e.g. the gk_central server is down), or while
  away from the internet.
- **gk_central itself can't be switched from here** — it's Guanming's server. If
  it's down (`Database unavailable`), tell him.
- **Other skills keep working** when a server is off; they note that the database
  check didn't run.

---

## Function 3 — Update the setup

Updates happen only when the curator asks. The skill sets up no background job,
schedule or automatic check.

### What "update" does and doesn't cover

- **The data itself.** gk-central has no local copy, so there is nothing to
  download. The copy on the curator server is refreshed from gk_central every
  night, so queries see curation as of the last nightly run — anything edited in
  the Curator Tool today shows up tomorrow. To confirm the refresh is running, run
  `test gk-central` and read "Newest edit in copy": it should be from the last day
  or so. If it's several days old, the nightly refresh has probably stopped; tell
  Guanming. Nothing changes locally either way. ols is always live.
- **The local setup.** This is what Function 3 changes: the password, the
  connection details, and the installed software.

### How it works

1. Run `status` and `test` for each installed server, and tell the curator what
   they show.
2. Ask what has changed, or identify it from the output, using the table below.
3. Say which command(s) you'll run and what each changes, and wait for the
   go-ahead.
4. Run them, then `test` again to confirm.

| What changed | How you notice | What to do | What changes locally |
|---|---|---|---|
| **Password rotated** | `authentication failed`, for everyone at once | Get the new password from Guanming. The curator reruns `set-password gk-central` in their own terminal, then `test gk-central` | The Keychain item only |
| **Server address moved** | Connection refused or timeouts; a new card from Guanming | `configure gk-central --bolt ... --http ...`, then `test` | `config.json` only; Claude registrations are untouched |
| **https endpoint is live** | Guanming announces it | `disable gk-central`, then register what he provides: `claude mcp add --scope user --transport http gk-central <url>`, plus whatever auth he specifies (keep tokens out of the repo and chat the same way). Keep the name `gk-central` so other skills' permissions still match | Claude registrations; the old password can be removed from Keychain Access |
| **Newer server software** | A maintainer bumps the pinned versions at the top of `reactome_mcp.py` after testing them | `git pull`, then `update-server` | The two programs in `~/.local/bin/` and the launcher |
| **This skill's helper changed** | `status` says "Launcher out of date" (usually after a `git pull`) | `update-server` | The launcher copy in `~/.config/reactome/mcp/` |
| **Plain-text password in a Claude config** | `status` prints a WARNING (e.g. the curator earlier followed the card's JSON) | `enable gk-central` replaces the entry with the launcher. The helper names any backup that still holds the password; delete it once everything works | That config entry |

After `update-server` or any registration change, restart Claude Code sessions
and fully quit and reopen Claude Desktop.

---

## Using the servers from other skills

Tool names in Claude Code are `mcp__<server>__<tool>`:

| Server | Tools |
|---|---|
| `gk-central` | `mcp__gk-central__read_neo4j_cypher`, `mcp__gk-central__get_neo4j_schema` |
| `ols` | `mcp__ols__*` (e.g. `search_terms`, `get_term_info`, `get_term_ancestors`) |

The repo's `.claude/settings.json` pre-approves exactly these — tool names only,
no credentials — so a review doesn't stop for a permission prompt on every query.
The write tool is deliberately not on the list.

Rules for any skill that uses them:

- **Optional, never required.** Check whether the tools are available in the
  session. If they aren't, say so in one line and carry on — never make a skill
  unrunnable because a server is off or the open port has closed.
- **Which server answers which question.** gk-central = the current state of
  curation, including unreleased work. ols = ontology IDs and labels (never assert
  a GO/ChEBI ID from memory when ols is available). For what's publicly released,
  use the ContentService (https://reactome.org/ContentService/).
- **Read-only, bounded queries.** Return `stId` and `displayName`; `LIMIT`
  exploratory queries; match on `stId` or `dbId` rather than names where possible.
- **Check property names before relying on them.** Confirm an unfamiliar property
  with `get_neo4j_schema` or `RETURN keys(n)` on one node first.
- **Report, don't fix.** Record database discrepancies in the skill's output for
  the curator to resolve in the Curator Tool.

`/review-internal` and `/release-doi-batch` each have a short optional
database-check section written to these rules.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Connection refused / timeout to gk-central | Using the server's internal bolt port (what its discovery endpoint and the browser prefill advertise) | Use the bolt port on the card; `configure` again |
| Browser won't load gk-central | `https://` | Use `http://` — no TLS on this port. In the browser's connect dialog, type the card's bolt port yourself |
| `authentication failed` | Password rotated | Function 3 |
| `Database 'graph.db' is unavailable` | gk_central's Neo4j needs a restart | Email Guanming; nothing to fix locally |
| Queries work, `get_neo4j_schema` fails | APOC missing (`test` reports it) | Tell Guanming. Meanwhile `CALL db.labels()` and `CALL db.relationshipTypes()` via the read tool |
| Server shows *failed* in `claude mcp list` or Desktop | Launcher not installed, password not stored, or not configured | Fix what `status` reports; `test` confirms |
| Tools missing in a session | Session started before `enable`, or Desktop closed rather than quit | New Claude Code session; fully quit and reopen Desktop |
| A write tool is listed | `--read-only` missing — only possible if something other than this helper registered the server | `disable <server>`, then `enable <server>` |
| `set-password` says it needs a terminal | Run through Claude or the `!` prompt | Run it in a separate Terminal window |

Still stuck on gk-central: contact Guanming Wu with the exact error and your OS.
Port and firewall questions go to Adam Wright and Joel Weiser at OICR.

---

## Notes

- **Windows and Linux:** there's no Keychain, so the password goes in
  `~/.config/reactome/mcp/secrets/gk-central` (Windows: under `%USERPROFILE%`),
  relying on your user profile's permissions. Claude Desktop's config is at
  `%APPDATA%\Claude\claude_desktop_config.json` on Windows. Commands are otherwise
  the same. The Windows path is less tested — report problems as a GitHub issue.
- **Plain-text transport.** The gk-central ports are http and unencrypted bolt, so
  the password crosses the network unencrypted whichever client you use. That's a
  property of the interim server, and one reason for the planned https endpoint.
- **Pinned versions:** `mcp-neo4j-cypher==0.6.0`, and `ols-mcp-server` at commit
  `4f22ed7`, set at the top of `reactome_mcp.py`.
