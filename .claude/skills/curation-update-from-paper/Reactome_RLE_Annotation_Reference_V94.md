# Reactome RLE Annotation Reference — V94
## For use with the Reactome Curator Assistant system prompt

Extracted from: Curator Guide V94 (parts 1 & 2) and Data Model Glossary V90.
Scope: ReactionLikeEvent annotation only. Curator Tool operation, diagrams, disease
pathway structuring, drug curation, and cell lineage paths are excluded.

---

## 1. EVENT CLASS HIERARCHY

```
Event [superclass — not annotated directly]
├── Pathway
│   └── CellLineagePath  [out of scope here]
└── ReactionLikeEvent [superclass — not annotated directly]
    ├── Reaction
    ├── BlackBoxEvent (BBE)
    ├── Polymerisation
    ├── Depolymerisation
    ├── FailedReaction     [disease only]
    └── CellDevelopmentStep  [cell lineage only]
```

### Reaction
Single-step transformation of inputs to outputs. Covers enzymatic reactions,
transport between adjacent compartments, complex association/dissociation,
protein–protein binding, protein–DNA binding.

### BlackBoxEvent (BBE)
Incompletely specified RLE or multi-step process. Use when:
- Molecular details are unknown (e.g., partially purified enzyme, unspecified products)
- Intervening steps exist but are deliberately not curated (e.g., transcription→protein,
  protein degradation, transport where mechanism is unknown but localisation is proven)
- Evidence is indirect (KO, rescue, overexpression, inhibitor treatment, domain deletion)

### FailedReaction
Disease loss-of-function event. Has inputs only (disease variant + WT co-inputs); no outputs.
Must have: disease tag, normalReaction, entityFunctionalStatus. Name format:
"Defective [protein] doesn't [WT function]"

### Polymerisation / Depolymerisation
Assembly/disassembly of polymers from/to repeated identical units.

---

## 2. MANDATORY AND REQUIRED FIELDS FOR ReactionLikeEvent

### MANDATORY (must be filled before release)

| Field | Description |
|-------|-------------|
| **name** | Concise, unique event name (see Naming section) |
| **input** | Each input PhysicalEntity entered individually, including cofactors (ATP, NAD+, ubiquitin) and stoichiometric partners |
| **output** | Each output PhysicalEntity entered individually, including byproducts (ADP, Pi, PPi) |
| **compartment** | Specific GO_CellularComponent term (see Compartment rules) |
| **species** | Homo sapiens for human; specific non-human species for non-human or chimeric reactions |
| **literatureReference** | Verified PMID providing **direct experimental evidence** for this reaction in the annotated species |
| **summation** | Free-text description; background citations go here, not as primary evidence |
| **edited** | InstanceEdit recording curator name and date |

### REQUIRED (fill where applicable)

| Field | Description |
|-------|-------------|
| **catalystActivity** | PhysicalEntity + GO_MolecularFunction; required when a catalyst is known |
| **inferredFrom** | Points to the non-human or chimeric RLE this human event is inferred from |
| **authored / reviewed** | InstanceEdit for external author/reviewer |

### OPTIONAL (but important)

| Field | Description |
|-------|-------------|
| **regulatedBy** | Regulation instance (NegativeRegulation, PositiveRegulation, Requirement) |
| **precedingEvent** | Prior RLE (RLE→RLE only; never Pathway→RLE) |
| **isChimeric** | TRUE if proteins from ≥2 species were mixed in the same assay |
| **disease** | Disease Ontology (DO) term — required for all disease RLEs |
| **normalReaction** | For disease RLEs: the corresponding WT RLE |
| **entityFunctionalStatus** | For disease RLEs: gain/loss-of-function descriptor |
| **evidenceType** | ECO term — used when direct evidence rule cannot be met |

---

## 3. NAMING CONVENTIONS

### ReactionLikeEvents
General form: **[PhysicalEntity] [active verb] [object]**

