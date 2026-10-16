# gk_central and OLS checks for /review-internal

Companion to `SKILL.md` ("Live database checks"). Every query here was run against
the gk_central copy on 2026-09-23 on three pathways: R-HSA-9995698 (The CARD8
inflammasome, 13 events), R-HSA-5083629 (a disease pathway with a FailedReaction)
and R-HSA-9973849 (HHV8 Infection, ~480 events; all eleven queries together take
about 5 seconds).

Run each query with `mcp__gk-central__read_neo4j_cypher`, passing the pathway's
ST_ID as a parameter: `params: {"stId": "R-HSA-XXXXXXX"}`. All queries are
read-only and scoped to the pathway under review.

## Schema facts these queries rely on

gk_central is built from the editing database, so a few names differ from the
released graph database. Don't "correct" them:

- Hierarchy: `(pathway)-[:hasEvent*]->(event)`.
- Order: `(following)-[:precedingEvent]->(preceding)`.
- Participants: `input`, `output`; catalysts via
  `(rle)-[:catalystActivity]->(ca)-[:physicalEntity]->(entity)` and
  `(ca)-[:activity]->(GO molecular function)`; regulation via
  `(rle)-[:regulatedBy]->(reg)-[:regulator]->(entity)`.
- GO terms: `goBiologicalProcess`, `activity`; the ID is in `identifier`
  **without** the `GO:` prefix.
- Literature: `literatureReference` → `LiteratureReference.pubMedIdentifier`
  (integer), plus `year`, `journal`, `title`.
- Credits: `(InstanceEdit)-[:authored|reviewed|internalReviewed|revised]->(event)`.
  The InstanceEdit's `displayName` is the person ("Weiser, JD") and `dateTime` the date.
- Inference: `(source event)-[:inferredTo]->(inferred event)` — the reverse of the
  released database's `inferredFrom`.
- Release flag: `doRelease` is `true`, `false` or absent (null).
- Events carry no `speciesName`; use `(e)-[:species]->(sp)`.
- Disease: `(x)-[:disease]->(Disease)`, DOID number in `identifier`;
  `(FailedReaction)-[:normalReaction]->(rle)`;
  `(rle)-[:entityFunctionalStatus]->()-[:functionalStatus]->()-[:functionalStatusType]->(type)`.
- Drugs: `ProteinDrug` / `ChemicalDrug` / `RNADrug` with
  `referenceEntity` → `ReferenceTherapeutic` (Guide to Pharmacology ID in `identifier`).

If a query errors on a name, run `mcp__gk-central__get_neo4j_schema` or
`RETURN keys(n)` on one node before changing it.

---

## Q0 — Freshness (metadata header)

gk_central is refreshed nightly. The newest edit shows how current the copy is.

```cypher
// Q0
MATCH (ie:InstanceEdit) RETURN max(ie.dateTime) AS newestEdit
```

## Q1 — Pathway overview (Executive Summary, Sections 2, 3, 5)

```cypher
// Q1
MATCH (p:Pathway {stId: $stId})
OPTIONAL MATCH (p)-[:species]->(sp)
OPTIONAL MATCH (p)-[:goBiologicalProcess]->(go)
OPTIONAL MATCH (p)-[:disease]->(d)
OPTIONAL MATCH (p)-[:literatureReference]->(lr)
OPTIONAL MATCH (ie)-[r:authored|reviewed|internalReviewed|revised]->(p)
OPTIONAL MATCH (m:InstanceEdit)-[:modified]->(p)
RETURN p.stId AS stId, p.displayName AS name, p.doRelease AS doRelease,
       collect(DISTINCT sp.displayName) AS species,
       collect(DISTINCT 'GO:' + go.identifier + ' ' + go.displayName) AS goBP,
       collect(DISTINCT d.displayName + ' (DOID:' + d.identifier + ')') AS disease,
       collect(DISTINCT lr.pubMedIdentifier) AS pmids,
       collect(DISTINCT type(r) + ': ' + ie.displayName) AS credits,
       max(m.dateTime) AS lastModified
```

- No row → the ST_ID isn't in gk_central: stop the database checks and say so.
- `name` ≠ the report's pathway name → the report may predate a rename.
- Empty `goBP` → Section 2 rule (a) applies.

## Q2 — Event inventory (Overall Notes, Sections 1, 2, 5)

