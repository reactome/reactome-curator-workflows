# Running Reactome Curator-Workflow Skills as a Team

Draft for discussion. Captures the questions, trade-offs, and possible conventions for
letting a team of curators run these Claude Code skills consistently — with the right
settings, tidy outputs, and documentation that stays in sync.

---

## 1. Why this document exists

Claude Code skills are easy to *write* but have a few non-obvious rules about how they are
*discovered, configured, and run*. When several people share one GitHub repo of skills,
those rules create four recurring problems:

1. **Discovery** — Claude Code only finds skills in specific locations, tied to the directory
   you launch it from.
2. **Runtime requirements that don't travel with the repo** — network allow-lists, MCP
   servers, and Python libraries a skill needs to actually run.
3. **Output hygiene** — where the files a skill generates end up (and whether they pollute
   the git repo).
4. **Documentation drift & precedence** — the same skill is described in several `.md`
   files, and `CLAUDE.md` is always loaded and can override a `SKILL.md`.

---

## 2. How Claude Code loads things (the mechanics everyone needs to know)

| Thing | Where it's read from | When | Notes |
|---|---|---|---|
| **Skills** | `<launch-dir>/.claude/skills/` and `~/.claude/skills/` | discovered at launch | Does NOT scan sibling dirs or descend into nested repos. Only the skill's `name`+`description` sit in context; the full `SKILL.md` body loads **on invocation** (progressive disclosure). |
| **`CLAUDE.md`** | `<launch-dir>` (project root) + `~/.claude/CLAUDE.md` | auto-loaded at launch, **always in context** | Treated as standing instructions; can **override** default behaviour. Heavier than a README. |
| **`settings.json`** | `<launch-dir>/.claude/settings.json` + `~/.claude/settings.json` | auto-loaded at launch | Holds permissions / host allow-lists (e.g. the eutils rule). |
| **MCP servers** | user-level config (there is **no** `.mcp.json` in this repo) | per user | Not part of the repo — each person configures their own. |

**Consequence:** whether a skill is *found* depends on the launch directory (or `~/.claude/skills/`);
whether it *runs fully* depends on settings + MCP + libraries that are partly per-user.

---

## 3. What travels with the repo vs. what each user must set up

| Travels with the repo (zero per-user setup, works when launched **from the repo**) | Does NOT travel — per-user setup |
|---|---|
| The skills (`SKILL.md` + companion files) | **MCP servers** (`gk-central-remote`, `ols`, `reactome`) — user config |
| `.claude/settings.json` → `WebFetch(domain:eutils.ncbi.nlm.nih.gov)` permission | **Python libs**: `openpyxl` (xlsx output), `pypdf` (read uploaded PDFs) |
| `CLAUDE.md` (auto-loaded when launched from repo) | Running **outside** the repo: replicate the eutils permission into `~/.claude/settings.json` and symlink skills into `~/.claude/skills/` |

> Note: the eutils permission is `WebFetch(domain:…)`. A skill that calls E-utilities via Bash
> `curl` instead of WebFetch is governed by **Bash** permissions, not this rule — document per
> skill which mechanism it uses, and allow-list accordingly.

---

## 4. Three ways to run the skills — pros & cons

### Option A — Launch from the repo root *(simplest)*
`cd ~/…/reactome-curator-workflows && claude`

| Pros | Cons |
|---|---|
| Skills found with zero setup | **Outputs land in the git working tree** (clutter, accidental-commit risk) |
| eutils permission + `CLAUDE.md` load automatically | Loads the full `CLAUDE.md` into context every session (even for unrelated skills) |
| Nothing to symlink | No natural per-skill/per-task output separation |
| Easiest to document for non-technical curators | Repo is meant for *code*, not data (see repo "What This Repo Is Not") |

### Option B — Symlink skills into `~/.claude/skills/`, launch from per-project folders *(recommended power-user)*
`ln -s …/reactome-…/.claude/skills ~/.claude/skills` (whole dir) **or** one symlink per skill.

