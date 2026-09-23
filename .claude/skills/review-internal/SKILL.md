# Internal Module Review Skill

## Purpose

Perform a formal internal curation review of a Reactome pathway report, following
Curator Guide V94 (or current version) standards. This file is the complete and
authoritative specification for the review; it produces a structured review DOCX
identical to the established Reactome internal review format.

The companion output template is:
 @Reactome_InternalReview_TEMPLATE.docx

Reference materials for entity and event name checking (Section 7):
 @EWAS_name_rules.docx
 @Rules_for_automatic_reaction_typing.docx
 @ptm_prefixes.md
 @Small_molecule_renaming.xlsx
 @bau060.pdf

## Working directory and upload destination — set this up first

To keep this repository clean, **never write generated files into it.** Before
doing anything else, settle two things with the curator:

- **Local directory** — where the review DOCX and any intermediates are written.
  Default is a gitignored `output/` folder in the repo
  (`./output/<pathway-slug>-review/`; git already ignores `output/`), or give an
  absolute path outside the repo (e.g. `~/reactome-work/hhv8-infection-review/`).
- **Release version** — e.g. `V95`. This labels the review and names the Drive
  upload subfolder; it does not affect where the file is written locally. If it
  was supplied in $ARGUMENTS, confirm it rather than asking again.

Create the directory with `mkdir -p`, write all outputs there, and report the
full path back. Do not write into the repo root, `.claude/`, or next to the
skill files.

**Upload destination.** Reviews are archived on the shared Drive so the whole
team can see the full set for a release. This skill does not upload — it writes
locally and tells the curator where the file belongs. Once the review is
written, state:

> Upload this review to the `<release>` subfolder of the Reactome Internal
> Reviews Drive folder: https://drive.google.com/drive/folders/1J_T0-Ihx8hdsNv75pvrsJqjYwJo3gYpP
> Create the `<release>` subfolder if it does not already exist.

The same destination and release label also go in the report's own metadata
header block (see Formatting Standards), so the DOCX carries its filing
instructions with it.

## Required Inputs

Before invoking this skill, upload both of the following to the conversation:

 1. Pathway report DOCX — generated from the Reactome Curator Tool for the
    pathway being reviewed. Multi-part reports must be merged into a single
    DOCX before uploading.

 2. Curator Guide PDF — current version (Curator_Guide_V94.pdf or later).
    A copy of V94 is in this skill directory for convenience, but always
    confirm you are using the version current at the time of review.

If either file is missing, stop and ask the user to upload it before proceeding.

## Optional — live database cross-check

The report is what's being reviewed. The live database, if you can reach it,
catches what a report can't show: a report exported before a rename, events
dropped when a multi-part report was merged, a GO ID that doesn't exist.

**Detect, don't require.** Check whether the session has the `gk-central` MCP
tools (`mcp__gk-central__read_neo4j_cypher`) and the `ols` tools. Use whichever
are present. If neither is, add one line to Overall Notes — "Live database
cross-check not run (no Reactome MCP server available; see
/analysis-reactome-mcp)" — and review from the documents alone. Never stop the
review to set a server up.

With **gk-central**, read-only queries matching on the report's ST_ID (confirm
unfamiliar property or relationship names with `get_neo4j_schema` first):

- The pathway ST_ID exists and its `displayName` matches the report → if not,
  MEDIUM, in Overall Notes.
- Events under the pathway in gk_central versus events in the report → events
  missing from the report go in Overall Notes, MEDIUM: the report may be an
  unmerged multi-part export, or stale.
- PMIDs attached to each event in gk_central versus the report's reference lists
  → differences go in Section 3.
- GO biological process terms on the pathway and its reactions in gk_central
  versus the report → differences go in Section 2.

With **ols**: resolve every GO ID you recommend in Section 2 and confirm its label
before writing it down. Don't recommend an ID that OLS doesn't return.

Label every database-derived finding "(gk_central)" or "(OLS)", and note in the
metadata header whether the cross-check ran. gk_central may be newer than the
exported report, so a report-versus-database difference is something for the
curator to reconcile. It is not proof the report is wrong: rate it MEDIUM unless
it also breaks a Curator Guide rule on its own.

## Invocation

 /review-internal $ARGUMENTS

$ARGUMENTS should specify:
 - Pathway name (required)
 - Reactome ID / ST_ID, e.g. R-HSA-9985686 (required)
 - Reviewer name (required)
 - Review date (required)
 - Release version, e.g. V95 (optional) — labels the review and names the
   Drive upload subfolder. If omitted, ask for it at the opening gate.