```cypher
// Q2
MATCH path = (p:Pathway {stId: $stId})-[:hasEvent*]->(e:Event)
OPTIONAL MATCH (e)-[:goBiologicalProcess]->(go)
OPTIONAL MATCH (src:Event)-[:inferredTo]->(e)
OPTIONAL MATCH (src)-[:species]->(srcSp)
OPTIONAL MATCH (e)-[:literatureReference]->(lr)
OPTIONAL MATCH (m:InstanceEdit)-[:modified]->(e)
OPTIONAL MATCH (au:InstanceEdit)-[:authored]->(e)
OPTIONAL MATCH (rv:InstanceEdit)-[:reviewed|internalReviewed]->(e)
RETURN e.stId AS stId, e.schemaClass AS class, e.displayName AS name,
       min(length(path)) AS depth, e.doRelease AS doRelease,
       collect(DISTINCT 'GO:' + go.identifier + ' ' + go.displayName) AS goBP,
       collect(DISTINCT srcSp.displayName) AS inferredFromSpecies,
       count(DISTINCT lr) AS nRefs, count(DISTINCT au) AS nAuthored,
       count(DISTINCT rv) AS nReviewed, max(m.dateTime) AS lastModified
ORDER BY depth, name
```

- Events here and not in the report → the report may be an unmerged multi-part
  export, or older than the database.
- Events in the report and not here → removed or moved since export.
- `lastModified` later than the report's export date → the curation changed after
  the report was generated.
- `nRefs = 0` on a non-inferred event → Section 3 (every event needs literature
  support).
- `inferredFromSpecies` non-empty → apply the inferredFrom evidence rules (Section 5).
- `nAuthored = 0` → missing author attribution (Section 5). `nReviewed = 0` is
  expected before external review; note it, don't flag it.
- `doRelease` false or null is normal for work in progress — not a finding.
- More than ~150 rows → run Q3 and Q4 per subpathway (pass the subpathway's
  ST_ID) as you write each section, rather than all at once.

## Q3 — Literature per event (Section 3)

```cypher
// Q3
MATCH (p:Pathway {stId: $stId})-[:hasEvent*0..]->(e:Event)
WITH DISTINCT e
OPTIONAL MATCH (e)-[:literatureReference]->(lr:LiteratureReference)
RETURN e.stId AS stId, e.displayName AS name,
       collect(DISTINCT {pmid: lr.pubMedIdentifier, year: lr.year, journal: lr.journal}) AS refs
ORDER BY name
```

Compare with each reference list in the report. `verify_pmids.py` remains the
authority on whether a PMID matches its citation; this query shows what is
actually attached to each event.

## Q4 — Reaction participants (Sections 1, 7)

```cypher
// Q4
MATCH (p:Pathway {stId: $stId})-[:hasEvent*]->(e:ReactionLikeEvent)
WITH DISTINCT e
OPTIONAL MATCH (e)-[:input]->(i)
OPTIONAL MATCH (e)-[:output]->(o)
OPTIONAL MATCH (e)-[:catalystActivity]->(ca)-[:physicalEntity]->(c)
OPTIONAL MATCH (ca)-[:activity]->(mf)
OPTIONAL MATCH (e)-[:regulatedBy]->(reg)-[:regulator]->(rgr)
RETURN e.stId AS stId, e.schemaClass AS class, e.displayName AS name,
       collect(DISTINCT i.displayName) AS inputs,
       collect(DISTINCT o.displayName) AS outputs,
       collect(DISTINCT c.displayName + ' [GO:' + mf.identifier + ']') AS catalysts,
       collect(DISTINCT reg.schemaClass + ': ' + rgr.displayName) AS regulators
ORDER BY name
```

These are the entity names as stored — authoritative for Section 7 and for
reading reaction diagrams in the report.

## Q5 — Entity-chain breaks (Section 1.3)

For every preceding-event pair, checks whether an output of the preceding event
is an input, catalyst or regulator of the following one — directly, or through
set membership (an output that is a member of an input set counts, and vice
versa). **Returns only the pairs with no link.**

