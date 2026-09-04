# Running Reactome Curator-Workflow Skills as a Team

Draft for discussion. **Structure:** *Part I* states the problem — why the obvious "run every skill
from the repo root" approach breaks down. *Part II* explains the Claude Code mechanics behind it.
*Part III* proposes the solutions, the process, and the decisions the team needs to make.

> **Status (updated 2026-08-06).** Several proposals in this doc have since shipped and are marked
> **[DONE]** inline: `CLAUDE.md` has been slimmed to an orientation index (§2, §11, §14), the
> `.gitignore` now covers generated outputs (§7, §14), and the PMID "web search vs. E-utilities"
> drift used as the running example (§1.6, §11) has been corrected across `SKILL.md`/READMEs/`CLAUDE.md`.
> The repo now holds **eight** skills — `/curation-build-illustration` was added after this draft and
> introduces a second allowlisted host (`reactome.org`) alongside `eutils.ncbi.nlm.nih.gov`, plus a
> per-request output-directory convention (`illustrations/<slug>/`, git-ignored) that is a concrete
> example of §13's output-convention recommendation. Remaining open items are the governance/CI and
> preflight decisions in §15.

---

# Part I — The problem

## 1. The obvious approach, and why it breaks down

The natural thing for a team is: **clone the repo, launch Claude Code from the repo root, and run
every skill there.** It works — but because this repo is a **grab-bag of unrelated skills bundled
only for shared distribution**, running everything from that one directory is problematic for
several compounding reasons:

1. **Outputs pile up inside the git repo.** Every generated file (`*_reactions.xlsx`, reports,
   scratch notes) lands in the git working tree — clutter, name collisions, merge friction, and
   accidental-commit risk. It also violates the repo's own "not a place for raw data files"
   principle. → *Output hygiene.*
2. **No per-task/per-project separation, and mixed session history.** All work shares one output
   folder and one conversation-history bucket, so you can't tell which run/skill produced what, and
   past sessions are a flat, mixed list. → *Sessions, history, and "projects".*
3. **A bloated `CLAUDE.md` loads on every session** — full descriptions of every unrelated skill,
   irrelevant to whatever single skill you're running, costing tokens and (worse) able to silently
   override the `SKILL.md` you actually invoked. → *§2 below, and Documentation & precedence.*
4. **Runtime requirements don't all travel with the repo.** Python libraries and MCP servers are
   per-machine; the repo's permission settings apply only when you launch from inside the repo.
   → *What travels vs. per-user.*
5. **No safeguard that prerequisites are met before a run** — a curator can invoke a skill missing a
   library, an MCP server, or the eutils permission, and only discover it mid-run. → *Preflight.*
6. **Documentation drifts** across `SKILL.md`, the skill `README.md`, the top-level `README.md`, and
   `CLAUDE.md` (we already hit this: the PMID protocol was updated to NCBI E-utilities in `SKILL.md`
   but still read "web search" in the READMEs — **[DONE]** since corrected everywhere; the risk pattern
   stands even though this instance is fixed). → *Documentation & precedence.*

Underlying all of this is a **discovery constraint** (Part II): Claude Code only finds skills
relative to the directory you launch from — which is *why* people end up running everything from the
repo root in the first place.

## 2. Special focus — the bloated `CLAUDE.md`

`CLAUDE.md` is auto-loaded, **in full**, into context at the start of every session launched from the
repo, and treated as high-authority **instructions** (not documentation). For a repo of *unrelated*
skills this creates a specific problem:

- **It isn't informative for running any one skill.** You invoke one skill; the write-ups for the
  other six are noise. What actually governs the run is that skill's `SKILL.md`, which loads on
  demand anyway. So the per-skill detail in `CLAUDE.md` is pure redundancy at run time.
- **It's actively risky, not just wasteful.** Because it's always in context and phrased as
  instructions, a stale line in `CLAUDE.md` (e.g. "verify PMIDs via web search") can **silently
  override or blend with** the correct `SKILL.md` instruction — there is no rule that makes
  `SKILL.md` win. A stale README only misleads a human; a stale `CLAUDE.md` changes what the model
  *does*.
- **It also dilutes and costs.** Always-on tokens every session, plus attention spent on detail
  irrelevant to the current task.