Examples:
 /review-internal "HHV8 Infection" R-HSA-9521541 "Marc Gillespie" 2026-06-16 V95
 /review-internal "TP53 Regulation of DNA Repair" R-HSA-6796648 "Lisa Matthews" 2026-04-15

There are no pathway-type modifiers. Every review applies the same standards and
covers the full report; disease and drug standards apply automatically wherever
the report carries disease or drug annotation (see Standards to Apply).

## What This Skill Does

Read both uploaded documents in full. Then produce a complete internal review
DOCX titled:

 Reactome_[PathwayName]_[ReactomeID]_InternalReview.docx

The review opens with a report header and an Executive Summary, then contains
exactly these seven sections.

---

### REPORT OPENING — EXECUTIVE SUMMARY

Before Section 1, and after the metadata header block, the report must carry:

1. **Issue Count by Priority** — a HIGH / MEDIUM / LOW / Total tally.

2. **Critical Issues — Action Required.** A table of every HIGH-priority issue
   found anywhere in Sections 1-7, so a reviewer sees what must change without
   reading to the end:

    Issue | Section(s) | Location (§) | Required Action

   Rules for this table:
   - **HIGH priority only.** MEDIUM and LOW belong in their own sections and in
     Section 6, not here.
   - **It is a strict subset of Section 6.** Every row here must also appear in
     the Section 6 consolidated table, worded consistently. Never list an issue
     here that is absent from Section 6, and never omit a HIGH-priority issue
     from here that Section 6 records.
   - **Order by section**, then by severity of consequence within a section.
   - **If there are no HIGH-priority issues, say so explicitly** — write "No
     HIGH-priority issues identified" rather than leaving the table empty.

3. **Overall Recommendation** — ready for peer review / needs revision / needs
   significant revision.

4. **Overall Notes** — observations that apply to the pathway as a whole and do
   not fit a specific section.

---

### SECTION 1 — REACTION CONNECTIVITY

1.1 Strengths: Identify what is correctly structured. Cover preceding-event
   linkages, pathway branching/convergence, BlackBoxEvent usage, and
   biological coherence.

1.2 Issues: Flag each connectivity problem with §-level citation, priority
   (HIGH / MEDIUM / LOW), and a specific recommended action.

1.3 Input→Output Entity Chain Verification:
   For every pair of events where one event is listed as the preceding
   event of the next, verify that the output entity of the preceding event
   is correctly named as an input entity of the following event.
   Specifically check:

   (a) Post-translational modification (PTM) state tracking: when a
       reaction produces a phosphorylated, glycosylated, ubiquitinated,
       sumoylated, methylated, palmitoylated, propionylated, or otherwise
       modified entity, confirm that the modification prefix (e.g., p-,
       GlcNAc-, NG-, M1polyUb-, SUMO2-, methyl-) is preserved in the
       entity name used as the input of the immediately following event.

   (b) Oligomeric state tracking: when a reaction produces a dimer,
       trimer, tetramer, pentamer, or hexamer, confirm that the oligomeric
       form is named as the input of the following event.

   (c) Complex state tracking: when a reaction produces a named complex
       (e.g., ORF18:ORF34), confirm that the complex is used as the input
       of the following event, not the individual subunits.

   (d) Accumulated modifications: when an entity has undergone multiple
       preceding modifications (e.g., GlcNAc + M1polyUb), confirm that
       the downstream event names the fully modified entity.

   Present findings in a table:
   Preceding Event | Output Entity Named | Following Event | Input Entity Named | Consistent? | Priority | Action

   For confirmed mismatches, provide a specific recommended correction.

   Note: diagrams embedded in the pathway report show the actual entity
   labels used in the Curator Tool — these are authoritative for entity
   names and should be cross-referenced when summation text is ambiguous.

---

### SECTION 2 — GO BIOLOGICAL PROCESS ASSIGNMENTS

GO BP POLICY (apply these rules when evaluating assignments):

(a) Pathways: A GO BP term is not mandatory in the data model, but as
   editorial policy every pathway SHOULD have a BP term unless the
   pathway describes something out of scope for GO. All viral life
   cycles and host-virus interactions are in scope; specific effects
   of pharmaceuticals may be out of scope. Flag any pathway or
   sub-pathway missing a BP term as MEDIUM priority unless clearly
   out of GO scope.

