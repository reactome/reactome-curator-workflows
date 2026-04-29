# Internal Module Review Skill

## Purpose

Perform a formal internal curation review of a Reactome pathway report, following
Curator Guide V94 (or current version) standards. This skill applies the complete
Reactome Internal Curation Review prompt (v1.4, March 2026) and produces a
structured review DOCX identical to the established Reactome internal review format.

The full prompt specification is maintained in:
 @Reactome_InternalReview_PROMPT_v1_4.docx

The companion output template is:
 @Reactome_InternalReview_TEMPLATE.docx

Reference materials for entity and event name checking (Section 7):
 @EWAS_name_rules.docx
 @Rules_for_automatic_reaction_typing.docx
 @ptm_prefixes.md
 @Small_molecule_renaming.xlsx
 @bau060.pdf

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

 /internal-module-review $ARGUMENTS

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
 /internal-module-review "HHV8 Infection" R-HSA-9521541 "Marc Gillespie" 2026-04-15
 /internal-module-review "TP53 Regulation of DNA Repair" R-HSA-6796648 "Lisa Matthews" 2026-04-15 disease

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

Present ALL issues from Sections 1-7 (including all Section 1.3 entity chain
mismatches and all Section 7 naming violations) in a single consolidated table:
 Issue | Section(s) | Type | Priority | Action Required

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