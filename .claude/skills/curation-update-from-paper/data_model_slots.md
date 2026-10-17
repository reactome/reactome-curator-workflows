# Which slots actually get filled — measured, not remembered

**What this is.** Slot occupancy across released gk_central content, with the
queries that produced it. It answers "does an RLE normally carry this?" with a
number instead of a recollection, which is the question a proposal keeps
needing and which no glossary answers.

**Why it exists.** The data model is documented three times over (Glossary PDF,
RLE reference §13, Curator Guide Appendix C5) and that did not stop this skill
from proposing `goBiologicalProcess` on every reaction — a slot only 5% of real
reactions carry — or from omitting `relatedSpecies` on a host-pathogen pathway
where every neighbouring event had it. Prose says what a slot *means*. This
says whether curators *use* it.

**Snapshot taken 2026-10-17** against the nightly gk_central copy. Re-run the
queries below when the numbers matter; they are cheap. Percentages are of
released instances (`doRelease = true`) for events, of all instances for
physical entities.

---

## ReactionLikeEvent — 21,651 released

| Slot | % | Read as |
|---|---|---|
| `stableIdentifier` | 100 | automatic |
| `species` | 99 | **always** — the environment the reaction occurs in |
| `compartment` | 98 | **always** |
| `input` | 98 | **essentially always** |
| `output` | 97 | **essentially always** |
| `summation` | 95 | **expected** |
| `reviewStatus` | 88 | set by the review process, not the proposal |
| `literatureReference` | 86 | **expected** — the gap is mostly inferred events |
| `precedingEvent` | 60 | common, not required |
| `catalystActivity` | 41 | only where there is a catalyst |
| `regulatedBy` | 15 | only where there is a regulator |
| `inferredTo` | 13 | orthology inference |
| `crossReference` | 9 | |
| `disease` | 9 | |
| `relatedSpecies` | 6 | **but see below — 82% of these are disease events** |
| `goBiologicalProcess` | **5** | **pathway-level slot. See below.** |
| `entityFunctionalStatus` | 3 | disease RLEs |
| `normalReaction` | 3 | disease RLEs |

```cypher
MATCH (e:ReactionLikeEvent) WHERE e.doRelease = true
WITH count(e) AS total
MATCH (e2:ReactionLikeEvent)-[r]->() WHERE e2.doRelease = true
WITH total, type(r) AS rel, count(DISTINCT e2) AS n
RETURN rel, n, toInteger(100.0*n/total) AS pct ORDER BY n DESC
```

## Pathway — 3,568 released

| Slot | % |
|---|---|
| `species` | 100 |
| `hasEvent` | 98 |
| `summation` | 97 |
| `reviewStatus` | 86 |
| `literatureReference` | 85 |
| **`goBiologicalProcess`** | **48** |
| `compartment` | 33 |
| `disease` | 22 |
| `normalPathway` | 13 |
| `figure` | 12 |
| `relatedSpecies` | 6 |

Same query with `:Pathway`.

### `goBiologicalProcess` belongs to the pathway

**48% of pathways, 5% of reactions.** A reaction's molecular function is
carried by `catalystActivity` → GO MF; the biological process is a property of
the pathway the reaction sits in.

So: **do not propose a GO BP term per reaction.** Propose one for the new
subpathway, and leave the reactions without one unless there is a specific
reason. Inventing seven reaction-level GO BP labels is how three non-existent
GO terms entered the rotavirus draft.

### `relatedSpecies`: the second species in a two-species reaction

**The rule.** When two species take part in one reaction, the **host** is the
`species` and the **other organism** is the `relatedSpecies`. For human
curation the host is Homo sapiens, but the rule is about the host, not about
humans — released content includes `Gallus gallus` as `species` with
`Infectious bronchitis virus` as `relatedSpecies`.

**The one exception.** A **chimeric** reaction built for inference — entities
from several species combined in one assay, usually in vitro — lists **all**
species in the `species` slot and sets `isChimeric`, instead of using
`relatedSpecies` (Curator Guide, `Curator_Guide_V94_Extract.md` §3.2). So two
species in a reaction means one of two treatments, never a bare second species
in `species`:

| Situation | `species` | `relatedSpecies` |
|---|---|---|
| Host and another organism interacting | the host | the other organism |
| Chimeric construct for inference | **all** species | — (set `isChimeric`) |

**What it is used for in practice.** 1,340 released RLEs carry it, across **49
distinct values — every one a pathogen**: viruses, bacteria, *Candida
albicans*, *Leishmania major*, *Plasmodium falciparum*. 1,099 of those events
(82%) are `isInDisease`; the remaining 18% are mostly innate-immune recognition
where the host prevails, which the Guide classes as normal rather than disease.

So the slot's definition is general but its exercise so far is entirely
host–pathogen. A two-species reaction of another kind is not wrong, just
unprecedented — propose it and say so.

The 6% global figure is not permission to skip the slot: it is low because most
of Reactome is single-species. **Within an infection branch it is the norm**,
so check the branch rather than the global number:

```cypher
MATCH (p:Pathway {stId:$stId})-[:hasEvent*]->(e:ReactionLikeEvent)
OPTIONAL MATCH (e)-[:species]->(s)
OPTIONAL MATCH (e)-[:relatedSpecies]->(rs)
RETURN e.stId, e.displayName,
       collect(DISTINCT s.displayName)  AS species,
       collect(DISTINCT rs.displayName) AS relatedSpecies
```

## PhysicalEntity classes

| Class | n | Slots at ≥10% |
|---|---|---|
| `EntityWithAccessionedSequence` | 68,850 | `species` 99, `referenceEntity` 99, `compartment` 88, `hasModifiedResidue` 25, `disease` 11 |
| `Complex` | 27,327 | `compartment` 99, `species` 99, `hasComponent` 99, `literatureReference` 15 |
| `DefinedSet` | 9,525 | `compartment` 99, `hasMember` 98, `species` 90 |
| `SimpleEntity` | 9,341 | `compartment` 99, `referenceEntity` 99, `crossReference` 16 |

```cypher
UNWIND ['EntityWithAccessionedSequence','Complex','DefinedSet','SimpleEntity'] AS cls
MATCH (p) WHERE cls IN labels(p)
WITH cls, collect(p) AS ps, count(p) AS total
UNWIND ps AS p2 MATCH (p2)-[r]->()
WITH cls, total, type(r) AS rel, count(DISTINCT p2) AS n
WHERE n > total/10
RETURN cls, rel, toInteger(100.0*n/total) AS pct, total ORDER BY cls, pct DESC
```

Two things to take from this table:

- **`SimpleEntity` carries no species** — it does not appear at all, at any
  threshold. This matches the Guide: a complex of only SimpleEntities has no
  species listed. Do not propose a species on a small molecule.
- **`referenceEntity` is effectively mandatory** on EWAS (99%) and SimpleEntity
  (99%). An EWAS without a UniProt/ENSEMBL reference, or a SimpleEntity without
  ChEBI, is incomplete — flag it PENDING CURATOR VERIFICATION rather than
  omitting the slot silently.

---

## How this is enforced

`build_update_doc.py` checks the two rules above and prints a **data model
check** alongside the conformational-change check:

- `go_bp` set on a proposed reaction → advisory, with the 5%/48% split quoted.
- Some events carrying `related_species` and others not → advisory, since a
  branch is either host-pathogen or it is not.
- An infection-shaped proposal with no `related_species` anywhere → advisory.

Advisory rather than blocking: each has legitimate exceptions, and a proposal
is for a curator to rule on. But none should reach the curator unnoticed.
