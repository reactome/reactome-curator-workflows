# Resolving proposed values against the data model

**The principle.** A value in a proposal is either *resolved against the
database* or *flagged for the curator* — never asserted because it sounds
right. Preference is not a mechanism; a query is.

**The limit, which matters as much as the principle.** A query settles
**identity and existence**. It cannot settle **suitability**. "Does
`GO:0022829` exist and what is its label?" is answerable by machine. "Is a
viral perforin-like pore a *wide pore channel activity*?" is not — that is a
curator's judgement about fit, and dressing it up as resolved is worse than
leaving it open.

So every proposed value lands in exactly one of three states, and the state has
to be *earned*:

| State | Meaning | How it is earned |
|---|---|---|
| `RESOLVED` | identity confirmed | a query returned exactly one match; record the identifier |
| `AMBIGUOUS` | query ran, several candidates | record all of them, let the curator pick |
| `JUDGEMENT` | identity fine, fit is the question | say what the query found and why it does not settle it |

`PENDING CURATOR VERIFICATION` with no query behind it is none of these. It
means the work was not done.

---

## Taxonomy — species and relatedSpecies

```cypher
MATCH (s) WHERE (s:Species OR s:Taxon)
  AND toLower(s.displayName) CONTAINS toLower($name)
OPTIONAL MATCH (s)-[:crossReference]->(x)
RETURN s.dbId, s.displayName, s.taxId, s.abbreviation,
       collect(DISTINCT x.identifier) AS xrefs
ORDER BY s.displayName
```

The NCBI `taxId` disambiguates rank, which display names do not. A worked
example: searching `rotavirus` returns two instances that look like duplicates
and are not —

| Instance | taxId | abbrev | rank |
|---|---|---|---|
| `Rotavirus` | 10912 | ROT | genus |
| `Rotavirus A` | 28875 | RVA | species |

Both are correct. Which one applies is decided by the paper's organism, and
confirmed by the entity namespace already in use in the branch (`R-RVA-*`
corresponds to abbreviation `RVA`). No preference was involved.

## Existing physical entities — reuse before creating

```cypher
MATCH (pe:PhysicalEntity)
WHERE toLower(pe.displayName) CONTAINS toLower($token)
OPTIONAL MATCH (pe)-[:compartment]->(c)
OPTIONAL MATCH (pe)-[:species]->(s)
RETURN pe.stId, pe.displayName, pe.schemaClass,
       collect(DISTINCT c.displayName) AS compartment,
       collect(DISTINCT s.displayName) AS species
ORDER BY pe.displayName
```

Filter the result on **both** compartment and species before calling it a
match — Reactome creates a separate instance per compartment, and the same
name exists across species. A search for `80S ribosome` returns instances in
*Oryza sativa*, *Arabidopsis*, *S. cerevisiae*, *Oryctolagus*, *Mus* and
*Homo sapiens*, plus several mRNA complexes; only one is
`80S ribosome [cytosol]`, Homo sapiens, `R-HSA-72500`.

- exactly one match on name + compartment + species → `RESOLVED`, record the ST_ID
- several → `AMBIGUOUS`, list them all with their ST_IDs
- none → genuinely new; say so, and say what you searched for

## Ontology terms — GO, ChEBI

Resolve **label and accession together** via the `ols` MCP server, and never
write a term down that has not come back from it. A plausible-sounding label is
not a term: three of the first rotavirus draft's GO BP labels did not exist.

```
mcp__ols__search_terms(query=<label>, ontology="go")
mcp__ols__get_term_info(id="GO:0046718")     # confirms label + obsolete status
```

`get_term_info` also reports `is_obsolete`, which search results do not.

Two cautions:

- `exact_match: true` does **not** reliably filter by label — it returns
  non-matching terms. Read what comes back.
- A term existing is not a term fitting. `wide pore channel activity`
  (`GO:0022829`) is real, but its definition is energy-independent diffusion
  through gap junctions and porins. Whether a viral perforin-like pore belongs
  there is `JUDGEMENT`, not `RESOLVED` — record the accession, quote the
  definition, and put the question to the curator.

## Release status — before linking an ST_ID

```
https://reactome.org/ContentService/data/query/<ST_ID>     200 = released
```

Handled automatically by `build_update_doc.py`; see SKILL.md.

---

## Recording the result in the spec

Put the evidence next to the value, so a reader sees the basis rather than an
assertion:

```json
"related_species": "Rotavirus A (NCBI taxon 28875, R-RVA namespace) — RESOLVED",
"go_mf": "wide pore channel activity (GO:0022829) — JUDGEMENT: term exists, but
          its definition covers gap junctions and porins; fit for a viral pore
          is the curator's call",
"reuses": "80S ribosome [cytosol] (R-HSA-72500) — RESOLVED, unique on name +
           compartment + species"
```

The renderer counts bare `PENDING` markers and reports them, because a value
with no query behind it should not pass silently as though it had been checked.