(b) Reactions: Reactions are permitted to carry BP terms, but a reaction
   that is part of the process described by its parent pathway should
   NOT repeat the parent's BP term. Reaction-level BP terms SHOULD
   be used when Reactome groups something that GO keeps separate.
   Key example: GO always distinguishes "process X" from
   "regulation of process X", but Reactome annotates regulation
   events as part of the process. Therefore, regulation reactions
   contained within pathway X can/should be annotated with the GO
   "regulation of X" BP term to bridge this gap.

2.1 Present findings in a table:
   Pathway/Sub-pathway or Reaction | Current GO BP Term(s) or Status |
   Recommended GO Term(s) with IDs | Priority

2.2 Add notes on overall GO BP coverage strategy. Cross-reference curator
   comments that mention GO terms. Apply Curator Guide standards: terms
   must be as specific as possible; infectious disease pathways should use
   GO terms specific to the type of infection (viral-process terms for
   viral pathways, bacterial-process terms for bacterial, parasitic-process
   terms for parasitic pathways, etc.). Identify any regulation reactions
   that would benefit from a "regulation of X" BP term per rule (b) above.

---

### SECTION 3 — LITERATURE REFERENCES

**Run the verifier first.** Before writing this section, run the bundled helper
against the report. It resolves every PubMed URL in the report through NCBI
E-utilities in one batched call and reports discrepancies:

    python3 .claude/skills/review-internal/verify_pmids.py <report.docx>

Optional: `--json <path>` to capture findings as JSON, `--email you@org` to send
a courtesy contact address to NCBI.

What it checks:
 - first-author surname, initials, publication year and journal, against the
   PubMed record for each PMID in the reference lists
 - PMIDs PubMed does not recognise
 - the same PMID listed twice in one reference list (duplicate
   LiteratureReference — cf. QA check GT037)
 - in-text citations with no matching reference in the same section, and the
   near-miss case where the same author is listed under a different year
 - references listed but never cited in that section's summation

Fold its output into 3.1-3.5 below with the priorities it assigns. Two rules:

 - **If the script cannot reach NCBI it exits non-zero and verifies nothing.**
   Do not record references as checked in that case. Say in the review that PMID
   verification did not run, and flag the whole section for manual checking.
 - **Never assert a PMID is correct that the script did not resolve.** Anything
   it lists as UNCHECKED stays unchecked in the review.

The script reads the DOCX directly and uses the standard library only. It calls
`eutils.ncbi.nlm.nih.gov` via urllib under Bash, so it is governed by Bash
permission rather than the `WebFetch` allowlist entry.

3.1 Report the verifier's findings: author, year and journal disagreements,
   unresolved PMIDs, and duplicate PMIDs within a reference list.
3.2 Report citations with no matching reference, and references never cited.
3.3 Flag preprints (bioRxiv, medRxiv) not labeled as such.
3.4 Flag comment thread text that has leaked into summation bodies.
3.5 Flag any remaining references needing publication status verification.
   Note the overall quality of literature coverage as a strength if warranted.

Author-name discrepancies that survive the automated check — diacritical marks,
transliteration variants, inconsistent rendering of the same author across
events — still need reading by eye; the script compares only the first author.

---

### SECTION 4 — GRAMMAR, CLARITY, AND SUMMATION QUALITY

4.1 List all typographical and grammatical errors in a table:
   Priority | Location | Error As Written | Type | Correction

4.2 Identify clarity issues: missing acronym expansions, confusing concept
   mixing, ambiguous statements, undefined technical terms.
   Note all curator comments that flag grammar or clarity issues.

---

### SECTION 5 — GENERAL CURATION QUALITY

5.1 Strengths: Literature depth, strain/cell-line provenance, inference
   handling, consistent terminology, Curator Guide compliance.

5.2 Areas for Improvement: Systemic patterns, missing author attributions,
   missing pathway-level GO BP terms, redundant reaction-level BP terms,
   missed regulation-of-X opportunities, inferred events without required language.

---

### SECTION 6 — PRIORITIZED ISSUE SUMMARY

Present ALL issues from Sections 1-7 (including all Section 1.3 entity chain
mismatches and all Section 7 naming violations) in a single consolidated table:
 Issue | Section(s) | Type | Priority | Action Required

