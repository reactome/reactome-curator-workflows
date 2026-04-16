# Curation Review Skill

## Purpose

Perform a formal internal curation review of a Reactome pathway report, following
Curator Guide V94 (or current version) standards. This skill applies the complete
Reactome Internal Curation Review prompt (v1.4, March 2026) and produces a
structured review DOCX identical to the established Reactome internal review format.

The full prompt specification is maintained in:
 @Reactome_InternalReview_PROMPT_v1_4.docx

The companion output template is:
 @Reactome_InternalReview_TEMPLATE.docx

## Required Inputs

Before invoking this skill, upload both of the following to the conversation:

 1. Pathway report DOCX — generated from the Reactome Curator Tool for the
    pathway being reviewed. Multi-part reports must be merged into a single
    DOCX before uploading.

 2. Curator Guide PDF — current version (Curator_Guide_V94.pdf or later).
    A copy of V94 is in this skill directory for convenience, but always
    confirm you are using the version current at the time of review.

If either file is missing, stop and ask the user to upload it before proceeding.

## Invocation

 /curation-review $ARGUMENTS

$ARGUMENTS should specify:
 - Pathway name (required)
 - Reactome ID / ST_ID, e.g. R-HSA-9985686 (required)
 - Reviewer name (required)
 - Review date (required)
 - Pathway type modifier, if applicable (optional):
     disease     — applies disease pathway additional standards
     drug        — applies drug curation additional standards
     large       — applies scope restriction for 50+ reaction pathways;
                   specify sub-pathway names or §-references to focus on

Examples:
 /curation-review "HHV8 Infection" R-HSA-9521541 "Marc Gillespie" 2026-04-15
 /curation-review "TP53 Regulation of DNA Repair" R-HSA-6796648 "Lisa Matthews" 2026-04-15 disease

## What This Skill Does

Read both uploaded documents in full. Then produce a complete internal review
DOCX titled:

 Reactome_[PathwayName]_[ReactomeID]_InternalReview.docx

The review must contain exactly these seven sections:

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

3.1 Flag preprints (bioRxiv, medRxiv) not labeled as such.
3.2 Flag author name discrepancies, including diacritical marks.
3.3 Flag comment thread text that has leaked into summation bodies.
3.4 Flag any references needing publication status verification.
   Note the overall quality of literature coverage as a strength if warranted.

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

Present ALL issues from Sections 1-5 (including all Section 1.3 entity chain
mismatches) in a single consolidated table:
 Issue | Section(s) | Type | Priority | Action Required

Sort HIGH → MEDIUM → LOW within each type.

---

## Formatting Standards

- Output a properly formatted DOCX, not plain text
- Use navy (#1F3864) for H1 headings, teal (#1F7A8C) for H2
- Include the metadata header block: pathway name, report filename,
 guide version, reviewer name, review date
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

## Optional Additions (append via $ARGUMENTS modifier)

### disease — Disease Pathway Additional Standards

- Verify that disease terms are assigned from DOID (not free text)
- Check that FailedReactions have entityFunctionalStatus and normalReaction
 attributes referenced in summations
- Verify that loss-of-function and gain-of-function reactions are in
 separate sub-pathways per Curator Guide disease structure standards
- Check that COSMIC / ClinVar / ClinGen cross-references are present
 for characterized variants

### drug — Drug Curation Additional Standards

- Verify that all drug entities have a GtP identifier in the referenceEntity slot
- Check that drug binding reactions are typed as 'Association' in the ELV
- Verify that disease attribute is set on drug entities
- Flag any drug without ChEBI cross-reference (desirable but not mandatory)
- Check that regulation instances reference the correct downstream event

### large — Large Pathway Scope Restriction (50+ reactions)

- Focus reaction connectivity and grammar review on the sub-pathways
 specified in $ARGUMENTS
- For Section 1.3, focus on the same sub-pathways but flag any entity
 naming inconsistency that spans sub-pathway boundaries
- Complete all other sections (GO terms, references, quality) across
 the full report

## Output

Produce the review as a downloadable DOCX file named:
 Reactome_[PathwayName]_[ReactomeID]_InternalReview.docx

Do not ask clarifying questions. Work from the two uploaded documents alone.

## Notes and Limitations

- Claude Sonnet 4.x can handle large pathway reports (200+ pages) in a
 single session. If output is truncated, append "Continue the review
 from Section [N]" in a follow-up message.
- The entity chain analysis in Section 1.3 is based on reading summation
 text and reaction diagram images. All flagged mismatches should be
 verified by the curator in the Curator Tool before correction.
- Claude will suggest GO BP terms based on training data. Always
 cross-check suggested GO IDs against OLS4 (https://www.ebi.ac.uk/ols4/)
 or AmiGO before committing terms.
- Claude cannot access live PubMed or bioRxiv. Flag all preprints for
 manual verification.
- This prompt was calibrated against Curator Guide V94/V95. If the guide
 changes substantially, review the standards block and update accordingly.