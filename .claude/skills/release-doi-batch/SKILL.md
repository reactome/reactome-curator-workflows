# Generate DOI Batch Skill

## Purpose

Take a release's curation tracking spreadsheet, format it into the canonical
DOIs.xlsx worksheet layout used by previous releases, then generate the CrossRef
DOI batch XML for that release.

This is a **two-stage** workflow, and both stages are scripted:

| Stage | Script | What it does |
|---|---|---|
| 1. Format | @format_release_sheet.py | Converts the wide release tracking sheet (e.g. `Release 97.xlsx`) into the 15-column DOIs.xlsx layout matching V95/V96, and validates it |
| 2. Generate | @generate_crossref_xml.py | Builds the CrossRef 5.3.1 batch XML from that worksheet |

Stage 1 is new. Previously curators reshaped the tracking sheet into the DOIs.xlsx
layout by hand, which is where most batch errors came from. Run Stage 1 first
unless the target worksheet already exists in DOIs.xlsx and has been checked.

Claude's role is to set up inputs correctly, run the scripts, and **walk the
curator through the Stage 1 validation report** — the validation catches real
data problems, and those are curation decisions, not something Claude should
silently fix.

## Invocation

    /release-doi-batch $ARGUMENTS

`$ARGUMENTS` is the worksheet name (release version), e.g.:

    /release-doi-batch V97

If the curator supplies a tracking spreadsheet ("here's Release 97.xlsx"), run
both stages. If they only want the XML from an already-prepared worksheet, skip
to Stage 2.

## Working directory — set this up first (keeps the repo clean)

To keep this repository clean, **never write generated files into it.** Before
running anything, agree on one working directory for this run. Ask the curator:

- **Where** it should live — default is a gitignored `output/` folder in the repo
  (`./output/<name>/`; git already ignores `output/`), or an absolute path
  outside the repo (e.g. `~/reactome-work/<name>/`).
- **What** to name it — suggested default: `<version>-doi-batch` (e.g.
  `V97-doi-batch`).

Create it with `mkdir -p`, write both the formatted workbook and the batch XML
there, and report the full paths back. Never write output to the repo root or
next to the scripts.

## Prerequisites

1. Python 3:

        python3 --version

2. pandas and openpyxl (pinned versions live in the repo's requirements.txt):

        pip3 install --user -r requirements.txt

3. **DOIs.xlsx** available locally (from the Reactome Team Drive). Typical path:

        ~/Documents/Reactome/DOIs/BatchSubmission/Not Submitted/DOIs.xlsx

   Both scripts take `--excel` / `--dois` to point at it. `generate_crossref_xml.py`
   also falls back to `DOIs.xlsx` (or `Not Submitted/DOIs.xlsx`) next to the script.

4. For Stage 1, the **release tracking spreadsheet** (e.g. `Release 97.xlsx`).

5. DOIs.xlsx must have a `Release` sheet row for the target version, with columns
   `Version`, `Release Year`, `Release Month`, `Release Day`. Stage 1 checks this
   for you and reports it up front.

6. Every curator in the release must appear in the DOIs.xlsx `Curator ORCID`
   sheet (`Curator Given`, `Curator Surname`, `ORCID`) — that sheet is how curator
   ORCIDs get filled in. Stage 1 raises an error naming anyone missing.

If a prerequisite is missing, stop and help the user resolve it before proceeding.

---

# Stage 1 — Format the release sheet

## What it converts

The curation team's tracking sheet is wide and workflow-oriented (`Curator`,
`External_Contributor`, `contributor_type`, `ORCID`, `contributor_URL`, `TLP`,
`release_site`, `NOTES`, …). DOIs.xlsx worksheets are narrow and deposit-oriented.
The script maps between them:

| DOIs.xlsx column | Comes from |
|---|---|
| `Project_ID` | `Project_ID` (coerced to int) |
| `Project` | `Project` (whitespace collapsed) |
| `Curator Given` / `Curator Surname` | `Curator` full name, split by exact match against the `Curator ORCID` sheet |
| `Curator ORCID` | `Curator ORCID` sheet lookup |
| `StableID` | `StableID` |
| `StableID_root` | **Derived** from `StableID` (version suffix stripped); the source column is cross-checked, not trusted |
| `Contributor Given` / `Contributor Surname` | `External_Contributor` split using `Contributor_Last_Name` as the anchor |
| `Contributor Role` | `contributor_type`, title-cased |
| `Contributor ORCID` | `ORCID`, falling back to an ORCID parsed out of `contributor_URL` |
| `Editor` / `Reviewer` / `Title` / `DOI Data` | Generated XML helper fragments, matching the V95/V96 cells |

Anchoring the contributor split on the surname column keeps multi-word given
names (`David P Hill`) and compound surnames (`Andrea Senff-Ribeiro`) intact.

The DOI is always derived as `10.3180/{StableID}` — never copied from the
tracking sheet's `new-updated_DOI` column, which in practice drifts out of sync.
Disagreements are reported as errors.