| Reaction type | Name pattern | Example |
|---------------|-------------|---------|
| Enzymatic | Subject verbs object | p-T14,Y15-CDK1 dephosphorylates CDC25A at S124 |
| Complex assembly | A binds B | GRB2 binds SOS1 |
| Complex dissociation | A dissociates from B | ADP dissociates from ATP:ADP:Pi:MgATPase |
| Transport | A translocates from [X] to [Y] | KPNA1 translocates from cytosol to nucleoplasm |
| Conformational activation | Use "activated" ONLY for inactive→active conformational change | GTP-bound RAS activates BRAF |
| FailedReaction | Defective [protein] doesn't [WT function] | Defective ALG9 does not add mannose to N-glycan precursor |

**Rules:**
- "complex" and "receptor" are excluded from PE names unless part of an established common name (e.g., RNA pol II complex, Mediator complex)
- "activated" has a special meaning — only for conformational change from inactive to active state
- PTM prefix: p-S124-CDC25A (phospho at serine 124)
- Non-human proteins: Capitalised (Jak2); human proteins: ALL-CAPS (JAK2)

### PhysicalEntity names
**EWAS:** Gene symbol (HGNC/UniProt); PTM as prefix (e.g., p-Y256,Y263-HAVCR2);
fragment/cleavage as suffix.

**Complex:** Colon-separated component names:
`GRB2:SOS1`, `IL3:IL3RA:IL3RB:JAK2`, `IL4:p-Y-IL4R:JAK2:p-Y-IL2RG:JAK3`
- Cardinality: 2x, 3x etc. in front of name (dimer/tetramer acceptable; NOT homo-/hetero- or "complex")
- When a complex grows by addition: new component appended on the right
- >4 components: descriptive name from literature acceptable if widely used
- Add compartment in brackets when needed for disambiguation: `GRB2:SOS1 [cytosol]`

**Set names (≤4 members):** Comma-separated list: `IL3,IL3RA,CSF2RB`
**Set names (≥5 members):** Descriptive/functional name if widely used; family name with plural suffix (CCRs); range notation (CCR2-5)

---

## 4. COMPARTMENT RULES

- Use the most specific GO_CellularComponent term available
- **Nucleoplasm** not nucleus; **cytosol** not cytoplasm
- For RLEs involving participants in >1 compartment: compartment field reflects ALL participating compartments (inputs, outputs, catalyst, regulators)
- Complexes: record the "core compartment" (place most associated with function) in compartment slot; other locations auto-populated at release in includedLocation
- Membrane-spanning complexes: membrane listed in compartment; flanking compartments auto-added
- All members of a set must share the same compartment

**Do NOT create new compartment instances.** Contact Managing Editor if needed.

---

## 5. EVIDENCE RULES

### The primary rule
The literatureReference on a Reaction **MUST provide direct experimental evidence** for
that specific reaction in the annotated species (human for human Reactome).

### Evidence classification

| Evidence type | Reaction class | Examples |
|---------------|---------------|---------|
| DIRECT | Reaction | co-IP with purified proteins, in vitro reconstitution, NMR, SPR/ITC, crystallography, direct enzymatic assay, direct cleavage assay |
| INDIRECT | BlackBoxEvent (provisional) | KO/rescue, overexpression, inhibitor treatment, domain deletion — flag; search for direct evidence |
| INSUFFICIENT | Do not annotate | Microarray alone, bulk proteomics alone, ChIP-seq alone, computational prediction alone, review statement without primary citation |

### Overexpression co-IP
Flag as OVEREXP ONLY if co-IP uses only overexpressed proteins; endogenous interaction
not confirmed.

### Reviews as input
A review may be used to identify biology and locate primary papers, but the review itself
**cannot** be the literatureReference on a Reaction. Trace to the primary paper.

### Evidence type slot
If the fundamental direct-evidence rule cannot be met, fill the **evidenceType** slot with an
ECO term and explain the inference in the summation. This is acceptable only to complete
an otherwise well-evidenced pathway.

### BBE with known steps
If a BBE represents a process whose full molecular details are known but deliberately
not curated here, those details may be annotated elsewhere in Reactome and linked via
the hasEvent attribute of the BBE.

---

