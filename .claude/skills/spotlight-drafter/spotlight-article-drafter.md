---
name: spotlight-article-drafter
description: Draft candidate Reactome "Research Spotlight" articles — both the short (one-paragraph) and expanded/long-form versions — that highlight a published paper's use of Reactome data or tools. Use this whenever Lisa asks to draft, write, or generate a Spotlight article, a "candidate spotlight," a spotlight blurb/summary, or asks whether a paper would make a good Spotlight — even if she just attaches a PDF/DOI and says something like "spotlight this," "is this a good candidate," "write up the long and short versions," or points at a paper found in a journal-scan/candidate deck and asks for the write-up. Also use it when she references the Spotlight tracking spreadsheet, the Spotlight archive, or a "how was Reactome used" slide and wants article text produced from it. This skill only drafts the article text/content — it does NOT do the final HTML/Joomla formatting (use the separate spotlight-to-joomla skill for that, after a curator has approved wording and a publish date).
---

# Reactome Spotlight Article Drafter

## What this produces

Reactome's homepage features one paper per month in a "Research Spotlight" that
highlights an interesting or high-profile use of Reactome data/tools in the
literature. Each Spotlight has two forms, both drafted at once:

- **Short version** — a single, dense paragraph (roughly 80-150 words) for the
  homepage teaser and the permanent Spotlight Archive list.
- **Expanded/long version** — a multi-paragraph piece (roughly 350-550 words)
  giving background, method detail, and broader significance, used when a
  curator wants a fuller writeup (e.g. for a newsletter or the author outreach
  email).

Both are drafts for a curator (Lisa or a colleague) to review, edit, and
schedule — never publish them or contact authors on her behalf.

## Before you start: gather the inputs

You need, at minimum, the candidate paper itself (PDF, DOI, or URL). It's very
common for this to arrive alongside a slide deck or notes that already
identify *how the paper used Reactome* — curators often screen candidates in
batches and record a "How was Reactome used?" summary plus a Pros/Cons
assessment per paper before drafting. Use these notes as a head start, not as
ground truth: treat every factual claim in them (which PMID, which model
system, which figure, which pathway) as a hypothesis to confirm against the
actual paper in Step 1, not a fact to carry forward. Screening is done in
batches from memory or quick skims, so small errors creep in — a transposed
digit in a PMID, a paper misremembered as an animal study when it's actually
cultured cells, that kind of thing — and they're easy to miss if you draft
straight from the notes. If something in the paper doesn't match the notes,
say so plainly in the editorial note (Step 6) and draft from what the paper
actually says.

If the paper is a large PDF, read it in pages (methods and results sections
matter most here — introductions/abstracts alone are rarely enough to write
an honest expanded version).

**When the paper is paywalled or full text won't load:** don't fill the gaps
with inference. Draft from whatever you can confirm — the abstract, any
accessible figures, an open-access preprint version — and treat everything
else (a specific pathway name, a supplementary figure, a citation) as
unconfirmed. Say explicitly, in the editorial note, which claims are
confirmed from primary text and which are reported secondhand (from the
curator's notes, from a search-result snippet, from a summary a research
subagent produced) and haven't been independently verified. A curator can
decide whether to chase down full access; they can't un-trust a draft that
quietly presented an inference as a fact.

## Step 1 — Pin down exactly how Reactome was used

This is the most important step, because it determines what you can honestly
claim in the article. Search the paper (Methods, Results, figure legends, and
supplementary methods) for every mention of "Reactome" and answer:

- **Which Reactome tool/resource?** e.g. pathway overrepresentation analysis,
  GSEA/ReactomeGSA, the Functional Interaction (FI) network/FIViz Cytoscape
  plugin, the Pathway Browser, downloaded Reactome gene sets (.gmt), Reactome
  as one of several interaction/pathway databases feeding a custom network,
  ReactomePA, iPANDA, or something else.
- **What did it contribute to the paper's conclusions?** Was it central to a
  key finding, or a supporting/validation step, or just one of several
  resources used in passing?
