# Reactome Curator Assistant

An AI-assisted biocuration workflow for proposing Reactome pathway hierarchies and verifying primary literature evidence. Built for use with Claude (Anthropic) via the claude.ai Projects interface or the Claude API.

---

## Contents

| File | Description |
|------|-------------|
| `Reactome_Curator_Assistant_Prompt.md` | The full system prompt that defines the assistant's role, workflow, and rules |
| `Reactome_RLE_Annotation_Reference_V94.md` | Condensed annotation reference covering ReactionLikeEvent curation rules extracted from the V94 Curator Guide and V90 Data Model Glossary |

---

## Overview

The Reactome Curator Assistant is a structured AI workflow that supports the pre-curation stage of Reactome pathway annotation. Given either a biological topic or a set of references (PMIDs, DOIs, or uploaded PDFs), the assistant:

1. Identifies or receives the references to be annotated
2. Proposes a complete Reactome pathway hierarchy — pathway names, subpathway names, and reaction names
3. Verifies the primary experimental literature for every proposed reaction using a mandatory ten-step protocol
4. Applies the full species and chimeric reaction framework, pairing non-human or mixed-species evidence reactions with inferred human reactions throughout
5. Presents the full hierarchy and verified citation blocks together for curator review

The assistant is designed to reduce the time spent on literature triage and hierarchy planning, and to surface citation errors — including fabricated PMIDs — before any data reaches the database. It does **not** replace the curator's database work. Ontology resolution, UniProt verification, duplicate detection, and full annotation table population remain the curator's responsibility and are explicitly out of scope.

---

## How to Use

### Requirements

- A Claude account with access to claude.ai Projects (claude.ai Pro, Team, or Enterprise), **or** access to the Claude API
- The system prompt (`Reactome_Curator_Assistant_Prompt.md`) loaded as the project instructions or passed as the system message in an API call
- Optionally: the reference file (`Reactome_RLE_Annotation_Reference_V94.md`) added to the project knowledge base

### Setup on claude.ai

1. Create a new Project at claude.ai
2. Open **Project instructions** and paste the full contents of `Reactome_Curator_Assistant_Prompt.md`
3. Under **Project knowledge**, upload `Reactome_RLE_Annotation_Reference_V94.md`
4. Start a new conversation — the assistant will open with the session prompt automatically

### Setup via API

Pass the contents of `Reactome_Curator_Assistant_Prompt.md` as the `system` parameter and the reference file content as a user-turn document at the start of the conversation, or embed it in the system prompt directly.

---

## Workflow

Each session runs as two consecutive phases without an approval gate between them.

```
Session opening
    │
    ├── Mode A: Curator supplies references
    │       │   PMIDs / DOIs / uploaded PDFs
    │       └── Assistant reads papers and proceeds
    │
    └── Mode B: Curator supplies a topic
            │   Assistant searches for primary literature
            │   Presents ranked candidate reference list
            └── STOP — curator confirms or modifies list
                    │
                    └── Curator replies "proceed"

Phase 1 — Hierarchy proposal (Stage 2)
    Proposed pathway / subpathway / reaction names
    Evidence species flags (human / non-human / chimeric)
    Non-human and chimeric reactions paired with inferred human reactions
    Proceeds immediately to Phase 2 — no approval gate

Phase 2 — Literature verification (Stage 3)
    Ten-step PMID verification protocol per reaction
    PMC full-text fetch and verbatim evidence sentence extraction
    Standard citation blocks or inferred-human citation blocks
    Subpathway by subpathway — no stops between subpathways

STOP — full output presented for curator review
```

---

## The Ten-Step PMID Verification Protocol

Every reaction in Phase 2 is processed through the following mandatory steps before a citation block is presented:

1. Search each PMID individually via web search and confirm the PubMed record exists
2. Match all five identifying fields: first author surname, journal, year, key title words, specific experimental claim
3. Flag any unverified PMID explicitly — never present an unverified PMID as correct
4. Confirm the cited paper contains **direct** evidence for the specific reaction, not merely a related topic; if the paper is a review, trace to the primary paper
5. Present all PMIDs as clickable hyperlinks (`https://pubmed.ncbi.nlm.nih.gov/[PMID]/`)
6. Fetch the primary paper full text via PMC where available
7. Locate and quote the specific experimental evidence sentence from the primary paper, including method, proteins, cell type or system, and figure number
8. Flag evidence quality mismatches (overexpression only, murine only, mixed species, indirect evidence)
9. For review inputs: trace the review reference number to the underlying primary paper and verify the PMID matches
10. Flag evidence relevance mismatches if the paper does not directly support the specific mechanistic claim

---

## Citation Block Format

### Standard (direct or indirect evidence)

```
Reaction name:    [name from hierarchy]
Primary PMID:     https://pubmed.ncbi.nlm.nih.gov/[PMID]/
Primary PMC URL:  https://pmc.ncbi.nlm.nih.gov/articles/PMCXXXXXXX/
Authors/Year:     [First author et al., Year, Journal]
Primary evidence: "[verbatim sentence from primary paper including method,
                  proteins, cell type or system, and figure number]"
Evidence type:    DIRECT / INDIRECT / OVEREXP ONLY
Species:          [human / murine / other]
Flags:            [mismatches, gaps, curator actions required]
```

### Inferred human reaction

```
Reaction name:    [inferred human reaction name]
Evidence type:    INFERRED FROM NON-HUMAN / INFERRED FROM CHIMERIC
Species:          Homo sapiens (inferred)
inferredFrom:     [name of the paired non-human or chimeric reaction]
Primary PMID:     https://pubmed.ncbi.nlm.nih.gov/[PMID]/
Authors/Year:     [same as paired evidence reaction]
Flags:            No independent human experimental evidence. Human annotation
                  is inferred. Curator should confirm human orthology is
                  supported before submission.
```

---

## Species and Chimeric Reaction Rules

The assistant applies the following logic to every proposed reaction. All reactions ultimately yield a human annotation.

| Experimental situation | Reaction type | isChimeric | Inferred human required |
|------------------------|--------------|-----------|------------------------|
| Human proteins/cells only | Human reaction | FALSE | No |
| Single non-human species only | Non-human reaction | FALSE | Yes |
| ≥2 species mixed in same assay | Chimeric reaction | TRUE | Yes |

Non-human proteins are named with initial capitalisation (Jak2); human proteins are ALL-CAPS (JAK2).

---

## Evidence Classification

| Evidence class | Reaction type | Examples |
|---------------|--------------|---------|
| DIRECT | Reaction | co-IP with purified proteins, in vitro reconstitution, SPR/ITC, NMR, crystallography, direct enzymatic or cleavage assay |
| INDIRECT | BlackBoxEvent (provisional) | KO, rescue, overexpression, inhibitor treatment, domain deletion |
| INSUFFICIENT | Do not annotate | Microarray alone, bulk proteomics alone, ChIP-seq alone, computational prediction alone, review statement without primary citation |

---

## What Is Out of Scope

The following are handled separately by the curator using database tooling and are not performed by the assistant:

- Neo4j / gk_central database queries (duplicate detection, hierarchy placement confirmation)
- OLS ontology term verification (GO, ChEBI, MONDO, UBERON accessions)
- UniProt REST API verification (sequence length, PTM coordinates, isoform selection)
- GtoPdb drug interaction checks
- Full annotation table population in the Curator Tool
- Disease flag resolution
- Pathway diagram drawing

All fields requiring these steps are marked **PENDING CURATOR VERIFICATION** in the assistant's output.

---

## The RLE Annotation Reference File

`Reactome_RLE_Annotation_Reference_V94.md` is a condensed reference extracted from the V94 Curator Guide and V90 Data Model Glossary. It covers only the content relevant to ReactionLikeEvent annotation and is intended to ground the assistant's outputs in the current Reactome controlled vocabulary and rules.

### Sections