**The reframe that resolves "is there even a point to it?":** ask *who loads it, and when.* Under the
recommended workflow (run each skill from your own project directory), the repo's `CLAUDE.md`
**doesn't load at all during a skill run** — it loads only when someone launches Claude Code *inside
the repo*, i.e. a **contributor/maintainer editing the skills**, not a curator running one. So its
legitimate role here is a **contributor-orientation file**, not a runtime manual: keep it, but as
*what the repo is + conventions + the "Adding a New Skill" SOP + a one-line index to each skill*, and
move all per-skill operating detail into the `SKILL.md` files. (Concrete recommendations under
*Documentation & precedence*.)

> **[DONE]** `CLAUDE.md` has since been slimmed to exactly this orientation-index form (512→191
> lines). The recommendation below is now the shipped state, not a proposal.

---

# Part II — Why these happen (the mechanics)

## 3. How Claude Code loads things

| Thing | Where it's read from | When | Notes |
|---|---|---|---|
| **Skills** | `<launch-dir>/.claude/skills/` and `~/.claude/skills/` | discovered at launch | Does NOT scan sibling dirs or descend into nested repos. Only the skill's `name`+`description` sit in context; the full `SKILL.md` body loads **on invocation** (progressive disclosure). |
| **`CLAUDE.md`** | `<launch-dir>` (project root) + `~/.claude/CLAUDE.md` | auto-loaded at launch, **always in context** | Standing instructions; can **override** behaviour. Heavier than a README. |
| **`settings.json`** | `<launch-dir>/.claude/settings.json` + `~/.claude/settings.json` | auto-loaded at launch | Permissions / host allow-lists (e.g. the eutils rule). |
| **Session transcripts** | `~/.claude/projects/<encoded-launch-path>/*.jsonl` | written per session | Keyed by launch directory; **local & per-user**, not in the repo. |
| **MCP servers** | user-level config (there is **no** `.mcp.json` in this repo) | per user | Not part of the repo — each person configures their own. |

**Consequence:** whether a skill is *found* depends on the launch directory (or `~/.claude/skills/`);
whether it *runs fully* depends on settings + MCP + libraries that are partly per-user; and how work
is *organised* (outputs, history) is keyed to the launch directory.

## 4. What travels with the repo vs. what each user must set up

| Travels with the repo (zero per-user setup, works when launched **from the repo**) | Does NOT travel — per-user setup |
|---|---|
| The skills (`SKILL.md` + companion files) | **MCP servers** (`gk-central-remote`, `ols`, `reactome`) — user config |
| `.claude/settings.json` → `WebFetch(domain:eutils.ncbi.nlm.nih.gov)` **and** `reactome.org` permissions | **Python libs**: `pandas` + `openpyxl` (xlsx/CSV output). *(No PDF library is needed — uploaded PDFs are read by Claude directly, not a `pypdf`-style import.)* |
| `CLAUDE.md` (auto-loaded when launched from repo) | Running **outside** the repo: replicate the `eutils.ncbi.nlm.nih.gov` **and** `reactome.org` permissions into `~/.claude/settings.json` and symlink skills into `~/.claude/skills/` |

> Note: the host permissions are `WebFetch(domain:…)` for both `eutils.ncbi.nlm.nih.gov`
> (`/extract-reactions`) and `reactome.org` (`/curation-build-illustration`). A skill that calls a
> host via Bash `curl` instead of WebFetch is governed by **Bash** permissions, not this rule —
> document per skill which mechanism it uses, and allow-list accordingly.

---

# Part III — Solutions & process

## 5. The recommended setup (in one place)

The target state that resolves Part I:

- **Expose skills globally** — symlink the repo's `.claude/skills` into `~/.claude/skills` (whole-dir
  → new skills auto-appear after `git pull`), so discovery no longer forces you into the repo.
- **Run each skill from its own per-task project directory** — outputs, session history, and
  instructions stay scoped to that directory.
- **Do the per-user runtime setup once** — replicate the `eutils.ncbi.nlm.nih.gov` and
  `reactome.org` permissions into `~/.claude/settings.json`, `pip3 install --user -r requirements.txt`, configure
  the MCP servers — and re-run after skill updates (driven by committed requirement manifests).
- **Trim `CLAUDE.md` to a contributor index**; make each `SKILL.md` the single source of truth.
- **Give each skill a preflight** that verifies prerequisites on invocation.

The rest of Part III details each piece; open questions are collected under *Decisions the team needs
to make*.

## 6. Run modes — pros & cons

### Option A — Launch from the repo root *(simplest)*
`cd ~/…/reactome-curator-workflows && claude`