```cypher
// Q5
MATCH (p:Pathway {stId: $stId})-[:hasEvent*]->(next:ReactionLikeEvent)-[:precedingEvent]->(prev:ReactionLikeEvent)
WITH DISTINCT prev, next
OPTIONAL MATCH (prev)-[:output]->(o)
WITH prev, next, collect(DISTINCT o) AS outs
OPTIONAL MATCH (next)-[:input]->(i)
WITH prev, next, outs, collect(DISTINCT i) AS ins
OPTIONAL MATCH (next)-[:catalystActivity]->()-[:physicalEntity]->(c)
WITH prev, next, outs, ins, collect(DISTINCT c) AS cats
OPTIONAL MATCH (next)-[:regulatedBy]->()-[:regulator]->(r)
WITH prev, next, outs, ins, ins + cats + collect(DISTINCT r) AS uses
WHERE NONE(o IN outs WHERE ANY(u IN uses WHERE u = o
        OR exists((u)-[:hasMember|hasCandidate*1..3]->(o))
        OR exists((o)-[:hasMember|hasCandidate*1..3]->(u))))
RETURN prev.stId AS precedingId, prev.displayName AS preceding,
       [o IN outs | o.displayName] AS outputs,
       next.stId AS followingId, next.displayName AS following,
       [i IN ins | i.displayName] AS followingInputs
ORDER BY precedingId
```

A row is a candidate 1.3 finding: the preceding event's output never reaches
the following event. Check it against the text rules in 1.3 (PTM state,
oligomer state, complex vs subunits) — the usual cause is that the following
event uses an unmodified or unassembled form. Some rows are legitimate
(a preceding event that only supplies context, e.g. an expression event whose
product enters via a different entity); say so rather than flagging those.

## Q6 — Reactions with no ordering (Section 1)

Reactions that neither follow nor precede any event. On a large pathway this can
be a long list; report the count and representative examples, grouped by
subpathway.

```cypher
// Q6
MATCH (p:Pathway {stId: $stId})-[:hasEvent*]->(e:ReactionLikeEvent)
WITH DISTINCT e
WHERE NOT (e)-[:precedingEvent]->() AND NOT ()-[:precedingEvent]->(e)
RETURN e.stId AS stId, e.displayName AS name
```

## Q7 — Name hygiene (Section 7)

Leading, trailing or doubled spaces in event and entity names.

```cypher
// Q7
MATCH (p:Pathway {stId: $stId})-[:hasEvent*0..]->(e:Event)
WITH DISTINCT e
OPTIONAL MATCH (e)-[:input|output|catalystActivity|physicalEntity|regulatedBy|regulator*1..2]->(pe:PhysicalEntity)
WITH collect(DISTINCT e) + collect(DISTINCT pe) AS xs
UNWIND xs AS x
WITH DISTINCT x
WHERE x.displayName <> trim(x.displayName) OR x.displayName CONTAINS '  '
RETURN x.stId AS stId, x.schemaClass AS class, '[' + x.displayName + ']' AS nameInBrackets
```

## Q8 — Protein entities: genes, coordinates, modifications (Section 7.1)

```cypher
// Q8
MATCH (p:Pathway {stId: $stId})-[:hasEvent*]->(e:ReactionLikeEvent)-[:input|output|catalystActivity|physicalEntity|regulatedBy|regulator*1..2]->(pe:PhysicalEntity)
WITH DISTINCT pe
MATCH (pe)-[:hasComponent|hasMember|hasCandidate|repeatedUnit*0..4]->(leaf:EntityWithAccessionedSequence)
WITH DISTINCT leaf
OPTIONAL MATCH (leaf)-[:referenceEntity]->(ref)
OPTIONAL MATCH (leaf)-[:hasModifiedResidue]->(mr)
WITH leaf, ref, collect(DISTINCT mr.displayName) AS modifications,
     apoc.text.regexGroups(leaf.displayName, '\\((\\d+)-(\\d+)\\)') AS g
WITH leaf, ref, modifications,
     size(g) > 0 AND (leaf.startCoordinate IS NULL OR leaf.endCoordinate IS NULL
       OR toInteger(g[0][1]) <> leaf.startCoordinate
       OR toInteger(g[0][2]) <> leaf.endCoordinate) AS coordinateMismatch,
     ref IS NULL AS noReference
WHERE coordinateMismatch OR noReference OR $all = true
RETURN leaf.stId AS stId, leaf.displayName AS name, ref.identifier AS uniprot,
       ref.geneName[0] AS primaryGene, leaf.startCoordinate AS start, leaf.endCoordinate AS end,
       modifications, coordinateMismatch, noReference
ORDER BY coordinateMismatch DESC, noReference DESC, name
```

Pass `params: {"stId": ..., "all": false}` to get only problem rows (the default
for a review); `"all": true` lists every protein entity — use it only on small
pathways or one subpathway at a time.

- `coordinateMismatch = true` → the residue range in the name disagrees with the
  stored start/end coordinates (or one is missing). Flag in 7.1.