| Section | Content |
|---------|---------|
| 1. Event class hierarchy | RLE subclasses and when each is used |
| 2. Mandatory and required fields | Full field table for RLEs |
| 3. Naming conventions | Event and PhysicalEntity naming rules with examples |
| 4. Compartment rules | GO_CellularComponent usage; specific vs. general terms |
| 5. Evidence rules | Direct/indirect/insufficient classification; overexpression flag |
| 6. Species and chimeric rules | Decision table; non-human and chimeric reaction pairs |
| 7. PhysicalEntity classes | EWAS, Complex, Set, SimpleEntity, Polymer, OtherEntity |
| 8. Catalyst and regulation | CatalystActivity, activeUnit, Regulation subclasses |
| 9. Gene expression patterns | Pattern A (TF binding proven), Pattern B, miRNA |
| 10. Summation rules | What goes in summation vs. literatureReference |
| 11. Reaction balance | Imbalance check rules; FailedReaction exception |
| 12. Disease RLE specifics | FailedReaction, GOF reactions, EFS, HGVS naming |
| 13. Data model glossary | Key class and attribute definitions for RLE annotation |
| 14. Quick reference table | What goes where at a glance |

### What is excluded from the reference file

Curator Tool installation and operation, diagram drawing and ELV procedures, QA check mechanics, drug curation, cell lineage paths, disease pathway hierarchy structuring and diagram sharing, ChEBI and species instance creation, and release procedures. These are either outside the scope of the AI-assisted workflow or require live database access.

### Source documents

- Reactome Curator Guide V94 (released September 2025; parts 1 and 2)
- Reactome Data Model Glossary V90 (released September 2024)

The reference file should be updated when a new version of the Curator Guide is released. Sections most likely to require updating between versions are: naming conventions (section 3), disease RLE rules (section 12), and evidence classification (section 5).

---

## Limitations and Important Caveats

**PMID fabrication risk.** Large language models can generate plausible-sounding but entirely fictitious PMIDs. The ten-step verification protocol is designed specifically to catch this failure mode. The assistant verifies every PMID against five identifying fields before presenting a citation block and flags any unverified PMID explicitly. Curators should nonetheless independently confirm all PMIDs before database submission.

**Full-text access.** The assistant fetches PMC full text where papers are open access. For paywalled papers, it uses web search to locate the relevant experimental passage. If a paper is not accessible, the citation block is flagged as incomplete.

**Knowledge cutoff.** The underlying model has a training cutoff and may not be aware of very recent publications. In Mode B (topic-based), the assistant performs live web searches to identify current literature, but curators should verify that the most recent relevant primary papers have been captured.

**Controversy and conflicting evidence.** Where supplied references contain conflicting findings, the assistant flags the conflict and presents both sides. It does not adjudicate between conflicting studies — that decision rests with the curator and, where relevant, the expert reviewer.

**Ontology accessions.** GO, ChEBI, MONDO, and UniProt accessions are not resolved in this workflow. All are marked PENDING CURATOR VERIFICATION. The assistant uses plain-text term labels throughout.

---

## Version History

| Version | Date | Notes |
|---------|------|-------|
| 1.3 | April 2026 | Current version. Reference-input variant. Adds Mode A (curator supplies references) alongside Mode B (topic search). Mandatory ten-step PMID verification protocol. Full species/chimeric framework applied at hierarchy and citation stages. |
| 1.0–1.2 | 2025–2026 | Earlier iterations; topic-only mode; less structured citation verification |

---

## Contributing

Suggestions for improving the system prompt or reference file are welcome via GitHub Issues. When proposing changes to the reference file, please cite the specific section of the Curator Guide or Data Model Glossary that supports the change, and note the guide version.

---

## Acknowledgements

The workflow and reference file are derived from the Reactome Curator Guide (V94) and Data Model Glossary (V90), maintained by the Reactome curation team at the Ontario Institute for Cancer Research and collaborating institutions. The naming conventions follow Jupe et al. (2014), *Database* (Oxford), PMID 24951798.