The `Editor` / `Reviewer` / `Title` / `DOI Data` columns are legacy manual-assembly
helpers; `generate_crossref_xml.py` ignores them and builds the XML from the
structured columns. They are reproduced so the worksheet matches prior releases.
One deliberate difference: where a contributor has no ORCID, older sheets wrote
an empty `https://orcid.org/`; the script omits the `<ORCID>` line instead,
matching what actually gets deposited.

## Running Stage 1

Validate first, write nothing:

    python3 format_release_sheet.py V97 \
      --source "~/Desktop/Release 97.xlsx" \
      --dois "~/Documents/Reactome/DOIs/BatchSubmission/Not Submitted/DOIs.xlsx" \
      --validate-only

Then write a standalone workbook into the working directory:

    python3 format_release_sheet.py V97 \
      --source "~/Desktop/Release 97.xlsx" \
      --dois "~/Documents/Reactome/DOIs/BatchSubmission/Not Submitted/DOIs.xlsx" \
      --output ./output/V97-doi-batch/V97_formatted.xlsx

Or insert the sheet straight into DOIs.xlsx (**backs the file up first**, and
places the new sheet after the other version sheets, before `Release`):

    python3 format_release_sheet.py V97 \
      --source "~/Desktop/Release 97.xlsx" \
      --dois "~/Documents/Reactome/DOIs/BatchSubmission/Not Submitted/DOIs.xlsx" \
      --in-place

### Options

- `--source-sheet NAME` — sheet within the tracking workbook. Defaults to the
  worksheet name if present, otherwise the first sheet.
- `--sort project|surname|source` — row order. `project` (default) groups
  contributors under each pathway alphabetically, matching V96. `surname` matches
  V95's contributor-surname order. `source` preserves the tracking sheet's order.
  Order does not change the XML — the generator groups by `Project_ID` regardless
  — so this is purely for reading the spreadsheet.
- `--validate-only` — report and write nothing.
- `--strict` — exit non-zero if there are any errors (for scripted use).

**Default to the standalone `--output` file.** Only use `--in-place` once the
curator has seen the validation report and agreed, and tell them where the backup
went. `--in-place` rewrites DOIs.xlsx via openpyxl; the workbook is plain data
today, but confirm the curator isn't relying on cell formatting before using it.

## Reading the validation report

The script prints ERRORS (blocking) and WARNINGS (advisory). It still writes the
sheet when there are errors, so the curator can inspect it — **but do not proceed
to Stage 2 with unresolved errors.** Bring each one to the curator; these are
curation decisions.

**Errors** — malformed `StableID` (must be `R-HSA-NNNNNNN.V`; catches missing
`R-` prefixes and stray newlines), `StableID_root` disagreeing with `StableID`,
`new-updated_DOI` disagreeing with `StableID`, one `Project_ID` mapping to several
`StableID`s, one `StableID` used by several projects, a contributor listed twice
on the same project, a curator missing from the `Curator ORCID` sheet, a malformed
ORCID, a blank Project/StableID/contributor, and a missing `Release` sheet row.

**Warnings** — a contributor with no ORCID (the element is omitted; flag for
follow-up, every contributor should have one), a stale `no_ORCID_ID='yes'` flag
where an ORCID is in fact present, a contributor name that doesn't end with its
stated surname, a role other than Author/Reviewer, and a `Project_ID` carrying
inconsistent titles.

Two error classes matter most, because they change what gets deposited:

- **One `Project_ID`, several `StableID`s.** The generator emits one dataset per
  `Project_ID` and takes the `StableID` from the first row of the group — the
  other versions are silently dropped, so the DOI minted may not be the intended
  one. The curator must pick one `StableID` per project.
- **`new-updated_DOI` disagrees with `StableID`.** One of the two is wrong.
  Ask which; do not guess.

---

# Stage 2 — Generate the CrossRef XML

Run from the directory containing `generate_crossref_xml.py`, writing output into
the working directory. **Ask the curator for their depositor email first** —
`--email` is required and has no default; it is the CrossRef depositor address
for this submission, so use the address of the person running the deposit:

    python3 generate_crossref_xml.py V97 \
      --email you@institution.org \
      --excel "~/Documents/Reactome/DOIs/BatchSubmission/Not Submitted/DOIs.xlsx" \
      --output ./output/V97-doi-batch/V97.xml

Without `--output` the script writes to the current directory — always pass it so
nothing lands in the repo.

If Stage 1 wrote a standalone workbook rather than using `--in-place`, either
copy the sheet into DOIs.xlsx first, or point `--excel` at a workbook that has
both the version sheet **and** the `Release` sheet. The standalone file from
`--output` has only the version sheet, so `--excel` must still be DOIs.xlsx.

On success the script prints the output path, version and batch ID, release date,
and the number of datasets (unique `Project_ID`s). Check that dataset count
against the number of distinct projects in the release.

## What the Script Produces

The output XML conforms to CrossRef schema 5.3.1. Key construction details:

- `doi_batch_id`: version number × 100000, zero-padded to 9 digits
- `timestamp`: `{year}{month:02d}{day:02d}1230`
- One `<dataset dataset_type="collection">` block per unique `Project_ID`
- Contributors: external authors/reviewers first, curator last as
  `sequence="additional" contributor_role="editor"`