- `noReference = true` → the protein has no UniProt reference entity.
- `primaryGene` is the UniProt primary gene symbol — the basis for EWAS names.
- `modifications` lists the modified residues — check against the PTM prefix in
  the name (7.1, `ptm_prefixes.md`).

## Q9 — Small molecules (Section 7.3)

```cypher
// Q9
MATCH (p:Pathway {stId: $stId})-[:hasEvent*]->(e:ReactionLikeEvent)-[:input|output|catalystActivity|physicalEntity|regulatedBy|regulator*1..2]->(pe:PhysicalEntity)
WITH DISTINCT pe
MATCH (pe)-[:hasComponent|hasMember|hasCandidate*0..4]->(sm:SimpleEntity)
WITH DISTINCT sm
OPTIONAL MATCH (sm)-[:referenceEntity]->(ref)
RETURN sm.stId AS stId, sm.displayName AS name,
       ref.databaseName + ':' + ref.identifier AS id, ref.name AS referenceNames
ORDER BY name
```

Compare `name` with `referenceNames` and `Small_molecule_renaming.xlsx`. A
missing `id` is a missing ChEBI reference.

## Q10 — Disease and drug annotation (Standards: disease, drugs)

Run only when Q1 or Q2 shows disease annotation, or Q4 shows drug entities.

```cypher
// Q10
MATCH (p:Pathway {stId: $stId})-[:hasEvent*0..]->(e:Event)
WITH DISTINCT e
OPTIONAL MATCH (e)-[:disease]->(d)
OPTIONAL MATCH (e)-[:normalReaction]->(nr)
OPTIONAL MATCH (e)-[:entityFunctionalStatus]->()-[:functionalStatus]->()-[:functionalStatusType]->(fst)
OPTIONAL MATCH (e)-[:input|output|catalystActivity|physicalEntity|regulatedBy|regulator*1..2]->(dr:Drug)
OPTIONAL MATCH (dr)-[:referenceEntity]->(tr)
WITH e, collect(DISTINCT d.displayName + ' (DOID:' + d.identifier + ')') AS disease,
     nr, collect(DISTINCT fst.displayName) AS functionalStatus,
     collect(DISTINCT dr.displayName + ' [' + coalesce(tr.databaseName + ':' + tr.identifier, 'NO REFERENCE') + ']') AS drugs
WITH e, disease, nr, functionalStatus, drugs,
     [x IN [
       CASE WHEN e.schemaClass = 'FailedReaction' AND nr IS NULL THEN 'FailedReaction without normalReaction' END,
       CASE WHEN e.schemaClass = 'FailedReaction' AND size(functionalStatus) = 0 THEN 'FailedReaction without entityFunctionalStatus' END,
       CASE WHEN e.schemaClass = 'FailedReaction' AND size(disease) = 0 THEN 'FailedReaction without disease' END,
       CASE WHEN ANY(d IN drugs WHERE d ENDS WITH '[NO REFERENCE]') THEN 'drug without Guide to Pharmacology reference' END
     ] WHERE x IS NOT NULL] AS problems
WHERE size(problems) > 0
RETURN e.stId AS stId, e.schemaClass AS class, e.displayName AS name, problems,
       disease, nr.stId AS normalReaction, functionalStatus, drugs
ORDER BY class, name
```

Returns only events with a problem, named in `problems`. No rows means the
disease and drug checks found nothing to flag. Whether the pathway carries disease
annotation at all comes from Q1/Q2.

---

## OLS checks (Section 2)

With the `ols` tools:

1. **Every GO term in use** (from Q1, Q2, and catalyst activities in Q4): call
   `mcp__ols__get_term_info` with `id: "GO:XXXXXXX"`. Flag `is_obsolete: true` as
   HIGH. The result may come from an ontology that imports GO (e.g.
   `ontology_name: "ado"`); the label still applies.
2. **Every GO term you recommend**: confirm it exists with
   `mcp__ols__search_terms` (`query`: the label, `ontology: "go"`,
   `exact_match: true`) or `get_term_info`, and use the label OLS returns. Don't
   recommend an ID OLS doesn't return.
3. **Redundant reaction terms (rule b)**: for a reaction's BP term, call
   `mcp__ols__get_term_ancestors` (`term_iri`:
   `http://purl.obolibrary.org/obo/GO_XXXXXXX`, `ontology: "go"`). A reaction term
   equal to the pathway's term is redundant. A reaction term that is a *child* of
   the pathway's term is acceptable and more specific.
4. **Specificity**: `mcp__ols__get_term_children` on a broad term shows whether a
   more specific child fits (Standards: prefer child terms).