This table is the complete record at every priority. The Critical Issues table in
the Executive Summary is its HIGH-priority subset — reconcile the two before
finishing, so no HIGH issue appears in one and not the other.

Sort HIGH → MEDIUM → LOW within each type.

---

### SECTION 7 — ENTITY AND EVENT NAME CONVENTIONS

Apply the rules in @EWAS_name_rules.docx, @Rules_for_automatic_reaction_typing.docx,
@ptm_prefixes.md, and @bau060.pdf (Jupe et al. 2014, controlled vocabulary paper) to
check every entity and event name in the pathway report.
Use @Small_molecule_renaming.xlsx as a lookup reference for small molecule names.

#### 7.1 EWAS (protein/peptide) entity names

Check every protein/peptide entity name against the following rules:

(a) **Gene symbol core.** The name must use the HGNC gene symbol derived from
   UniProt via the Reactome referenceEntity. Human proteins: ALL-CAPS. Non-human:
   initial capitalisation only (e.g., Jak2 for mouse, JAK2 for human).

(b) **Peptide coordinate suffix.** Coordinates are added as `(start-end)` only
   when the EWAS start or end position differs from the UniProt Chain feature.
   When coordinates are needed, both start and end must be given. Unknown
   positions are written as `?` (e.g., `ACAN(17-?)`).

(c) **PTM prefixes.** Each modification must use the prefix from @ptm_prefixes.md
   (column: Prefix), looked up by PSI-MOD ID. Non-phosphorylation PTMs are listed
   before phosphorylation prefixes. Multiple copies of the same non-phospho PTM
   use `Nx` notation (e.g., `2xPalmC`).

(d) **Phosphorylation prefixes.** Format: `p-[subtype_letter][coordinate]`.
   Subtype letters: S (serine), T (threonine), Y (tyrosine); omit letter when
   subtype is unknown. Phosphorylations are ordered by coordinate position.
   When >4 of any phospho subtype are present, replace individual coordinates
   with a count (e.g., `p-7Y-KIT`). Mixed subtypes are ordered by coordinate,
   not grouped by subtype (e.g., `p-Y55,S112,S121,Y227-SPRY2`).

(e) **Combined PTM + phosphorylation.** Non-phospho PTMs come first; phospho
   prefixes come last (e.g., `2xPalmC-MyrG-p-S1177-NOS3(2-1203)`).

(f) **Mutation notation.** Sequence substitutions follow the gene symbol:
   `GENE residueXvariant` (e.g., `CTNNB1 T41A`). Premature terminations use `*`.
   The words "mutant", "mutants", or "mutation" are not part of the name. A set
   of variants is named `[PTM-]GENE residueN mutants` (e.g., `pS45-CTNNB1 T41 mutants`).

(g) **Exemptions.** Do not flag entities that are exempt from systematic renaming:
   names containing "mutant" or "active"; entities with a disease annotation;
   entities whose referenceEntity has no gene name; non-ReferenceGeneProduct
   referenceEntities (mRNA, miRNA, etc.); isoforms with variantIdentifier > 1;
   entities with non-simple modifiedResidue (GroupModifiedResidue, crosslink).

Present findings in a table:
 Entity Name As Written | Rule Violated | Correct Form | Priority

Flag as HIGH if the modification state misrepresents the biology or conflicts with
Section 1.3 entity chain analysis. Flag as MEDIUM for incorrect prefix or coordinate
format. Flag as LOW for cosmetic issues (ordering, capitalisation inconsistencies
in non-human entities).

#### 7.2 Reaction/event names

Check every reaction and event name against the naming format rules in
@Rules_for_automatic_reaction_typing.docx. Apply these formats:

| Reaction class | Required format |
|---|---|
| Transformation (default, no catalyst) | `a TRANSFORMS TO b` |
| Binding | `a BINDS b` |
| Dissociation | `a DISSOCIATES TO b AND c` |
| Polymerization | `a POLYMERIZES TO x` |
| Depolymerization | `x DEPOLYMERIZES TO a` |
| Catalysed (GOMF verb available) | `Protein x [GOMF-verb] entity a TO d` |
| Transferase | `Protein x TRANSFERS y TO a (TO FORM a2)` |
| Transport, no transporter | `a TRANSLOCATES FROM [compartment x] TO [compartment y]` |
| Transport, named transporter | `Protein x TRANSPORTS a (FROM compartment x TO compartment y)` |
| Antiporter | `Protein x EXCHANGES a FOR b (across the y membrane)` |
| Cotransporter | `Protein x COTRANSPORTS a (b) WITH c (d)` |
| Activation | `a is activated` |
| Regulation | `a (positively or negatively) REGULATES x` |