## 6. SPECIES AND CHIMERIC REACTION RULES

Every Reactome annotation ultimately requires a **human** RLE. Where experimental
evidence is non-human, paired reactions are required.

### Definitions

**Human reaction:** All proteins are human. species = Homo sapiens. isChimeric = FALSE.

**Non-human reaction (Form A):** Experiment performed entirely in one non-human species.
- Create the non-human reaction (species = that species, isChimeric = FALSE)
- Create a paired **inferred human reaction** (species = Homo sapiens, isChimeric = FALSE,
  inferredFrom = the non-human reaction's stId)
- Non-human protein names: Capitalised (Jak2). Human: ALL-CAPS (JAK2).

**Chimeric reaction (Form B):** Experiment explicitly combined proteins from ≥2 species in
the same assay (e.g., human substrate + rabbit enzyme in vitro).
- Create the chimeric reaction (list ALL participating species, isChimeric = TRUE)
- Create a paired **inferred human reaction** (species = Homo sapiens, isChimeric = FALSE,
  inferredFrom = the chimeric reaction's stId)

### Decision table

| Experimental situation | Reaction type | isChimeric | inferredFrom |
|------------------------|--------------|-----------|-------------|
| Human proteins/cells only | Human reaction | FALSE | — |
| Single non-human species only | Non-human reaction | FALSE | — |
| + inferred human | Human reaction | FALSE | Non-human reaction |
| ≥2 species mixed in same assay | Chimeric reaction | TRUE | — |
| + inferred human | Human reaction | FALSE | Chimeric reaction |

### Key notes
- Do NOT create a non-human pathway and infer an entire human pathway from it.
  Create individual non-human reactions and infer individual human RLEs.
- The inferredFrom human RLE carries the same literatureReference as its non-human
  or chimeric source reaction.
- When creating a chimeric reaction for inference, ALL species must be listed in the
  species slot.
- relatedSpecies: used in host–pathogen interactions to tag the "bystander" (pathogen)
  species; NOT used for standard chimeric reactions.

---

## 7. PHYSICALENTITY CLASSES (relevant to RLE annotation)

### EntityWithAccessionedSequence (EWAS)
Protein, DNA, or RNA with a UniProt/Ensembl accession. Linked via referenceEntity to
ReferenceGeneProduct (proteins), ReferenceDNASequence, or ReferenceRNASequence.
- Each modified form and each cellular location = separate EWAS instance
- PTMs: use hasModifiedResidue slot (ModifiedResidue, GroupModifiedResidue,
  CrosslinkedResidue subclasses)
- Coordinate must be specified when known; use 1/−1 if uncertain

### Complex
Covalent or non-covalent association of ≥2 PhysicalEntities. Components listed in
hasComponent. Naming: colon-separated. Compartment = core compartment.

### DefinedSet
Well-characterised PhysicalEntities that are functionally indistinguishable. Members
linked by logical OR — any member can participate in the reaction.

### CandidateSet
Members (proven) + candidates (believed equivalent by phylogeny/domain structure but
not directly proven). Candidates annotated as PM5-level variants in disease context.

### SimpleEntity
Small molecule not genome-encoded (ATP, NAD+, Pi, water). Linked to ChEBI via
referenceEntity (ReferenceMolecule). Separate instance per compartment.

### Polymer
Indeterminate repeating units. repeatedUnit attribute holds the unit(s).

### OtherEntity
Structures that cannot or should not be described molecularly (e.g., cell membrane when
specific binding partner is unknown).

---

## 8. CATALYST AND REGULATION ANNOTATION

### CatalystActivity
Associates one PhysicalEntity with one GO_MolecularFunction.
- If the catalyst is a Complex and one component mediates the activity, specify that
  component as activeUnit (NOT the whole complex as activeUnit — the physicalEntity
  itself should never be listed as the activeUnit)
- If a PhysicalEntity enables multiple MolecularFunctions, create a separate
  CatalystActivity instance for each
- GO_MolecularFunction: use most specific term available; consult UniProt ontologies
  section or OLS (https://www.ebi.ac.uk/ols)

### Regulation
Added to the regulatedBy attribute of a ReactionLikeEvent.

| Class | Use |
|-------|-----|
| NegativeRegulation | Inhibitory effect of a regulator PhysicalEntity |
| PositiveRegulation | Stimulatory effect of a regulator PhysicalEntity |
| Requirement | PhysicalEntity without which event cannot occur |
| NegativeGeneExpressionRegulation | Direct inhibitory effect on a BBE gene expression event |
| PositiveGeneExpressionRegulation | Direct stimulatory effect on a BBE gene expression event |

- If the Regulator is a Complex, specific regulatory component(s) = activeUnit(s) of the
  Regulation instance
- For computational modelling: when regulator is a complex containing the target gene
  or mRNA, specify the transcription factor as activeUnit to prevent spurious predictions

---

## 9. GENE EXPRESSION REGULATION PATTERNS

### Pattern A — TF binding to DNA demonstrated (≥2 of 3 criteria met)
1. Binding elements in regulatory region + ChIP or EMSA evidence
2. TF level change correlates with target gene expression (reporter assay, qRT-PCR)
3. Mutation of TF binding sites affects target expression

Annotation: Two-step.
- **Step 1 (Reaction):** TF binds target gene DNA
- **Step 2 (BBE):** Gene expression: gene → protein (or mRNA if translational regulation
  will follow). Preceding event = Step 1.
- Regulation: PositiveGeneExpressionRegulation or NegativeGeneExpressionRegulation
  on Step 2; regulator = TF:gene complex; activeUnit = TF

Note: Show protein as output even for transcriptional regulation (we are protein-oriented).
Show mRNA as output of transcription BBE only if mRNA is input to another reaction
(e.g., miRNA regulation).

### Pattern B — No direct TF–DNA binding demonstrated
One criterion:
- TF level/activity change correlates with target gene expression

Annotation: Single BBE (gene → protein). Regulation = PositiveRegulation or
NegativeRegulation (general, not GeneExpression subclass).

### miRNA / translational regulation
- Validated by reporter assay OR co-IP of miRNA:mRNA + mRNA/protein level change
- Two-step: Step 1 = miRNA-RISC binds target mRNA; Step 2 = translation BBE (mRNA → protein)
- Preceding event: Step 1
- NegativeGeneExpressionRegulation on Step 2; regulator = RISC:mRNA complex;
  activeUnit = miRNA-RISC

---

## 10. SUMMATION RULES

- Free text describing the event and its biological context
- Cite **background** literature here (not primary evidence — primary evidence goes on
  the Reaction literatureReference slot)
- Any factual statement in the summation should be supported by a reference
- When an event is modified after release, update the summation to reflect the change
- For disease reactions with disputed or complex evidence, note this in summation

---

## 11. REACTION BALANCE

All molecules present as input must be present as output (including cofactors, byproducts).
Use the curator tool Imbalance Check QA to verify.

Exception: FailedReaction has inputs only, no outputs.

Cleavage reactions: output contains fragments of the input — these are flagged separately
by the QA tool and are not considered imbalances.

---

## 12. DISEASE RLE SPECIFICS (summary)

### FailedReaction (loss-of-function)
- Inputs: disease variant entity/complex/set + all WT co-inputs from normal reaction
- Outputs: none
- Required: disease tag, normalReaction, entityFunctionalStatus
- By convention: one and only one FailedReaction per parent disease pathway

### Gain-of-function disease RLEs
- Annotated as Reaction (not FailedReaction)
- Required: disease tag, entityFunctionalStatus
- normalReaction: fill if overlaid on WT diagram; leave empty if novel event
- Multiple RLEs allowed in a GOF pathway (propagate until disease entity no longer
  directly involved)

### EntityFunctionalStatus (EFS)
Three attributes:
- **diseaseEntity**: the variant EWAS/Complex/Set responsible for the phenotype
- **normalEntity**: the WT counterpart (required when normalReaction is specified)
- **functionalStatus**: FunctionalStatusType (gain/loss) + structuralVariant (SO term)

### Disease variant naming (HGVS-based, single-letter AA codes)
- Missense: GENE_W#N (e.g., MTR P1173L)
- Nonsense: GENE_W#* (e.g., BRCA2 R2318*)
- In-frame deletion: GENE_W#_W#del (e.g., HK1 H577_C672del)
- Duplication: GENE_W#_W#dup
- Insertion: GENE_W#_W#insXXX
- Indel: GENE_W#_W#delinsXXX
- Frameshift: GENE_W#Nfs*# (e.g., EXT1 L490Rfs*9)
- Fusion: GENE1(aa–aa)-GENE2(aa–aa) fusion

---

## 13. KEY DATA MODEL GLOSSARY DEFINITIONS (RLE-relevant)

**CatalystActivity:** Associates one physicalEntity with one GO_molecularFunction. If the
physicalEntity is a Complex, the catalytically active component is specified as activeUnit.

**Compartment:** A subset of GO_CellularComponent terms specifying non-overlapping
subcellular locations. If a physicalEntity occurs in >1 compartment, separate instances
are created for each location.

**GO_BiologicalProcess:** Local copy of GO BP ontology. Provides goBiologicalProcess
attribute for Events and Regulation instances.

**GO_CellularComponent:** Local copy of GO CC ontology. Provides compartment/location
attributes.

**GO_MolecularFunction:** Local copy of GO MF ontology. Provides activity attribute of
CatalystActivity.

**inferredFrom:** Points to the event in another species from which this event is inferred.
The cited event carries the primary experimental evidence; the inferred event carries only
inferredFrom.

**input:** The input PhysicalEntities of a ReactionLikeEvent, entered individually.

**isChimeric:** TRUE when an experiment explicitly combined proteins from ≥2 species in
the same assay.

**LiteratureReference:** Journal article with mandatory pubMedIdentifier (PMID). Author,
year, title, journal populated from PubMed.

**NegativeRegulation / PositiveRegulation / Requirement:** Regulation subclasses added
to regulatedBy attribute of RLEs.

**output:** The output PhysicalEntities of a ReactionLikeEvent, entered individually.

**precedingEvent:** Points to the immediately preceding RLE. RLE → RLE only
(never Pathway → RLE, never RLE → Pathway).

**ReactionLikeEvent:** Single-step molecular process converting inputs to outputs.

**regulatedBy:** Holds Regulation instances that describe stimulatory or inhibitory effects
on the RLE.

**relatedSpecies:** Tags the "bystander" (non-host) species in host–pathogen interactions.
Not used for standard chimeric reactions.

**species:** The species in which the reaction is occurring. Always Homo sapiens for
human Reactome curation (exception: non-human reactions created for inference).

**Summation:** Free-text description of an Event or PhysicalEntity. Background citations
(not primary evidence) are linked here.

---

## 14. QUICK REFERENCE: WHAT GOES WHERE

| Information | Where to record |
|-------------|----------------|
| Primary experimental evidence paper (PMID) | literatureReference on the Reaction |
| Background/context papers | literatureReference on the Summation |
| Catalyst identity + GO MF | catalystActivity on the Reaction |
| Inhibitor/activator of the reaction | regulatedBy (Regulation instance) |
| Non-human evidence for a human event | inferredFrom on the inferred human Reaction |
| Mixed-species in vitro experiment | isChimeric = TRUE on the chimeric Reaction + paired inferred human Reaction |
| PTMs on a protein | hasModifiedResidue on the EWAS |
| Disease variant | hasModifiedResidue (GeneticallyModifiedResidue subclass) on the variant EWAS |
| Disease classification | disease slot on the RLE and on the variant PhysicalEntity |
| WT counterpart for a disease RLE | normalReaction on the disease RLE |
| Gain/loss-of-function description | entityFunctionalStatus on the disease RLE |

---

*Source documents: Curator Guide V94 (pts 1 & 2); Data Model Glossary V90.*
*This reference covers RLE/reaction annotation only. Curator Tool operation, QA procedures,*
*pathway diagram drawing, drug curation mechanics, cell lineage paths, and release*
*procedures are excluded.*
