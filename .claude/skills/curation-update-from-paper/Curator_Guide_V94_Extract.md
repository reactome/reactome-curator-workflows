# Curator Guide V94 — extract for `/curation-update-from-paper`

**What this is.** A condensation of the sections of `Curator_Guide_V94.pdf`
(283 pp, 17 MB) that this skill needs and that
`Reactome_RLE_Annotation_Reference_V94.md` does **not** already cover. It exists
so the skill is self-contained and zip-portable; the full Guide is 17 MB and
cannot travel inside every skill.

**Provenance.** Extracted from `Curator_Guide_V94.pdf` with `pypdf`, section by
section; page numbers below are the PDF's own and are given so any statement can
be checked against the source. This is a condensation, **not a replacement** —
where it is silent, or where a decision turns on wording, open the Guide.

**What is deliberately out of scope**, because the RLE reference covers it:
event class hierarchy, mandatory RLE fields, general naming, compartments,
evidence classes, catalyst/regulation, summation rules, reaction balance.
Also out of scope because this skill never does it: Curator Tool UI, diagram
drawing, cell lineage paths, QA runs, release procedure.

---

## 1. Updating existing content (pp. 3–5)

This is the rule this skill most often brushes against, since every run is a
proposal against an already-curated pathway.

> "Be extremely careful changing ANY released instance. This should almost never
> be done unless new information has become available. Be absolutely sure to
> check any/all referrers of the instance being changed (entity/event) and make
> sure that those changes are relevant in ALL referrers."

> "Never change the compartment of an existing entity as that will change the
> compartment everywhere the entity is used."

**Consequences for a proposal:**

- Never propose editing a released instance casually. If the paper genuinely
  warrants it, say so explicitly, name the instance, and flag that referrers
  must be checked first — that check is the curator's, in the Curator Tool.
- Never propose changing an existing entity's compartment. If the new biology
  needs a different compartment, that is a **new entity**, not an edit.
- "Refine the output of event X" is a heavier request than it sounds. Put it in
  the open questions, not in the body as a settled recommendation.

## 2. Evidence, references and inference (pp. 3–5, 15–17)

> "In general any time you make a statement in your summation you should include
> a reference... otherwise the reviewer can't go and check. It also shows that it
> is an established fact, not your own finding or opinion."

High-throughput data alone is not sufficient evidence for an event:

> "you should NOT include events based solely on microarray, proteomics or
> similar high throughput data, unless either 1) an expert author has indicated
> that they believe the results are correct and represent the current consensus,
> or 2) The results are a meta-data analysis that combines several independent
> studies."

**Inferred steps are allowed, under conditions.** A reaction with no direct
experimental demonstration may be included:

> "as long as somewhere in subsequent events there is some kind of experimental
> data that suggests your inferred events must logically occur to get you to that
> point. It's essential that you explain the inference you have made... You must
> include citations for the characterized mechanism that allows you to make the
> inference."

> "you should NOT create a pathway in non-human species and use that to infer a
> human pathway. Instead, create individual non-human reactions and use those to
> infer the human RLEs where evidence for the RLE is missing."

So: a mechanistic gap-filling step is legitimate if the proposal states the
inference, cites the characterised mechanism it rests on, and flags that an
expert should approve it. An unexplained gap-filler is not.

## 3. Host–pathogen interactions (pp. 219–226)

**Read this before proposing anything in an infection pathway.** Its species
rules override the generic species/chimeric decision table, and they are the
single most commonly misapplied part of the Guide in this skill's domain.

### 3.1 The disease / normal boundary

> "We have set the disease / normal boundary by asking what the outcome of the
> host-pathogen interaction is. If the host wins and the pathogen is really
> neutralized, that counts as normal. If the pathogen wins to cause overt
> infection or to establish a stable latent state that could result in disease
> later, that counts as disease."

Entry and growth of a pathogen inside the host cell counts as **disease** and
belongs in the Infectious Diseases module.

### 3.2 Species and relatedSpecies — the rule to get right

> "The 'species' slot on the event identifies **the environment where the
> reaction is happening**. This should almost always be human for human Reactome
> curation."

> "In disease or immune system processes that involve host-pathogen interactions
> the host would be listed as the 'species' in the records of RLE and complexes,
> which are formed by host and pathogen entities."

> "The 'related species' is used to tag the source (or sources) of
> genome-encoded entities from 'elsewhere' that act as 'bystanders' in a
> process. In disease or immune system processes, the pathogen(s) would be
> listed as 'relatedSpecies' in RLEs and complex instances."

**The rule, stated generally:** when two species take part in one reaction, the
**host** goes in `species` and the **other organism** goes in `relatedSpecies`.

| Slot | Value |
|---|---|
| `species` | the **host** — Homo sapiens for human curation, but the rule is about the host; released content also has `Gallus gallus` as host |
| `relatedSpecies` | the **other species** — in every released case so far, the pathogen |