| Pros | Cons |
|---|---|
| Skills found with zero setup | **Outputs land in the git working tree** (clutter, accidental-commit risk) |
| eutils permission + `CLAUDE.md` load automatically | Loads the full `CLAUDE.md` every session (even for unrelated skills) |
| Nothing to symlink | No natural per-skill/per-task output or history separation |
| Easiest to document for non-technical curators | Repo is meant for *code*, not data |

### Option B — Symlink skills into `~/.claude/skills/`, launch from per-project folders *(recommended)*
`ln -s …/reactome-…/.claude/skills ~/.claude/skills` (whole dir) **or** one symlink per skill.

| Pros | Cons |
|---|---|
| Run from any working folder → **outputs stay with the project** | One-time setup (symlink + replicate eutils permission into `~/.claude/settings.json`) |
| No repo `CLAUDE.md` bloat loaded | Per-user, not captured by `git clone` alone |
| Per-project **session history** (`~/.claude/projects/<dir>/`) | Whole-dir symlink → `~/.claude/skills` is *only* this repo (can't mix other user skills) |
| Whole-dir symlink → **new skills auto-appear** after `git pull` | Individual symlinks → must add one per new skill |

### Option C — Per-project symlink into each working folder's `./.claude/skills/`
| Pros | Cons |
|---|---|
| Scopes each working folder to just the skill it needs | Most manual (symlink per folder) |
| Outputs stay with the project | Same per-user settings caveats as B |

**Suggested default:** Option A for casual/occasional use and onboarding; Option B for anyone running
skills regularly or producing outputs they need to keep organised. *(Team to confirm.)*

## 7. Output hygiene

Running from the repo root (Option A) drops every generated file into the git working tree.
- **Real, but manageable.** Risks: cluttered `git status`, accidental data commits, merge friction,
  and it violates the repo's "not a place for raw data files" principle.
- **Mitigations (cleanest first):**
  1. **Run from an external per-project working dir (Option B/C)** — outputs never touch the repo.
  2. **`.gitignore`** the output patterns as a safety net. **[DONE]** — the repo `.gitignore` now
     ignores `*.xlsx`/`*.xls`, `output/`, and the `illustrations/` per-request output tree (with an
     exception for committed skill reference spreadsheets under `.claude/skills/**`).
  3. **Convention:** skills write to a per-run subfolder rather than the current dir. **[Partly done]**
     — `/curation-build-illustration` already does this (`illustrations/<slug>/`); the convention is
     not yet uniform across the other skills.

*Team decision:* adopt (1) as recommended practice **and** keep (2) as a safety net (now in place).

## 8. Sessions, history, and "projects" (vs Claude Desktop)

### How sessions & logs work
- A **session = one run of `claude`** (fresh transcript each launch; resume with `claude --continue`,
  `claude --resume`, or `/resume`).
- **Transcripts are keyed by the launch directory** (`~/.claude/projects/<encoded-path>/*.jsonl`,
  where the memory files also live): same dir → one shared history bucket; different dir → separate
  buckets. They are **local & per-user** — not in the repo, not shared.

### Where the "why we changed a skill" record belongs
A transcript captures the reasoning behind a change, but it is **local, ephemeral, per-user, and not
attached to the skill's file history** — the wrong home for durable rationale. Record it in:
- **git commit messages / pull-request (PR) descriptions** (canonical, diff-attached, team-visible),
- a per-skill **`CHANGELOG`** + the version-history table,
- (optionally) **memory files** for your own cross-session continuity — also local.

**Rule: track skill-change rationale in git/PR/changelog, not in session logs.**

### Claude Code's "project" = a working directory
| Claude Desktop | Claude Code equivalent |
|---|---|
| A Project | A working **directory** you launch from |
| Chats in the project | **Sessions** launched there (`~/.claude/projects/<dir>/*.jsonl`) |
| Files in the project | Files **in that directory** |
| Project custom instructions | That directory's `CLAUDE.md` |
| Visual browser of chats/files | The **filesystem** + `/resume` (no sidebar) |

The abstraction exists, but it's **directory-based and filesystem-browsed, not a visual pane.**
Running everything from one directory collapses all "projects" into one — the opposite of Desktop's
separation. **Recovering it:** one working directory per task/project (Option B) gives each its own
outputs, transcript bucket, and instructions. For skill *development*, the natural "project" is the
repo itself (or a clone/worktree), and the shared iteration history lives in **git** — better than
Desktop's per-project chats because it's diff-attached and team-visible. (Still folder/`/resume`
navigation, not a GUI — it recovers the *separation*, not a visual sidebar.)

## 9. Preflight — a per-skill prerequisites check

**Problem:** a curator can invoke a skill without `openpyxl`, without the MCP servers, or from a
directory where the eutils permission isn't loaded — and only discover it mid-run.

**Proposal:** every skill begins by confirming prerequisites before doing work, e.g.:

> **Preflight — confirm before I start.** This skill needs: (1) launched from the repo root *or*
> skills symlinked into `~/.claude/skills/`; (2) the `WebFetch` host permission it uses
> (`eutils.ncbi.nlm.nih.gov` and/or `reactome.org`) — repo `settings.json`, or your
> `~/.claude/settings.json`; (3) any Python libs it needs (`pandas`, `openpyxl`) installed;
> (4) MCP servers X/Y **only if** using the database cross-check. Reply "ready", or ask for setup help.

### Will it fire if nobody reads `SKILL.md`? (yes — that's the point)
When a curator invokes the skill, Claude Code **loads the full `SKILL.md` and executes its
instructions** — so a preflight written as the **mandatory first step** runs automatically on every
invocation. (Precedent: this skill's existing `SESSION OPENING — ALWAYS EXECUTE FIRST` block.)
- **Verify, don't just ask.** The first step can *check* what's checkable (Bash
  `python3 -c "import pandas, openpyxl"`; confirm required MCP tools appear in the tool list) and only
  *ask* for the rest — stronger than trusting memory.
- **Soft gate vs hard gate.** A `SKILL.md` first-step is a reliable **soft** gate (model-followed,
  not guaranteed). For a deterministic **hard** gate, use a Claude Code **hook** — a script that runs
  on invocation and blocks on failure. A hook committed in the repo's `.claude/settings.json`
  **travels with the repo** (covers Option A); a user-global hook covers Option B. (Exact hook
  type/matcher to be confirmed against current hook docs.)
- **Both is viable:** `SKILL.md` preflight everywhere, plus an optional hard-gate hook for
  enforcement.

## 10. Per-user setup (run once, and RE-RUN after skill updates)

**Not truly one-time.** A new or revised skill can add a library, an MCP server, or an allow-listed
host — none of which `git clone`/`git pull` install for you. Run once at onboarding, then **re-run
after pulling skill changes.** Driving the setup script from committed requirement manifests (see
*Skill-building SOP additions*) is what keeps this from being manual monitoring.

**For everyone — any run mode (Option A included):**
```bash
# Python libs the skills need (xlsx/CSV output), pinned in the repo's
# requirements.txt. No PDF library is required — uploaded PDFs are read by
# Claude directly, not via a pypdf-style import.
pip3 install --user -r requirements.txt
#   This already covers the Google API client libraries /admin-drive-readme needs.

# MCP servers (gk-central-remote, ols, reactome) in user-level Claude config
#   — needed for any skill/feature that queries the database or ontologies.
```

**Additional — only if running OUTSIDE the repo (Option B/C):**
```bash
# Expose the skills without launching from the repo (whole-dir symlink → new skills auto-appear)
ln -s ~/Developer/reactome-curator-workflows/.claude/skills ~/.claude/skills
#    (or individual: ln -s …/.claude/skills/<skill> ~/.claude/skills/<skill>)

# Replicate the host permissions the repo's .claude/settings.json already provides:
#    ~/.claude/settings.json → merge BOTH "WebFetch(domain:eutils.ncbi.nlm.nih.gov)"
#    and "WebFetch(domain:reactome.org)" into permissions.allow
```

> The libs + MCP steps are required in **every** run mode (per-machine, never travel with the repo).
> The symlink + user-settings steps are needed **only** when launching from outside the repo.

## 11. Documentation & precedence hygiene

*(Why a bloated `CLAUDE.md` is risky and why it's a contributor doc, not a runtime manual, is covered
in Part I §2. This section is the fix.)*

**The drift problem:** a skill is currently described in up to four places — `SKILL.md`, the skill
`README.md`, the top-level `README.md`, and `CLAUDE.md`. When one is updated and the others aren't,
they diverge (we hit exactly this with the PMID protocol — since reconciled, but the structural risk
remains).

**How/when is `CLAUDE.md` updated?** It's a plain repo file, edited by hand via PR — **nothing syncs
it with `SKILL.md`.** It's *read* automatically every session but *maintained* manually, so it drifts
whenever someone forgets. The fix is to **not duplicate** (index, not copies).

**Recommendations:**
1. **Single source of truth = `SKILL.md`.** Operational detail (protocols, formats, column specs)
   lives there and nowhere else.
2. **Trim `CLAUDE.md` to a contributor index** — one line per skill (name, when to use, "see
   `.claude/skills/<name>/SKILL.md`") plus repo conventions and the "Adding a New Skill" SOP. Removes
   always-on bloat, eliminates the precedence conflict, and stops duplication. **[DONE]** — shipped
   (512→191 lines).
3. **READMEs are human-facing summaries** — short, and link to the `SKILL.md`; don't re-embed the
   full protocol.
4. **Change checklist:** when a skill changes, update in order — `SKILL.md` (authoritative) → skill
   `README.md` summary → top-level `README.md` blurb → `CLAUDE.md` index line + version history. A PR
   touching a `SKILL.md` should be reviewed for these.

### Can Claude auto-update the docs when a skill changes?
Three levels, increasing robustness:
- **On-demand (human-triggered) — available today.** Ask Claude, after editing a `SKILL.md`, to
  update the skill README, the top-level README blurb, and the `CLAUDE.md` index line; can be a
  one-shot `update-docs` command/skill. *Caveats:* relies on remembering to ask, and model edits are
  non-deterministic (may miss a spot / over-summarise / over-reach) → needs review.
- **Automatic (fires without being asked) — needs a hook or CI, not the model.** "Whenever a
  `SKILL.md` changes, update the docs" is executed by the **harness**: a `PostToolUse` hook (which may
  call headless `claude -p …`), or a **git pre-commit hook / GitHub Action** on the PR.
- **Most robust — remove what must be synced.** Lowest error is *not copying*: index + links. For the
  few derived bits (one-line description, index entry), **generate them from the `SKILL.md` YAML
  `description`** and have **CI regenerate + diff**, failing the PR if stale. Deterministic;
  Claude-assisted drafting complements it for prose rather than being trusted for correctness.

**Takeaway:** Claude-assisted sync speeds things up and catches most drift, but it's a *soft* aid —
pair it with a PR review or a CI staleness check for a real guarantee (same soft/hard-gate pattern as
*Preflight*).

## 12. Governance — who revises which files, when, and how they stay in sync

### The core rule: one source of truth
`SKILL.md` is **authoritative** for everything operational; `CLAUDE.md` holds **pointers/index only**;
READMEs are **human summaries that link, not duplicate**. Minimising overlap *is* the primary sync
mechanism — **you can't drift what you don't copy.**

### Who owns / edits what
| File | Purpose | Owner (edits) | Reviewer / approver |
|---|---|---|---|
| `SKILL.md` | Authoritative skill behaviour + preflight/requirements block | Skill author | Maintainer |
| Skill `README.md` | Short human summary; **links** to `SKILL.md` | Skill author | Maintainer |
| Top-level `README.md` | Repo overview + one short blurb per skill | Maintainer | — |
| `CLAUDE.md` | One-line index per skill + repo conventions / "Adding a New Skill" SOP | Maintainer | — |
| `requirements.txt` / MCP + host manifests / `.claude/settings.json` | Runtime deps + permissions | Skill author proposes | Maintainer approves |

### When (the trigger is always a PR to `main`)
- **Add a skill** → new `SKILL.md` + skill `README.md` + `CLAUDE.md` index line + top-level
  `README.md` blurb + requirement manifests.
- **Revise a skill's behaviour** → `SKILL.md` (authoritative) + **bump its version** + changelog;
  update the skill `README.md` summary *only if the summary changed*; touch `CLAUDE.md`/top-level
  `README.md` *only if the one-line description or triggers changed*. (Internal protocol changes
  should NOT require editing `CLAUDE.md` — that's the point of index-only.)
- **Rename / remove a skill** → update the `CLAUDE.md` index line, top-level `README.md`, and any
  symlink guidance.

### How sync is enforced
1. **PR checklist / template** (the change-checklist above) the reviewer must tick.
2. **Version bump + per-skill changelog** so "what changed, and did requirements change" is visible.
3. **Optional CI checks:** (a) every skill dir has a matching `CLAUDE.md` index line; (b) a
   *duplication detector* that fails if canonical text (e.g. the ten-step protocol) appears verbatim
   in more than one file; (c) `SKILL.md` version bumped when files under that skill changed.

### Decision needed
- Name the **maintainer(s)** with merge authority (repo currently lists Marc Gillespie).
- Adopt the ownership table + PR checklist; decide whether to add the CI duplication/version check.

## 13. Skill-building SOP additions (for curators authoring skills)

Every new skill's `SKILL.md` should include:
- **A "Preflight / Requirements" block** listing local prerequisites and the exact fixes.
- **An explicit list of runtime dependencies** (libraries, MCP servers, allow-listed hosts) so they
  can be added to the setup doc and, where possible, to `.claude/settings.json`.
- **An output convention** (where files are written; per-run subfolder).
- **A doc-sync note** (which other files must change when this skill changes).

**Aggregate requirements so setup isn't manual monitoring.** Per-user requirements *evolve* with each
skill, so keep a committed, machine-readable manifest the setup script consumes: `requirements.txt`
(libs), a required-MCP-servers list, and host allow-list entries. A PR that adds or changes a skill
**must** update that skill's Preflight block **and** these manifests, and bump the version. Onboarding
= run the setup script once; after any skill change = `git pull` && re-run it (idempotent). Add this
checklist to the repo's "Adding a New Skill" section.

## 14. Proposed supporting artifacts (build on agreement)

Each is optional and a team decision; all can be **committed to the repo** so they travel with
`git clone` (even when their *effects* — like home-dir symlinks — don't).

| Artifact | What it is | Serves |
|---|---|---|
| **Reusable preflight block** | A short `ALWAYS EXECUTE FIRST` section for every `SKILL.md`, with real *verify* commands and an ask-fallback. | Preflight (soft gate) |
| **`setup-user.sh` + `requirements.txt`** | Idempotent, re-runnable installer: symlink (outside-repo mode), merge eutils permission into `~/.claude/settings.json` without clobbering, `pip install`, and print remaining manual steps (MCP). | Per-user setup |
| **Requirement manifests** | Committed lists the script consumes: libs, required MCP servers, host allow-list. | SOP |
| **Hard-gate hook (optional)** | Hook + check script that blocks invocation on failed prerequisites; repo-committed (Option A) and/or user-global (Option B). | Preflight (hard gate) |
| **Trimmed `CLAUDE.md` (index form)** ✅ **[DONE]** | Reduce to one line per skill + conventions; `SKILL.md` authoritative. | Documentation & precedence |
| **`.gitignore` output-safety block** ✅ **[DONE]** | Ignore generated outputs so repo-root runs can't commit data. | Output hygiene |

**Suggested build order:** (1) trimmed `CLAUDE.md` + `.gitignore` — **[DONE]**; (2) preflight
block + `requirements.txt`/`setup-user.sh` — the propagation backbone (still open); (3) hard-gate hook —
only if soft gating proves insufficient (still open).

## 15. Decisions the team needs to make

1. **Standard run mode** — Option A (repo root) as default, Option B (symlink + per-project) for
   regular users? Document both. *(Still open.)*
2. **Output policy** — external working dirs + `.gitignore` safety net? Standard output-subfolder
   convention? *(Safety-net `.gitignore` **[DONE]**; the per-run-subfolder convention is adopted for
   `/curation-build-illustration` but not yet standardised across all skills — still open.)*
3. **Preflight — and how strong?** Mandatory first-step check in every `SKILL.md` (auto-fires; soft
   gate) that *verifies* rather than asks; optionally enforce with a hook (hard gate). Soft-only, or
   soft + hook? *(Still open.)*
4. **`CLAUDE.md` slimming** — reduce to a contributor index and make `SKILL.md` authoritative?
   ✅ **[DONE]** — implemented (512→191 lines).
5. **MCP-dependent features** — the database cross-check / ontology / participant-ID diff are deferred
   (need MCP servers). Decide if/when they join a skill, and document the MCP prerequisites prominently.
   *(Still open.)*
6. **Supporting artifacts** — which to build, and in what order (see *Proposed supporting artifacts*)?
   *(Trimmed `CLAUDE.md` and `.gitignore` **[DONE]**; preflight block, `setup-user.sh`, requirement
   manifests, and hard-gate hook still open.)*
7. **Governance & ownership** — adopt the ownership table + PR checklist, and optionally a CI
   duplication/version check? Name the maintainer(s). *(Still open; repo lists Marc Gillespie as
   maintainer.)*