| Pros | Cons |
|---|---|
| Run from any working folder → **outputs stay with the project**, not the repo | One-time setup (symlink + replicate eutils permission into `~/.claude/settings.json`) |
| No repo `CLAUDE.md` bloat | Per-user, not captured by `git clone` alone |
| Per-project **session history** (`~/.claude/projects/<dir>/`) | Whole-dir symlink means `~/.claude/skills` is *only* this repo (can't mix other user skills) |
| Whole-dir symlink → **new skills auto-appear** after `git pull` | Individual symlinks → must add one per new skill |

### Option C — Per-project symlink into each working folder's `./.claude/skills/`
| Pros | Cons |
|---|---|
| Scopes each working folder to just the skill it needs | Most manual (symlink per folder) |
| Outputs stay with the project | Same per-user settings caveats as B |

**Suggested default:** Option A for casual/occasional use and onboarding; Option B for anyone
running skills regularly or producing outputs they need to keep organised. *(Team to confirm.)*

---

## 5. Output hygiene — how serious is the repo-root problem?

Running from the repo root (Option A) drops every generated file (`*_reactions.xlsx`, reports,
scratch notes) into the git working tree. Severity:

- **Real, but manageable.** Risks: cluttered `git status`, accidental commits of data,
  merge friction if several people do it, and it violates the repo's own "not a place for raw
  data files" principle.
- **Mitigations (in order of cleanliness):**
  1. **Run from an external per-project working dir (Option B/C)** — cleanest; outputs never
     touch the repo.
  2. **`.gitignore`** the output patterns (e.g. `*_reactions.xlsx`, `*_reactions.csv`,
     `*-session-progress.md`, `*_curation_report.xlsx`) so they can't be committed accidentally.
  3. **Convention:** skills write to a per-run subfolder (e.g. `outputs/<pathway-slug>/`) rather
     than the current dir — keeps runs separate even within one working folder.

*Team decision:* adopt (1) as the recommended practice **and** add (2) as a safety net.

---

## 6. Pre-run requirements check ("preflight")

**Problem:** a curator can invoke a skill without `openpyxl`, without the MCP servers, or from a
directory where the eutils permission isn't loaded — and only discover it mid-run.

**Proposal:** every skill begins by confirming prerequisites with the user before doing work,
e.g.:

> **Preflight — confirm before I start.** This skill needs: (1) launched from the repo root
> *or* skills symlinked into `~/.claude/skills/`; (2) `WebFetch(domain:eutils.ncbi.nlm.nih.gov)`
> permission (repo `settings.json`, or your `~/.claude/settings.json`); (3) `openpyxl` and
> `pypdf` installed; (4) MCP servers X/Y **only if** using the database cross-check.
> Reply "ready" to proceed, or ask me for setup help.

Trade-off: adds one confirmation step. Keep it lightweight (a single acknowledgement), and let
"ready" skip it. **Recommendation:** yes — bake a short preflight into each skill.

---

## 7. Skill-building SOP additions (for curators authoring skills)

Every new skill's `SKILL.md` should include:
- **A "Preflight / Requirements" block** (§6) listing local prerequisites and the exact fixes.
- **An explicit list of runtime dependencies** (libraries, MCP servers, allow-listed hosts) so
  they can be added to the team setup doc and, where possible, to `.claude/settings.json`.
- **An output convention** (where files are written; per-run subfolder).
- **A doc-sync note** (§8): which other files must change when this skill changes.

Add this checklist to the repo's existing "Adding a New Skill" section in `CLAUDE.md`/README.

---

## 8. Documentation & precedence hygiene

**The drift problem:** this protocol/skill is currently described in up to four places —
`SKILL.md`, the skill's `README.md`, the top-level `README.md`, and `CLAUDE.md`. We already hit
this: the ten-step PMID protocol was updated to NCBI E-utilities in `SKILL.md` but still reads
"web search" in the READMEs.

**The precedence problem:** `CLAUDE.md` is **always loaded** and can **override** behaviour;
`SKILL.md` loads on invocation. If they disagree, you have two competing instruction sources and
no guaranteed winner.

**Recommendations:**
1. **Single source of truth = `SKILL.md`.** Operational detail (protocols, formats, column specs)
   lives there and nowhere else.
2. **Trim `CLAUDE.md` to an index** — one line per skill (name, when to use, "see
   `.claude/skills/<name>/SKILL.md`"). This removes always-on context bloat, eliminates the
   precedence conflict, and stops duplication.
3. **READMEs are human-facing summaries** — keep them short and link to the `SKILL.md`; don't
   re-embed the full protocol.
4. **Change checklist:** when a skill changes, update in this order — `SKILL.md` (authoritative)
   → skill `README.md` summary → top-level `README.md` blurb → `CLAUDE.md` index line + version
   history. A PR touching a `SKILL.md` should be reviewed for these.

---

## 9. Decisions the team needs to make

1. **Standard run mode** — Option A (repo root) as default, Option B (symlink + per-project) for
   regular users? Document both.
2. **Output policy** — adopt external working dirs + `.gitignore` safety net? Standard output
   subfolder convention?
3. **Preflight** — add a required prerequisites check to every skill (and to the SOP)?
4. **`CLAUDE.md` sl-imming** — reduce it to an index and make `SKILL.md` authoritative?
5. **MCP-dependent features** — the database cross-check / ontology / participant-ID diff are
   deferred (they need MCP servers). Decide if/when they become part of a skill, and document the
   MCP prerequisites prominently if so.

---

## 10. One-time per-user setup (reference — Option B)

```bash
# 1. Expose the skills globally (whole-dir symlink → new skills auto-appear after git pull)
ln -s ~/Developer/reactome-curator-workflows/.claude/skills ~/.claude/skills
#    (or individual: ln -s …/.claude/skills/<skill> ~/.claude/skills/<skill>)

# 2. Replicate the eutils permission into user-global settings (merge into permissions.allow)
#    ~/.claude/settings.json → "WebFetch(domain:eutils.ncbi.nlm.nih.gov)"

# 3. Install Python libs
pip install openpyxl pypdf

# 4. Configure MCP servers (gk-central-remote, ols, reactome) in user-level Claude config
#    — only needed for the deferred database cross-check features.
```
