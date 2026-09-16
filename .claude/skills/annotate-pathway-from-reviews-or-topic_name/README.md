# annotate-pathway-from-reviews-or-topic_name

AI-assisted Reactome pre-curation: propose a pathway → subpathway → reaction
hierarchy and verify the primary experimental literature for every reaction.

**`SKILL.md` in this directory is the authoritative specification** — the workflow,
the mandatory ten-step PMID verification protocol, the species/chimeric framework,
the reaction-table deliverable, and the version history all live there. Read it
rather than this file.

## What's in this directory

| File | Description |
|------|-------------|
| `SKILL.md` | The skill itself: full workflow, protocols, and output specification |
| `Reactome_RLE_Annotation_Reference_V94.md` | Condensed ReactionLikeEvent curation reference, from the V94 Curator Guide and the Data Model Glossary |

## Running it

From Claude Code, launched in the repository root:

```
/annotate-pathway-from-reviews-or-topic_name
```

Then either supply references (Mode A: PMIDs, DOIs, or uploaded PDFs) or name a
biological topic (Mode B). Needs claude.ai Pro/Team/Enterprise or the Claude API
for context length; PubMed and PMC MCP servers are recommended so PMID
verification and full-text fetch run against live sources.

The output is a first-pass draft for curator review. It does not touch the
database, and GO / ChEBI / MONDO / UniProt accessions are left marked
**PENDING CURATOR VERIFICATION**.

## Contributing

Suggestions for the workflow or the reference file are welcome via GitHub issues.
When proposing a change to the reference file, cite the section of the Curator
Guide or Data Model Glossary that supports it, and note the guide version.

## Acknowledgements

The workflow and reference file derive from the Reactome Curator Guide (V94) and
Data Model Glossary, maintained by the Reactome curation team at the Ontario
Institute for Cancer Research and collaborating institutions. Naming conventions
follow Jupe et al. (2014), *Database* (Oxford), PMID 24951798.