- **Are specific named pathways or Stable IDs cited?** If the paper names
  pathways (e.g. "Interferon signaling", "Collagen degradation") you can link
  them; if it only used Reactome as a generic data source (e.g. inside a PPI
  network alongside STRING/BioGRID/IntAct) there may be nothing specific to
  link, and you should not invent a pathway link that isn't in the paper.
  Never guess or fabricate a Stable ID (`R-HSA-...`) or numeric `DB_ID`. This
  applies just as much to an ID that arrives secondhand — from a curator's
  notes, or from a research subagent's summary — as to one you'd make up
  yourself: "plausible-looking" isn't "verified." Only put a pathway link in
  the article once you (or the source you're quoting directly) have actually
  seen that ID attached to that pathway name, e.g. in the paper's own text or
  on reactome.org. If you're not sure, name the pathway in plain text without
  a link rather than guess at the ID.
- **Is Reactome named in a figure or table?** This matters for the curator's
  decision (see Step 5) even though it doesn't change the article text.

Be honest about how central or peripheral the usage was. Reactome's own
archive includes plenty of Spotlights where Reactome was one of several tools
(see `references/examples.md`) — the goal is an accurate description, not an
inflated one. Overstating Reactome's role is the single easiest way to make a
curator distrust the draft.

## Step 2 — Collect the bibliographic facts

Full paper title, first author (+ "et al." if more than ~3 authors, matching
archive convention), journal, and the month/year to cite (the archive
consistently cites the *issue* month, e.g. "August 2026," not the exact online
publication date — check both and prefer the issue/print date if the two
differ). Get the DOI or a stable article URL for linking the title.

## Step 3 — Calibrate style against the archive

Read `references/examples.md` before drafting — it contains full short+long
pairs pulled from Reactome's own Spotlight tracker (the ones where a curator
filled in *both* fields, which are the highest-quality style exemplars). If
you have live access to the tracking spreadsheet
(https://docs.google.com/spreadsheets/d/1F0v7altKbHRCbdDDkJprpYJbol36fbN7DE7W_uS9Qj4)
pull a few recent rows too, since new examples accumulate monthly and reflect
the curators' current preferences. Notice, across examples:

- Short versions open with "In their [Month Year] [Journal] article/paper,
  '[Title],' [Author] et al. ..." and stay to one paragraph.
- Long versions often (not always) open with a background paragraph that sets
  up the problem *before* naming the paper, then introduce the paper and its
  approach, then get specific about the Reactome methodology and findings,
  then close with significance/implications.
- Sentences are dense but plain — no marketing language, no unsupported
  superlatives. Claims are attributed to the study ("the authors show...",
  "Gallop et al. find...").
- Reactome's specific contribution is always named precisely (the tool, the
  pathways, the finding it supported) rather than referenced vaguely as
  "bioinformatics analysis."

## Step 4 — Draft the short version

One paragraph, ~80-150 words. Structure:

1. "In their [Month Year] [Journal] article, [Title](url), [Author] et al.
   ..." — what the paper did/found, in plain terms.
2. How Reactome was specifically used and what it revealed (from Step 1).
3. One closing sentence on the takeaway or broader implication.

Format the title as a markdown link `[Title](url)`, and format any named
Reactome pathway mentions as `[pathway text](Stable ID or DB_ID)` — this
matches the input format the spotlight-to-joomla skill expects downstream, so
a curator can hand your draft straight to that skill once it's approved.
Prefix the draft with a `[Spotlight publish date]` placeholder rather than
guessing a date; a curator assigns that when scheduling.

## Step 5 — Draft the expanded version

350-550 words, several paragraphs, written to stand alone (don't assume the
reader saw the short version). Typical shape:

1. **Background** — the problem or open question the field faced, without
   naming the paper yet (1-2 paragraphs for a general audience).
2. **This paper's approach** — introduce the paper by name/date/journal and
   describe the experimental design at a level a non-specialist reader can
   follow.
3. **The Reactome-specific method and result** — go into real detail here:
   what was fed into Reactome, what algorithm/analysis was run, what it
   returned, and how that supported the paper's conclusions. This is the
   section curators scrutinize most, since it's the actual evidence for
   whether the paper deserves a Spotlight.
4. **Significance** — close with why the finding matters / what it enables,
   generally 1-2 sentences, matching the paper's own stated implications
   rather than adding claims of your own.

Same linking conventions as the short version.

## Step 6 — Add an editorial note for the curator (recommended)

Curators screening candidates track a brief Pros/Cons note before drafting
(see the "How was Reactome used?" pattern in `references/examples.md`).
Include one alongside your draft — it's not part of the published article,
just a decision aid:

- **How Reactome was used** — one or two sentences, the plain-language
  version of Step 1's findings.
- **Pros** — things that make this a strong candidate: profile/recency of the
  journal, how central Reactome was, whether specific pathways can be linked,
  audience relevance.
- **Cons** — things that weaken it: Reactome as one of many tools, no named
  pathways to link, Reactome absent from figures, an older or less
  prominent venue, anything that might make a curator hesitate.
- **Verification flags** — anywhere the paper contradicted the screening
  notes (wrong PMID, wrong model system, etc.), and anywhere you couldn't
  reach full text and had to draft around an unconfirmed detail. Name the
  specific claim and what you'd want a human to double-check, rather than
  a vague "some details unverified."

Don't let this section talk you into softening or inflating the actual
article text above — the article should be accurate regardless of how
promising the Cons list looks.

## Output

Deliver both versions (plus the editorial note) as a single document, clearly
labeled "SHORT VERSION" / "EXPANDED VERSION" / "EDITORIAL NOTES", so a curator
can review, edit, and pick a publish date. If Google Drive access is
available and the curator has an existing "Spotlight candidates" folder,
offer to save the draft there as a Google Doc (matching how these drafts are
normally stored) in addition to sending the file directly. Otherwise, just
deliver the file.

Remind whoever reviews the draft that the next step, once wording and a
publish date are finalized, is the spotlight-to-joomla skill, which converts
the approved short paragraph into the exact HTML block used on the Reactome
website — don't do that conversion yourself as part of this skill.