For catalysed reactions: verify that the verb is consistent with the catalyst's
GO molecular function. The GOMF→verb mapping is documented in the Rules file.
Common verbs include: hydrolyses, phosphorylates, ubiquitinates, acetylates,
methylates, isomerizes, cleaves, biotinylates.

Present findings in a table:
 Event Name As Written | Reaction Class | Issue | Correct Format | Priority

Flag as HIGH if the wrong reaction class verb is used (e.g., TRANSFORMS for a
known binding event). Flag as MEDIUM for format deviations (missing compartment
in TRANSLOCATES, wrong verb tense). Flag as LOW for capitalisation or minor
phrasing issues.

#### 7.3 Small molecule names

Cross-reference small molecule entity names against @Small_molecule_renaming.xlsx
(sheet: "small molecules", columns: name and location). Flag any name that
differs from the canonical name in the reference list.

Note: the reference list is a large but not exhaustive lookup. Only flag cases
where a clear canonical form exists in the spreadsheet. For names not found in
the list, apply general chemical naming consistency checks.

Present findings in a table:
 Name As Written | Canonical Name | Location | Priority

#### 7.4 Complex names

Check every named complex against the CV rules in @bau060.pdf:

(a) **Component separator.** Components of a complex are separated by colons
   with no spaces (e.g., `GRB2:SOS1`, `IL3RA:IL3RB:JAK2`).

(b) **Repeated entity in a heteromeric complex.** When one entity appears more
   than once, precede its name with the count and `x` (e.g., `2xPPOX:FAD` for
   a complex of two PPOX molecules and one FAD). Do not use the familiar
   multimer term (dimer, tetramer) for heteromers — reserve those for homomers.

(c) **Homomeric multimers.** Familiar terms (dimer, trimer, tetramer, pentamer,
   hexamer) are acceptable for pure homomeric assemblies.

(d) **Hierarchical subcomplexes.** When a pre-existing complex or set is a
   component, enclose it in square brackets to show the hierarchical boundary
   (e.g., `[ABC1:ABC2]:[ABC3:ABC4]`). Nesting is recursive:
   `[[ABC1:ABC2]:[ABC3:ABC4]]:XYZ1`.

(e) **Set component in a complex name.** When a complex contains a set, the
   set is named using comma notation (see 7.5) and that comma-separated string
   is used within the colon-separated complex name, e.g.,
   `RhoRac GEFs:GDP` where `RhoRac GEFs` is the set.

Present findings in a table:
 Complex Name As Written | Rule Violated | Correct Form | Priority

Flag as HIGH if the wrong separator is used in a way that makes the composition
ambiguous (e.g., comma instead of colon). Flag as MEDIUM for missing square
brackets around subcomplexes or incorrect multimer notation. Flag as LOW for
capitalisation or spacing issues.

#### 7.5 Set names

Check every named set against the CV rules in @bau060.pdf:

(a) **Member separator.** Members of a Defined Set are separated by commas with
   no spaces (e.g., `IL3,IL3RA,CSF2RB`).

(b) **Candidate members.** In a Candidate Set, experimentally unverified candidate
   members are enclosed in round brackets within the comma-separated list
   (e.g., `HRH2,HRH3,(HRH6,HRH8)` where HRH6 and HRH8 are candidates).

(c) **Diagram label conventions.** When a set name is used as a diagram label,
   the following short forms are acceptable but the full CV name remains canonical:
   - Common gene-symbol stem + plural suffix (e.g., `VAVs` for VAV1, VAV2, VAV3)
   - Range notation (e.g., `CCR1-5` for CCR1–CCR5; `CCR1,3-5` for CCR1, CCR3–CCR5)
   - Functional description (e.g., `CCR2 ligands`, `VAV2-activated RhoGEFs`)
   - Diagram labels for sets must always be plural to distinguish them from
     singular entities (e.g., `alcohol dehydrogenase complexes`, not
     `alcohol dehydrogenase complex`).

Present findings in a table:
 Set Name As Written | Rule Violated | Correct Form | Priority

Flag as HIGH if comma and colon separators are confused (set treated as complex
or vice versa), or if candidate members are not distinguished from confirmed members.
Flag as MEDIUM for plural/singular errors in diagram labels. Flag as LOW for
ordering or cosmetic issues.

