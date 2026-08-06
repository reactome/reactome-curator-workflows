# Anthropic API Key & Org-Billing Best Practices

A short primer for anyone administering or using the **Reactome** Anthropic API
organization (the API Console at `console.anthropic.com`) for Claude Code and the
skills in this repo. Reactome runs as a **Claude Console API organization** billed
against a prepaid credit balance ("consumed with API, Claude Code, and Workbench
usage") — *not* a Claude.ai Team/Enterprise subscription. This guide covers how to
manage that setup safely and predictably.

> **Scope note.** This is about the API org and API-key billing. It is *not* about
> Claude.ai Pro/Team/Enterprise subscriptions. Some subscription-only features (e.g.
> Claude Code **Remote Control**) are **not available** with API-key access — see
> [Remote Control & API keys](#remote-control--api-keys) at the end.

---

## TL;DR — the seven rules

1. **Separate work with Workspaces** — one per purpose, each with its own limits and keys.
2. **One key per person or service** — never share a single key across curators.
3. **Set spend limits *before* handing out keys** — plus threshold email alerts.
4. **Keep keys out of code** — env vars or a secrets manager; never commit a key.
5. **Rotate on a schedule and on events** — quarterly, and immediately on exposure/departure.
6. **Keep the admin set small and roles least-privilege** — review membership each release.
7. **Watch usage and cut cost at the source** — prompt caching and the Batch API.

---

## 1. Use Workspaces to separate concerns

Workspaces are isolated environments inside the org, each with its own **spend limit,
rate limit, API keys, and members**. Don't run everyone off one default key.

Suggested Reactome layout:

| Workspace | Purpose | Who |
|---|---|---|
| `curation-claude-code` | Interactive Claude Code + repo skills | Curators |
| `release-scripts` | Batch/automation (DOI XML, QA trackers) | Release team |
| `experiments` | Ad-hoc / evaluation work | Anyone, low cap |

Benefits: a runaway session in one workspace can't drain the whole org, and usage is
attributable per workspace at a glance.

## 2. One key per person or service — never shared

Issue each curator (or each machine/service account) their **own** key inside the
relevant workspace.

- Shared keys can't be attributed to a person and can't be revoked individually.
- When someone leaves, or a laptop is lost, you revoke just their key — no disruption
  to anyone else.
- Anthropic shows the **full key only once** at creation. Capture it then; if lost,
  create a new one (you can't re-display it).

## 3. Set spend limits *before* handing out keys

This is the single most important control for a research org on prepaid credits.

- Set a **monthly spend limit per workspace** as a hard backstop.
- Enable **email alerts** at daily/monthly thresholds so surprises arrive as a
  "$200 spent" email, not a drained balance.
- Start conservative; raise limits as you learn real usage.

## 4. Keep keys out of code and out of this repo

- Store the key in each user's shell environment or a secrets manager:

  ```bash
  # ~/.zshrc  — per user, never committed
  export ANTHROPIC_API_KEY=your-key-here
  ```

- **Never** put a key in a committed file, a skill, a script, or a screenshot.
  This repo is cloned by many curators — a leaked key there is a leaked org balance.
- If a key is ever exposed (pasted in a PR, a log, a chat), **revoke and rotate it
  immediately** — exposure, not misuse, is the trigger.

## 5. Rotate keys on a schedule and on events

- **Scheduled:** rotate quarterly. This aligns naturally with Reactome's ~3–4
  releases per year, so make it part of the release checklist.
- **Event-driven:** rotate immediately on suspected exposure, or when a curator with
  a key leaves the project.
- Because keys are per-person/per-workspace, rotation has a small blast radius —
  one person re-exports one env var.

## 6. Roles and membership

- Keep the set of **org admins** small (a primary + one backup).
- Give curators the **least role** that lets them do their work.
- **Review the member list each release cycle** and remove anyone no longer active.

## 7. Watch usage — and cut cost at the source

- Check the **usage dashboard per workspace** monthly; investigate anomalies early.
- The two biggest cost levers:
  - **Prompt caching** — up to ~90% off repeated input tokens. Relevant here because
    several skills reload the same large context (Curator Guide, Data Model Glossary,
    naming-rule files) every run.
  - **Batch API** — 50% off for asynchronous, non-interactive workloads.
- For interactive Claude Code, **model choice** is the main dial — match the model
  to the task rather than defaulting to the most expensive one for everything.

---

## Recommended starting configuration for Reactome

1. Create a **`curation-claude-code`** workspace; move curator activity into it.
2. Set a **monthly spend cap + threshold alert email** to the admin on that workspace.
3. Issue **per-curator keys** in that workspace instead of one shared org key.
4. Add key rotation to the **release checklist** (quarterly).
5. Keep the "keys go in your shell env, never committed" rule visible to every
   curator who clones this repo (this file, plus the note in `README.md`).

---

## Remote Control & API keys

Claude Code **Remote Control** (drive a local session from claude.ai/code or the
mobile app) requires a **Claude.ai Pro/Max/Team/Enterprise subscription** login. It
**does not work with API-key access**, and it cannot be billed to the API-credit org
— it's a different product on the subscription side.

If you need remote/browser access while keeping API-key billing, run the `claude` CLI
on a machine and reach it over the web instead — e.g. **ttyd/Wetty + tmux** behind a
**Tailscale** network or **Cloudflare Tunnel**, **code-server** (VS Code in the
browser), or a cloud dev environment (Codespaces/Gitpod/Coder). All of these preserve
API-key billing because the process still authenticates with `ANTHROPIC_API_KEY`
(which Claude Code prioritizes over any subscription).

---

## References

- Workspaces — Claude Platform Docs: <https://platform.claude.com/docs/en/manage-claude/workspaces>
- Workspaces in the Anthropic API Console (blog): <https://claude.com/blog/workspaces>
- Continue local sessions with Remote Control — Claude Code Docs: <https://code.claude.com/docs/en/remote-control>
- Anthropic API pricing & optimization: <https://www.finout.io/blog/anthropic-api-pricing>

---

*Maintained alongside the Reactome curator workflows. Questions: open a GitHub issue.*