**Except for a chimeric reaction.** One built for inference — entities from
several species combined in a single assay, usually in vitro — lists **all**
species in `species` and sets `isChimeric`, and does not use `relatedSpecies`.
Two species in a reaction therefore always means one treatment or the other,
and never a second species sitting in `species` without `isChimeric`.

This is not a departure from the Guide to be flagged — it *is* the Guide. A
proposal that sets `species = Homo sapiens` and omits `relatedSpecies` is
**incomplete**, not merely unconventional. Check the branch with gk-central and
match it; neighbouring events will already carry both.

Note also:

- `relatedSpecies` set on an RLE "should be assigned to a first parent pathway."
- A chimeric reaction built for inference lists **ALL** species in `species`.
- A complex of only SimpleEntities has **no** species.
- A complex of a pathogen protein plus a SimpleEntity or OtherEntity takes the
  **pathogen** species and no relatedSpecies.
- A set whose members span several pathogen species lists **all** of them.
- A species new to Reactome needs an abbreviation assigned — contact Peter
  D'Eustachio.

### 3.3 Compartments for entities of microbial origin

Reactome departs from GO here, deliberately:

> "In contrast to GO, we use normal cell terms (for example, 'endoplasmic
> reticulum membrane' and not 'host cell endoplasmic reticulum membrane') to
> localize virus- or bacteria- or other pathogen-derived entities in an infected
> cell."

GO's `host cell ...` terms are for PAMP locations in the *pathogen's own*
compartments (e.g. "cell wall", "virion membrane"). Inside an infected host
cell, use the normal-cell term.

### 3.4 Disease term

> "For all kinds of pathogen entities in human (or other host) pathways the
> disease slots are filled in with a value corresponding to the disease they
> would cause if not neutralized."

This colours pathogenic entities red whether they are causing disease or being
neutralised. Assigning disease to complexes and reactions depends on the
outcome of the interaction (§3.1).

### 3.5 Physical entities

- Genomic, transcript and protein sequences **of microbial origin** are EWASs
  with a `referenceEntity` carrying an NCBI nucleotide, ENSEMBL, EMBL or UniProt
  identifier. Microbial nucleic acids may instead be direct children of
  `GenomeEncodedEntity` with the microbial species assigned.
- Molecules such as bacterial LPS, peptidoglycans or fungal mannans are
  `SimpleEntity` with a `referenceMolecule` carrying a ChEBI identifier.
- Host–pathogen interactions are usually captured as a **binding** between the
  host PE and a pathogen-associated molecular pattern (PAMP).

## 4. Retiring or restructuring existing events (pp. 239–244)

Relevant whenever a proposal's answer to "how does this relate to the existing
events?" is *supersede* rather than *add alongside*.

**Check referrers first, always:**

> "If you locally modify or delete an instance you checked out from gk_central,
> it will also be modified/deleted in gk_central when you synchronize. You must
> ALWAYS CHECK FIRST that the instance you intend to modify/delete is not in use
> elsewhere... If it has any you didn't know about, do not modify or delete it!"

**A released instance cannot just be switched off:**

> "A `_deleted` instance MUST be created any time a released Event or Entity is
> retired/deleted from the database. For example, when event restructuring
> occurs, any previously released events should NOT simply be flipped to
> do_release false. When this happens, this instance 'disappears without a
> trace' to users."

The order is: replace the instance in all referrers where relevant, **then**
delete it, creating a `_deleted` instance that records a reason, a replacement
where one exists, and an explanation in `curatorComment`. The `reason` attribute
is mandatory; "Killed and not replaced" is for instances that are simply wrong,
and requires finding and fixing every diagram that used them.

> "if you are deleting a pathway because it has been restructured and that
> pathway has a DOI, it is essential to specify the replacement instances in the
> `_deleted` instance. The historic author and reviewer instances should also be
> transferred to the replacement instance."

Whether an instance has been released is determined by the `released` attribute
of its stableID — not by whether it is visible on reactome.org today.

**Consequence for a proposal:** never present "supersede the existing events" as
a simple swap. It carries a referrer check, a `_deleted` instance per retired
event, diagram fixes, and DOI/credit transfer. Say so where the option is
offered.

---

## Where to go for what this does not cover

| Need | Source |
|---|---|
| RLE anatomy, naming, compartments, evidence classes | `Reactome_RLE_Annotation_Reference_V94.md` |
| PSI-MOD → EWAS name prefixes | `ptm_prefixes.md` |
| Disease pathway structure, EntityFunctionalStatus, disease entity annotation | Curator Guide pp. 148–218 |
| Drug curation, Guide to Pharmacology interaction file | Curator Guide pp. 226–236 |
| Curator Tool procedure, diagram drawing, QA checks | Curator Guide pp. 17–130, 244–258 |
| Published controlled vocabulary, citable | `bau060.pdf` (Jupe et al. 2014) |