---

## Formatting Standards

- Output a properly formatted DOCX, not plain text
- Use navy (#1F3864) for H1 headings, teal (#1F7A8C) for H2
- Include the metadata header block: pathway name, report filename,
 guide version, reviewer name, review date, and — at the top of the report —
 the release version and upload destination:
   Release:   <release version, e.g. V95>
   Upload to: https://drive.google.com/drive/folders/1J_T0-Ihx8hdsNv75pvrsJqjYwJo3gYpP
              (the <release> subfolder — create it if it does not exist)
- Priority labels: HIGH in red, MEDIUM in amber, LOW in green
- Reference reactions using §-notation matching the report's structure
- Reference curator comments by number (Comment #N)

## Standards to Apply

- Curator Guide is the primary standard. Every judgment must be traceable
 to a specific Guide requirement.
- For inferred events, apply the Guide's inferredFrom evidence requirements.
- For preprints: flag any citation to bioRxiv/medRxiv not labeled '[Preprint]'.
- For GO BP terms: every pathway should have a BP term (editorial policy)
 unless out of GO scope. Reactions may carry BP terms but should not repeat
 the parent pathway's term; use reaction-level BP for "regulation of X" cases.
 Prefer child terms over parent terms; use GO terms specific to the type of
 infection for infectious disease pathways.
- Typos and grammatical errors are MEDIUM or LOW priority unless they
 misrepresent biology, in which case treat as HIGH.
- Any reaction whose mechanistic basis is flagged as uncertain or contested
 in curator comments is HIGH priority and must appear in Section 6.
- For entity chain mismatches in Section 1.3:
   HIGH   — mismatch affects an entity whose modification state is
            explicitly described as functionally required in the summation
   MEDIUM — modification is present in the diagram but absent from the
            title/summation text
   LOW    — modification state is biologically ambiguous or data is from
            heterologous systems only
- Disease pathway standards — apply wherever the report carries disease
 annotation, and say nothing if it carries none:
   - Disease terms assigned from DOID, not free text
   - FailedReactions have entityFunctionalStatus and normalReaction
     attributes, referenced in their summations
   - Loss-of-function and gain-of-function reactions sit in separate
     sub-pathways, per Curator Guide disease structure standards
   - COSMIC / ClinVar / ClinGen cross-references present for
     characterized variants
- Drug curation standards — apply wherever the report carries drug
 annotation, and say nothing if it carries none:
   - Every drug entity has a GtP identifier in the referenceEntity slot
   - Drug binding reactions are typed 'Association' in the ELV
   - The disease attribute is set on drug entities
   - Flag any drug without a ChEBI cross-reference (desirable, not mandatory)
   - Regulation instances reference the correct downstream event

Review the full report. There is no scope restriction for large pathways — if
output is truncated, continue from the section where it stopped (see Notes and
Limitations) rather than narrowing what is covered.

## Output

Produce the review as a downloadable DOCX file named:
 Reactome_[PathwayName]_[ReactomeID]_InternalReview.docx

Write it to the local directory agreed at the opening gate, report the full
path, and repeat the Drive upload destination and release subfolder.

Do not ask clarifying questions about the review content — work from the two
uploaded documents alone. The opening gate's questions about the local output
directory and release version are the exception and must still be asked.

## Notes and Limitations

- Claude Sonnet 4.x can handle large pathway reports (200+ pages) in a
 single session. If output is truncated, append "Continue the review
 from Section [N]" in a follow-up message.
- The entity chain analysis in Section 1.3 is based on reading summation
 text and reaction diagram images. All flagged mismatches should be
 verified by the curator in the Curator Tool before correction.
- Claude will suggest GO BP terms based on training data. When the `ols`
 MCP server is available, every suggested GO ID is resolved through it (see
 Optional — live database cross-check). Otherwise, always cross-check
 suggested GO IDs against OLS4 (https://www.ebi.ac.uk/ols4/) or AmiGO before
 committing terms.
- PMID verification runs through verify_pmids.py against NCBI E-utilities
 (see Section 3). Claude itself has no PubMed access and must never assert a
 PMID is valid without the script's output. bioRxiv and medRxiv are not covered
 by the script — flag all preprints for manual verification.
- This prompt was calibrated against Curator Guide V94/V95. If the guide
 changes substantially, review the standards block and update accordingly.