- Sequence: `first` for the first contributor, `additional` for all others
- DOIs constructed as `10.3180/{StableID}`
- Resource URLs: `http://reactome.org/content/detail/{StableID}`
- ORCID values normalized to full URLs: `https://orcid.org/{id}`

---

## Interpreting Errors

### Stage 1

**`source workbook not found` / `DOIs.xlsx not found`**
→ Check the paths passed to `--source` and `--dois`. Quote paths containing
spaces (`"Release 97.xlsx"`, `"Not Submitted"`).

**`source sheet is missing required column(s)`**
→ The tracking sheet has been renamed or restructured. The script accepts common
aliases for each field (see `SOURCE_ALIASES` in the script); if a column has been
genuinely renamed, add the alias there rather than editing the spreadsheet.

**`curator 'X' is not in the 'Curator ORCID' sheet`**
→ Add them to that sheet in DOIs.xlsx (`Curator Given`, `Curator Surname`,
`ORCID`) and re-run. Without it, their name is split on the last space and their
ORCID is left blank.

**`version N has no row in the Release sheet`**
→ Add `Version` / `Release Year` / `Release Month` / `Release Day` to the
`Release` sheet before Stage 2.

### Stage 2

**`worksheet 'V97' not found. Available: [...]`**
→ Sheet names are case-sensitive. Either Stage 1 hasn't been run with
`--in-place`, or the sheet is still only in the standalone output file. Use the
exact name shown in the error.

**`version 97 not found in Release sheet.`**
→ The `Release` sheet needs a row where `Version` equals the numeric version
(`97`, not `"V97"`). The script strips non-numeric characters from the worksheet
name to get the version number.

**`ModuleNotFoundError: No module named 'pandas'`**
→ `pip3 install --user -r requirements.txt`   (from the repo root)

**Missing or malformed ORCID**
→ A blank ORCID means the `<ORCID>` element is omitted for that contributor
rather than emitted empty. CrossRef accepts this, but flag it for follow-up —
all curators and reviewers should have ORCIDs.

---

## After the Scripts Run

1. Open the output XML and spot-check 2–3 dataset blocks:
   - `<doi>` values follow `10.3180/R-HSA-XXXXXXX.V`
   - `<resource>` URLs are well-formed
   - contributor names, roles, and ORCIDs are correct
   - the date in `<update_date>` matches the intended release
   - multi-contributor pathways list every expected reviewer/author

2. Confirm the dataset count matches the number of projects in the release.

3. Cross-check against the database, if a Reactome MCP server is available (see
   below). Resolve anything it flags before submitting.

4. Submit to CrossRef via the deposit interface:
   https://doi.crossref.org/servlet/deposit
   Log in with the Reactome depositor credentials. Do not POST the file
   programmatically — use the web interface.

5. Save the output XML to the Reactome Team Drive in the DOI batch archive folder
   for the release, and save the updated DOIs.xlsx back to the Team Drive.

## Optional — database cross-check

A DOI minted for a mistyped or retired StableID resolves to nothing. If the
session has the `gk-central` MCP tools (`mcp__gk-central__read_neo4j_cypher`),
check the batch against the editing database before submitting. If it doesn't,
say "Database cross-check not run — gk-central not available (see
/analysis-reactome-mcp)" and continue; this step is never required.

Take every StableID and title from the generated XML (`<doi>` values minus the
`10.3180/` prefix, and each dataset's `<title>`), then in one read-only query
matching on `stId`:

- **StableID not found in gk_central** → flag, and don't submit that dataset
  until the curator confirms the ID. Usually a typo in DOIs.xlsx or a retired
  event.
- **Not a Pathway** → flag. DOIs are issued for pathways.
- **Title differs from `displayName`** → flag for the curator to decide which is
  right. The XML title comes from the DOIs.xlsx `Project` column.
- **DOI property** — if the Pathway nodes carry a DOI property (confirm the
  property name with `get_neo4j_schema` or `keys(p)` first; don't assume it),
  compare it with `10.3180/<StableID>` and flag mismatches.

Report findings as a short table (StableID | Issue | Suggested action). Never
edit the XML or DOIs.xlsx to fix a finding; the curator corrects DOIs.xlsx and
reruns the script.

## Notes

- Neither script validates against the CrossRef XSD before writing output. If
  CrossRef rejects the batch, check the error against
  https://data.crossref.org/schemas/crossref5.3.1.xsd
- `--email` is required by `generate_crossref_xml.py` and sets the CrossRef
  depositor address. There is no default — pass the address of the person running
  the deposit (typically one registered with CrossRef for the Reactome depositor
  account).
- `generate_crossref_xml.py` is idempotent — re-running for the same version
  overwrites the output. The `batch_id` is version-derived, not timestamp-derived,
  so CrossRef treats resubmissions with the same `batch_id` as updates.
- `format_release_sheet.py` is also idempotent; `--in-place` replaces an existing
  sheet of the same name and takes a fresh timestamped backup each run.
