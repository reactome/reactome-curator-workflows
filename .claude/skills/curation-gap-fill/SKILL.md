---
name: curation-gap-fill
description: >
  Fill curation gaps from a review paper. Starting from one paper (usually a
  review) and curator-named anchor nodes, propose a NEW Reactome pathway that
  links existing gk_central content and adds only the reactions that have human
  primary evidence. Agents extract candidate events (text and figures), survey
  gk_central, find human primary literature, compare against WikiPathways, KEGG and
  GO, and check every subpathway's event chain for gaps; inference from another
  species is a last resort. The draft is tested against the /review-internal standards,
  round after round, until no HIGH issue remains. Output: a curator-facing DOCX in
  the internal-review style (the decisions first, then the hierarchy, reactions,
  checks and the agents' arguments) and a staging markdown that converts to a
  WebBench "Load staged instances" JSON file. Use for "build a pathway for <topic>
  from this review", "what is Reactome missing for <topic>", "where would <topic>
  fit in Reactome", or "propose a hierarchy around these nodes". To update an
  existing pathway from a new primary paper, use /curation-update-from-paper instead.
  Proposes only; never writes to the database.
---

## ON INVOCATION — PRINT THIS FIRST

Show the curator what this run has to work with. Check which MCP tools are
actually present and say so; never claim a server that is not there.

```
/curation-gap-fill — reference material for this run

In this skill (curation-gap-fill/):
  build_pathway_proposal.py      Renders the proposal DOCX; refuses on a failed PubMed check.
  staging_from_md.py             Staging markdown → WebBench "Load staged instances" JSON.
  pathway_graphics.py            Hierarchy map and per-subpathway chain diagrams.
  compare_resources.py           Comparison against WikiPathways / KEGG (comparison only) / GO.
  render_pages.swift             Renders the paper's figure pages to PNG (PDFKit).
  gtopdb_lookup.py               Guide to Pharmacology ligand IDs from GtoPdb's bulk files.
  reactome_domain_model.json     Class/slot schema the staging converter checks against.
  sample_pathway_proposal_spec.json   Worked example (adipose tissue remodeling).

Shared with /curation-update-from-paper (../curation-update-from-paper/):
  Reactome_RLE_Annotation_Reference_V94.md, Curator_Guide_V94_Extract.md,
  resolution_queries.md, data_model_slots.md, ptm_prefixes.md,
  build_update_doc.py, reaction_graphic.py, verify_references.py

Live servers:
  gk-central   <present/absent>  Existing events, entities, placement, release status.
  ols          <present/absent>  Confirms every GO / ChEBI / CL term before it is written down.

Inputs: the paper (PDF preferred: its figures are read too), and your anchor
nodes (existing ST_IDs you think matter). Optional: a release label and a scope steer.
```

# Curation Gap Fill
Version 1.0 (piloted 2026-11-06 on Drareni & Seale, *Science* 394:618, "When fat
adapts", which became the adipose tissue remodeling proposal).

`/curation-update-from-paper` updates a pathway that exists, from a new primary
paper. This skill starts from **one paper, usually a review, and no pathway**. It
works out what Reactome already holds for the topic, proposes a hierarchy built
around anchor nodes the curator names, fills the gaps with reactions only where human
primary evidence supports them, and tests the draft against the
`/review-internal` standards until no HIGH issue remains.

**Proposes only. Never writes to gk_central.** The staging file it produces is
loaded by the curator, in WebBench, after reading the proposal.

---

## What it produces

All files go in `output/<topic-slug>/`, which is gitignored. Never write into the repo.

| File | Purpose |
|---|---|
| `<Topic>_proposal.docx` | The curator-facing proposal, in the internal-review look (navy banners, priority colours) **without** reviewer instructions. Ordered so the curator gets the decisions first and then descends by the table of contents: executive summary (at a glance, **Primary Curator Decisions**, assessment, summary) → Contents → how to use → visual reference (source figures) → 1 hierarchy (map, tree, topology) → 2 proposed reactions (chain diagrams, reaction tables) → 3 placement → 4 topology checks and design logic (class and disease, resource comparison, chain continuity, design principles) → 5 entities → 6 literature → 7 how it was built (the agents' arguments) → 8 internal review → 9 open questions → WebBench appendix. |
| `<topic>_staging.md` | Every NEW instance, one block each, in the staging format below. The curator edits this after reading the DOCX. |
| `user-instances-<topic>.json` | `staging_from_md.py` output: the file WebBench's **Load staged instances from a local file** button accepts. |
| `proposal_spec.json` | Everything the DOCX shows; re-render with `build_pathway_proposal.py`. |
| `agents/` | Every agent's JSON and MD per round, plus `construction_log.json`. |
| `drafts/` | The DOCX of each round (v1, v2, ...), so the curator can see what changed. |

---

## STEP 0: Ask for the anchor nodes (required)

Before any agent runs, ask the curator:

> Which existing Reactome events (ST_IDs) do you think matter for this topic,
> as places to reorganise or include? Any scope limits?

Resolve each anchor in gk_central. Report its class, its full lineage to the
TopLevelPathway, its size (number of RLEs) and whether it is released. **Anchors
are often pathways, not reactions**, and sometimes a whole branch: in the pilot
all four were pathways, and one was *Metabolism of lipids* (997 RLEs). Say so
before building. An anchor can become a shared child, a source of individually
linked events, or context only. That choice is recorded and offered to the
curator, never made silently.

Also settle the working directory and an optional release label, as
`/review-internal` does.

---

## The agents

Use the Agent tool. Launch independent agents in one message so they run
concurrently. Every agent writes JSON plus a digest of one page or less to `agents/`, and
reports back in under 300 words. The orchestrator (you) assembles, verifies and
arbitrates; it never takes an agent's claim on trust where a query can check it.

| Agent | Round | Job | Must not |
|---|---|---|---|
| **paper-extraction** | 0 | Every claim in the paper, verbatim, with printed page and figure, **including what the figure images themselves show** (render the figure pages to PNG first, see "The paper's figures"), bucketed CURATABLE / GROUPING / SUMMATION_ONLY under the data-model rule (an RLE is a change in participants or compartments). Molecular reading, likely class, species as stated in the review, and how each claim relates to the anchors. Also the paper's reference list. | look up PMIDs or query the database |
| **gk_central (survey)** | 0 | The anchors in full; the existing content for the topic, released and unreleased (unreleased content is colleagues' work in progress, so name the owners); existing events and entities per key molecule, with "none found" stated explicitly; TopLevelPathway list; how common multi-parent placement is; a placement recommendation. Every query recorded in `queries_run`. | write anything |
| **literature** | 1 | Resolve the paper's reference list to PMIDs (primary or review, and the experimental system). Then for each target event find up to 3 primary papers, preferring human systems, with a verbatim abstract sentence. Verdict per target: HUMAN_DIRECT / HUMAN_INDIRECT / NONHUMAN_ONLY / NONE_FOUND. Disagree with the extraction reading where the literature does. | take a PMID from anywhere but E-utilities |
| **gk_central (resolution)** | 1 | Exact dbId, stId, class and displayName for every event to reuse; RESOLVED / AMBIGUOUS / JUDGEMENT per entity (`../curation-update-from-paper/resolution_queries.md`), with branch-usage tiebreaks; compartments, species and GO instances; disagreements with the draft hierarchy, on database grounds. | assume an entity matches without filtering on name, compartment and species |
| **comparison** (optional, **on by default**) | 1, after the gk_central survey | Run `compare_resources.py` with the proposal's genes per subpathway (gk_central query over every participant of each linked pathway and reaction, plus the new reactions' genes). Then judge the differences as themes: LINK_PATHWAY, CLOSES_CHAIN_GAP, NEW_CANDIDATE (with one verified human PMID), COVERED_ELSEWHERE or OUT_OF_SCOPE. At most about 12 actionable themes. | copy KEGG content into the proposal; draft reactions |
| **internal review** | 2, 3 | Test the draft (see "The review loop"). Resume the same agent for later rounds with SendMessage, so it checks its own earlier findings. | edit the proposal |

### The paper's figures are evidence, not decoration

Text extraction reads only figure legends and scattered label text. Render the
figure pages as images and **look at them**: a schematic often states an ordered
chain that the text spreads over several paragraphs. In the pilot, Fig. 2B drew
"PLIN1 (P) → ABHD5 release → ATGL & HSL activation → TG-droplet hydrolysis", the
exact chain that new reactions E1 and E2 complete.

```
swift render_pages.swift <paper.pdf> <outdir> 3 <page> [<page> ...]   # PDFKit, no install
sips -c <h> <w> --cropOffset <y> <x> page<N>.png --out figures/figN.png
```

`render_pages.swift` ships in this directory; it uses PDFKit to draw each page at the given scale. Give the extraction agent the
images and have it record, for each candidate event, the figure panel that shows it.
Put the cropped figures in `figures/` and list them in the spec's `source_figures` as
`{file, label, caption, supports, credit}`. They render in Section 1 under
"Visual Support from the Source Paper", and each reaction table carries a "Source
paper figure" row. The credit line must state the copyright holder and "reproduced
for internal curation review only". Figures never go into the staging file or Reactome.

### Comparison with other pathway resources (on by default)

A review covers what its authors chose to discuss. WikiPathways, KEGG and GO show
what the field's other models contain, and the difference is a cheap check for
missing topology. In the pilot, KEGG and WikiPathways both showed natriuretic
peptide-stimulated lipolysis, which the review never mentions.

```
python3 compare_resources.py agents/proposal_genes.json \
    --wp-query "adipocyte,lipolysis,thermogenesis,..." --kegg hsa04923,hsa04714 \
    --go GO:0019433,GO:0019915 -o agents/comparison_resources.json
```

- **Sources and terms.** WikiPathways (CC0) and GO annotations (CC BY 4.0) are open.
  KEGG is used through its REST API as a **comparison only**: cite "compared
  against KEGG hsa04923", never copy its content, and keep the KEGG notice that
  `compare_resources.py` writes. No accounts are needed; downloads are cached in
  `~/.cache/reactome-curator-workflows/compare/`.
- **Input.** Gene symbols per subpathway, taken from gk_central over every participant
  (inputs, outputs, catalysts, regulators, complex components, set members) of
  each linked pathway and reaction, plus the new reactions' genes. The
  comparison is only as good as this list. Linked pathways count as covered.
- **Judging.** The raw output is large (809 absent genes in the pilot). The
  comparison agent groups the genes into themes and classifies each one, preferring
  existing Reactome pathways (the reuse order applies). Themes that close a chain
  gap are fed into the chain-continuity check. LINK_PATHWAY themes are linked when
  the curator's policy allows it. NEW_CANDIDATE themes become LOW open questions,
  never new reactions without the usual literature and review steps.
- **Report.** Spec key `comparison`: `{intro, themes[], notice}`. It renders as
  "Comparison with Other Pathway Resources" in Section 1, every theme shown with
  its outcome, including the excluded ones and why.
- **Cost.** About 100–200 k tokens for the agent, running in parallel with the literature
  agent, so it adds no wall-clock time. Turn it off when the curator says so ("no
  comparison"); the report then states that it was not run.

Between Round 0 and Round 1 the orchestrator spot-checks the survey's biggest
claims, writes `agents/hierarchy_v0.md` for the Round 1 agents to share, and
starts the construction log. In the pilot the spot check caught the survey
agent saying ATGL was never a TAG lipase; R-HSA-1482777 says otherwise. The real
gap was narrower: ATGL at the lipid droplet.

**PMID verification stays with the orchestrator** (as in `/curation-update-from-paper`). After the
literature agent reports, re-fetch every PMID you will use from ESummary yourself,
compare it with the agent's claimed first author and year, and build every
citation string from the PubMed record, not from the agent's text.

---

## Assembling the draft: rules the pilot settled

These are the decisions the review loop forced. Apply them from the start.

**Which events become new reactions.** Only those with primary evidence. When
the curator asks for human support, admit purified human protein, human
receptor reconstitution, human primary cells and human adipocyte (or other
cell-type) lines. Mark in-vitro reconstitution as such. Association studies,
knockdown phenotypes and mouse-only mechanisms go into summations or the
excluded list, each with its reason. A preprint is never a literatureReference.
A review supports pathway summations only.

**Contested human data stays neutral.** When human studies disagree (the pilot:
which beta-adrenergic receptor drives human brown fat), link all the existing
alternatives and say so in the summation. Never curate the review's preferred
answer as settled.

**Reuse order (curator policy).** (1) Link an existing **pathway** whole, as a
subpathway of the new pathway. (2) Only where the parent pathway is mostly
unrelated, link the single **reaction**, and say why: give the parent's size and how
many of its reactions are relevant. (3) Reuse existing **entities** always. Have the
gk_central agent check, for every reaction you plan to share, its parent
pathways and their relevance. In the pilot this replaced 10 individually shared
reactions with 7 linked pathways. Section 2's table carries a "Reuse level" column.
The Curator Guide's rule still applies: a reaction's precedingEvent must be a
reaction, never a linked pathway.

**Sharing existing content (new-only staging).** The staging file creates only
new instances. A new Pathway's `hasEvent` lists existing events or pathways as
shells, so they gain a second parent and nothing released is edited (174 human
pathways already have more than one parent). Moves, removals and new
`precedingEvent` links on existing events are open questions for the curator.
`updatedInstances` is never staged: it needs every attribute of the existing
instance, and a stale copy could overwrite a colleague's edits when committed.

- **Never share the same thing twice in one tree.** Before linking, check the
  candidate's lineage. If it already sits under the proposed parent (for
  example under a sibling pathway), or inside another pathway you are linking,
  cross-reference it in a summation instead. The pilot shared a PPARG event that
  was already under Adipogenesis; the review caught it (D21).
- **Link a pathway whole when a partial share breaks a chain.** Sharing six of
  seventeen Triglyceride catabolism events left the HSL reactions with no event
  making their catalyst. Linking the pathway whole fixed it without editing it (D22).
- **Don't link a whole large branch** under a tissue or topic pathway (the pilot:
  *Metabolism of lipids*, 997 RLEs). Link its relevant children.
- **New events reuse the exact participant instances** of the neighbouring
  existing events, so that they chain. Use branch-usage tiebreaks for duplicates
  (three LCFA [cytosol] instances share one ChEBI ID).

**Chain continuity, and inference from other species as a last resort.** For each
subpathway, lay out the intended chain and check every consecutive step against
gk_central: is it connected by a shared entity instance or a precedingEvent?
Classify each step as FILLED_BY_EXISTING, NEEDS_HUMAN_EVIDENCE,
INFERENCE_CANDIDATE or NOT_A_BREAK, and render the table in Section 1 (spec
`chain_gaps` and `chain_intro`). Then:

- Fill gaps with existing content first, at the highest reuse level.
- Then with new human-evidence reactions. If the evidence is less direct (for
  example, a reporter readout plus the canonical mechanism), set `evidenceType`
  to an existing ECO EvidenceType and state the rationale in the summation; the
  Guide requires both. In the pilot, E6 used ECO:0005548 (#9833236).
- **Only if** the gap breaks a chain the proposal depends on, and only
  non-human evidence exists: build the reaction in the experimentally supported
  species (non-human gene symbols in initial capitals, e.g. Jak2), then the human
  reaction with human participants and `inferredFrom` pointing at it ("Creating an
  inferred event", Curator Guide). Never build a non-human pathway to infer
  from. Stage both, with event status `INFERENCE_SOURCE` and `INFERRED`; the
  reaction table adds "Inferred from" and "Evidence type (ECO)" rows. In
  gk_central, 2,653 human reactions are manually inferred, mostly with
  evidenceType empty; follow the Guide and fill it anyway.
- Mouse-only mechanisms that would only **add** to the pathway, rather than
  repair a chain, are not inferred. They go to the open questions.

**Cell type.** Use the Cell Ontology through existing gk_central instances. The current
convention is `participantCellType` on the reaction, pointing to a
PhysicalEntityCellType wrapper (`physicalEntity` + a `cell` Cell instance; displayName
"<entity> in <cell>"). Do not create cell-tagged copies of entities: that is the
older convention, and it breaks entity chains. Set it where the evidence places
the reaction in a cell type. Otherwise the reaction table's "Cell type" row says
why it is not set (no fitting Cell instance, or the cell type is unresolved).

**Event class and disease status: assess and record them explicitly.** For every
new reaction-like event, consider each class in the data model (Reaction,
BlackBoxEvent, Polymerisation, Depolymerisation, FailedReaction,
CellDevelopmentStep). For every new pathway, consider Pathway, TopLevelPathway and
CellLineagePath. Record the chosen class, why, and why each other class was ruled out
(`class_assessment: {chosen, why, ruled_out{}}`). Record disease status for every
new event and pathway (`disease`). **Disease status follows the biology
represented**: a disease-state participant, an altered or failed function
(FailedReaction, with normalReaction and entityFunctionalStatus), or a disease slot.
**A drug participant does not decide it**: drug-binding reactions modelled on
existing ones (e.g. R-HSA-9611839, R-HSA-9728664) are normal events, and a drug
entity's indication is not the event's disease. Also check that no linked existing
pathway or reaction is, or contains, a disease event. `--validate` refuses a spec
without these fields. They render as the "Event Class and Disease Assessment"
table in Section 1, and as the Class and Disease event rows of each reaction table.

**Every new instance is checked for an existing equivalent**, including
LiteratureReference by `pubMedIdentifier`, complexes, drugs and Summations. The
pilot staged three LiteratureReferences that already existed (D20).
`make_spec`-style builders take an `existing_litrefs` map; query all PMIDs in one
Cypher call:

```cypher
MATCH (l:LiteratureReference) WHERE toString(l.pubMedIdentifier) IN $pmids
RETURN toString(l.pubMedIdentifier), l.dbId, l.displayName
```

**GO BP.** Confirm every term in OLS and find its gk_central instance (by
`identifier`, without the `GO:` prefix). A subpathway must not carry the same
term as a pathway it links as a child; check usage with
`MATCH (p:Pathway)-[:goBiologicalProcess]->(g {identifier:$id})`. Then move up
to a parent term (OLS `get_term_ancestors`). The name and the top-level term
should describe what the members actually are: excluding every phenotype claim
can leave a "remodeling" pathway with no remodeling events (D26). Offer the
curator a choice when that happens.

**Drugs** follow the class of their closest existing analogue (tirzepatide
followed semaglutide: ProteinDrug, extracellular region, a Guide to
Pharmacology ReferenceTherapeutic, a ChEBI cross-reference, and a disease slot).
Resolve the Guide to Pharmacology ligand with `gtopdb_lookup.py`:

```
python3 gtopdb_lookup.py tirzepatide          # by name, INN or brand synonym
python3 gtopdb_lookup.py --chebi CHEBI:65349  # by ChEBI
```

By default it uses GtoPdb's versioned bulk download files, which need no
account. They are cached in `~/.cache/reactome-curator-workflows/gtopdb/<version>/`, and
every answer carries the GtoPdb version. Check that the ID agrees with an
existing gk_central ReferenceTherapeutic where one exists (semaglutide 9724 did).
Then stage a new ReferenceTherapeutic modelled on the analogue's: identifier,
name and synonyms, inn, type, approved, url, and referenceDatabase "Guide to
Pharmacology - Ligands" (#9016465). The GtoPdb REST API is not used: it needs a
per-user key, and the bulk files carry the same ligand IDs.

**Summations are biology only.** Nothing about curation, modelling precedent,
what is "not curated here", or the agents. Those go in event `flags` (rendered
in the DOCX, never staged). Expand every acronym at first use within each
summation, use US spelling to match Reactome names, and give every in-text
citation a literatureReference on the same instance, and the reverse.

---

## The review loop

Round 2 onwards. Give the review agent the spec, the staging markdown, the
rendered DOCX and access to gk_central, OLS and E-utilities, and point it at
`../review-internal/SKILL.md` Sections 1–5 and 7 and its gk_central checks. It
tests the five things the curator cares about:

1. **Legitimate paper inclusion.** Primary for events, reviews for pathway
   summations only; the system is as claimed; the evidence sentence is verbatim;
   no preprints; citations and literatureReferences match one-for-one.
2. **Topology.** Entity chains across the new/existing boundary (query the
   existing events' participants); nothing shared twice; missing precedingEvents;
   placement.
3. **Required data-model elements**, including a duplicate check of every
   new instance against gk_central.
4. **Summation construction.**
5. **Naming and GO BP policy.**

Output: `agents/review_round<N>.json` with issues
`{id, priority, check, location, issue, evidence, action, owner, disputes}`,
where `owner` is orchestrator, literature, gk_central or curator, and `disputes`
names the construction-log entry it contradicts.

Then:

- **Verify every HIGH against the database before fixing it.** Route it to its
  owner: re-brief the literature or gk_central agent if it needs new searching;
  fix it yourself if it is assembly.
- **Log every disagreement** in `construction_log.json`: the argument, the
  evidence, the counter-argument and the resolution. Don't leave entries saying
  "pending" once a later round has settled them.
- **Regenerate the spec and staging file from one source** (a content JSON plus a
  builder script in `build/`), re-render to `drafts/v<N>.docx`, and resume the
  same reviewer to check its own findings and look for regressions.
- **Stop when a round finds no HIGH issue** (cap: 3 rounds, unless the curator
  sets another). Fix the remaining MEDIUM and LOW issues you can. Report the rest in
  `final_review.issues` **accurately**: the pilot's v2 claimed "no issues
  remain", and the reviewer caught it (D28).

The pilot's two review rounds found 4 HIGH, 8 MEDIUM and 7 LOW, then 0 HIGH, 2 MEDIUM and 4 LOW.
None of the HIGH issues was visible to the agents that built the draft.

---

## Construction log (`agents/construction_log.json`)

```json
{"rounds": [{"round": 0, "label": "what happened", "agents": ["..."]}],
 "entries": [{"id": "D1", "round": 0, "topic": "...", "raised_by": "gk_central",
              "position": "...", "evidence": "queries / PMIDs", "counter": "... or null",
              "resolution": "...", "status": "ADOPTED|CORRECTED|OPEN|DEFERRED|REJECTED"}]}
```

It renders as Section 6 of the DOCX. It is how the curator re-opens any decision,
so record why each one went the way it did, not only what was decided.

---

## The proposal spec and renderer

```
python3 build_pathway_proposal.py proposal_spec.json --validate
python3 build_pathway_proposal.py proposal_spec.json -o "<Topic>_proposal.docx"
```

`sample_pathway_proposal_spec.json` is the complete pilot spec. Top-level keys:
`title, proposed_pathway, source_paper, anchor_nodes, meta, executive, summary,
rationale, hierarchy, placement, subpathways, events, entities, references,
excluded_references, construction_log, final_review, open_questions, staging`.

The renderer reuses `/curation-update-from-paper`'s helpers (`build_update_doc.py`, `reaction_graphic.py`, `verify_references.py`), which stay in that skill's directory. It **refuses to render** when any reference
fails the PubMed five-field check (`verify_references.py`). It links an ST_ID
only when reactome.org serves it, and marks unreleased ones. It draws one
reaction diagram per new event (reused participants solid with their ST_ID; new
ones dashed and tagged NEW). Validation fails if a NEW event lacks name, type,
compartment, species, summation, subpathway or a reference; if a PMID lacks a
valid `pmid_source` or is missing from `references`; or if an executive decision
is not a HIGH open question.

### The logic must be written out

A curator who reads only the document must be able to follow every decision.
Tables alone are not enough, and `--validate` refuses a spec that is missing any of
these:

| Field | Renders as | Content |
|---|---|---|
| `summary` | Executive summary | Three paragraphs: what exists, what the paper and literature support, the verdict |
| `how_to_use` (optional) | "How to Use This Proposal" | Five numbered steps; a default is supplied |
| each subpathway's `chain` (`lanes`, `regulators`, `questions`, `context`) | Section 3: a chain diagram leading each subpathway (`pathway_graphics.render_chain`), with open questions pinned to the steps they affect. Section 1 opens with a one-page hierarchy map (`render_hierarchy_map`) above the tree table | Lanes of steps (`shared`, `new` or `gap`); `independent: true` for receptor events with no chain between them |
| `hierarchy_intro` | Section 1, opening | What the hierarchy is and how to read the tree table. The table is drawn as a tree (├─ └─ connectors, level shading, ▣ pathway / ● reaction marks, new reactions in green), so the pathway-to-reaction relationship is visible without reading the text |
| `topology_intro` + each subpathway's `topology` | Section 1, "Pathway Topology" | How the subpathways relate (shared molecules, physiological states), then for each subpathway how its events connect, where the new events plug in, and why it has, or lacks, new reactions |
| `rationale` | Section 1, "Design Principles" | The rules applied everywhere (admission, sharing, reuse) |
| each subpathway's `flow` | Section 3, "How the events connect" | One line: the chain, with arrows, NEW events marked |
| each NEW event's `rationale`, `inputs`, `outputs`, `following_event`, `cell_type`, `figure` | Section 3 reaction card | Why it is proposed, then ONE table: name, class, species, compartment (separate rows), cell type, inputs, outputs, catalyst, GO MF, regulators, preceding/following event, inferred from and ECO evidence type where they apply, evidence basis, source figure, the **summation**, and the **literature references** |
| each NEW event's `primary_pmid` | Reaction table: "Literature reference" before the summation, then "Additional references for the summation" after it | ONE reference for the reaction: the paper whose quote is its evidence. The summation's other references are listed after the summation and never repeat the reaction's reference. The staging file follows the same split: the reaction's `literatureReference` is the primary paper only, and the Summation instance carries the rest. |
| each reference (event and subpathway) | Reference lines | Short citation, PubMed and DOI links, the experimental system, and a **tight verbatim quote** (≤ one sentence, an exact substring of the abstract) supporting the specific claim. Subpathway summations get their own reference list. Any summation claim without a supporting reference gets one added. |
| `placement_intro`, `entities_intro`, `literature_intro`, `events_intro`, `questions_intro` | Opening of each section | What the section shows and how to read it |
| each open question's `options` | Section 8 | `[{choice_id, choice, apply, recommended}]`. `apply` gives the exact edit: which staging-file block or line to change, quoted as it appears in the file, or what to do in the Curator Tool after loading |

Quote staging-file lines in `apply` exactly. Before rendering, check that every
quoted line exists in the staging file; the pilot's builder does this.

---

## Applying the curator's decisions

The curator records choices in Section 8 and then either edits the staging file
by hand, following each option's `apply` text, or tells you, for example
"apply Q1=A, Q2=A, Q8=keep E5". In the second case:

1. Edit the proposal source (the content JSON in `build/`), never the generated
   staging file. Remove or change the affected events and lines, and move each
   settled question from `open_questions` into the construction log as a decision
   with `raised_by: curator`.
2. Regenerate the spec and staging file, run `staging_from_md.py --check`, and
   re-render the DOCX to `drafts/` and then to the final name.
3. If a decision adds or changes a reaction, run one more internal-review pass
   on the changed events only.
4. Tell the curator which Curator Tool steps remain (the `apply` text marked
   "Curator Tool": moves, precedingEvent links on existing events, set
   membership). Those are never staged.

---

## Staging markdown, then the WebBench JSON

```
python3 staging_from_md.py <topic>_staging.md --check     # validate only
python3 staging_from_md.py <topic>_staging.md -o user-instances-<topic>.json
```

The format is documented at the top of `staging_from_md.py`. In short:

```
### @rxn-atgl-tag Reaction
- name: ABHD5:PNPLA2 hydrolyzes TAG to DAG and LCFA
- species: #48887 "Homo sapiens" Species
- input: #163438 "TAG [lipid droplet]" SimpleEntity
- catalystActivity: @cat-rxn-atgl-tag
- summation: @sum-rxn-atgl-tag
```

`#dbId "displayName" Class` is an existing gk_central instance (use the stored
displayName exactly); `@key` is another new instance in the file. The converter
checks every class and slot against `reactome_domain_model.json`. It checks
list against single-valued slots, instance against literal slots, and that
every `@key` resolves. It assigns negative dbIds and writes the shape the WebBench
frontend's Export writes (`reactome/curator-tool-frontend`,
`UserInstancesService.exportUserInstances`), following the conventions of the
Paper2Path emitter (`reactome/curator-tool-llm`,
`curator_llm/services/emitter.py`).

Tell the curator: **loading replaces their current staged changes.** WebBench
saves those to the server first; they can recover them with *Restore staged-changes
backup*. Slots the proposal leaves for them (a drug's GtP reference, any
AMBIGUOUS entity) are listed in Section 4 and Section 8.

---

## Cost

The pilot's first pass ran 6 agent invocations (2 + 2 + review twice), about 1.1 M subagent
tokens and about 45 minutes of wall-clock time, plus the orchestrator's own work.
The literature agent was the largest (about 250 k tokens, 380 E-utilities calls).
For a narrower topic, cap the literature targets at the 15–20 events most
likely to become reactions.
