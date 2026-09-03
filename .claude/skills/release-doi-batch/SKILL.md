# Generate DOI Batch Skill

## Purpose

Run the Reactome CrossRef DOI batch XML generator for a given release version.
This skill wraps generate_crossref_xml.py — the script handles all XML construction,
contributor ordering, ORCID normalization, and output formatting. Claude's role is
to help set up inputs correctly, run the script, and interpret any errors.

The script is at: @generate_crossref_xml.py

## Invocation

 /release-doi-batch $ARGUMENTS

$ARGUMENTS should be the worksheet name (release version), e.g.:

 /release-doi-batch V94
 /release-doi-batch V95

## Working directory — set this up first (keeps the repo clean)

To keep this repository clean, **never write the generated XML into it.** Before
running the script, agree on one working directory for this run and write the
output batch XML there (via the script's `--output` flag). Ask the curator:

- **Where** it should live — default is a gitignored `output/` folder in the repo
  (`./output/<name>/`; git already ignores `output/`), or give an absolute path
  outside the repo (e.g. `~/reactome-work/<name>/`).
- **What** to name it — suggested default: `<version>-doi-batch` (e.g.
  `V94-doi-batch`).

Create it with `mkdir -p`, pass `--output <dir>/<version>.xml` when running the
script (see Running the Script), and report the full path back. Do not write the
XML to the repo root or next to the script.

## Prerequisites

Confirm the following before running:

1. Python 3 is installed:
    python3 --version

2. pandas is installed (pinned versions live in the repo's requirements.txt):
    pip3 install --user -r requirements.txt

3. DOIs.xlsx is available locally (from the Reactome Team Drive).
  Default location the script expects:
    Same directory as the script, OR
    A "Not Submitted" subdirectory next to the script.
  If it is elsewhere, the --excel flag overrides the default.

4. The Release sheet in DOIs.xlsx has an entry for the target version with
  columns: Version, Release Year, Release Month, Release Day.
  (Note: confirm column names match exactly — the script reads them by name.)

If any prerequisite is missing, stop and help the user resolve it before proceeding.

## Running the Script

Basic usage — run from the directory containing generate_crossref_xml.py, and
**write the output into the working directory** you set up above (never the repo).
**Ask the curator for their depositor email first** — `--email` is required and
has no default; it is the CrossRef depositor address for this submission, so use
the address of the person running the deposit:

 python3 generate_crossref_xml.py V94 --email you@institution.org --output ./output/V94-doi-batch/V94.xml

This writes V94.xml (version number extracted from the worksheet name) into your
working directory. Without `--output` the script would write to the current
directory — always pass `--output` so nothing lands in the repo.

With options:

 # Specify DOIs.xlsx location explicitly
 python3 generate_crossref_xml.py V94 --email you@institution.org --excel /path/to/DOIs.xlsx

 # Specify output file path
 python3 generate_crossref_xml.py V94 --email you@institution.org --output /path/to/output/V94_batch.xml

On success, the script prints:
 - Output file path
 - Version and batch ID
 - Release date
 - Number of datasets (unique Project_IDs)

## What the Script Produces

The output XML conforms to CrossRef schema 5.3.1. Key construction details:

- doi_batch_id: version_number * 100000, zero-padded to 9 digits
- timestamp: {year}{month:02d}{day:02d}1230
- One <dataset dataset_type="collection"> block per unique Project_ID
- Contributors: external reviewers (from Contributor columns) listed first,
 curator listed last as editor (sequence="additional", role="editor")
- Sequence: "first" for the first contributor, "additional" for all others
- DOIs constructed as: 10.3180/{StableID}
- Resource URLs: http://reactome.org/content/detail/{StableID}
- ORCID values normalized to full URLs: https://orcid.org/{id}

## Interpreting Errors

### Worksheet not found
 Error: worksheet 'V94' not found. Available: [...]
 → Check the exact sheet name in DOIs.xlsx. Sheet names are case-sensitive.
   Use the exact name shown in the error output.

### Version not found in Release sheet
 Error: version 94 not found in Release sheet.
 → Open DOIs.xlsx, go to the Release sheet, and confirm there is a row
   where the Version column equals the numeric version (e.g., 94, not "V94").
   The script strips non-numeric characters from the worksheet name to get
   the version number.

### DOIs.xlsx not found
 Error: DOIs.xlsx not found. Use --excel to specify the path.
 → Use --excel /full/path/to/DOIs.xlsx to point the script at the file.

### pandas / openpyxl import error
 ModuleNotFoundError: No module named 'pandas'
 → Run: pip3 install --user -r requirements.txt   (from the repo root)

### Missing or malformed ORCID
 If a contributor row has a blank ORCID, the script omits the <ORCID> element
 for that contributor rather than producing an empty tag. CrossRef will accept
 this, but flag it for follow-up — all curators and reviewers should have
 ORCIDs in the lookup sheet.

## After the Script Runs

1. Open the output XML and spot-check 2-3 dataset blocks:
  - Confirm <doi> values follow the pattern 10.3180/R-HSA-XXXXXXX
  - Confirm <resource> URLs are well-formed
  - Confirm contributor names and ORCIDs are correct
  - Confirm the release date in <update_date> matches the intended release

2. Submit to CrossRef via the deposit interface:
    https://doi.crossref.org/servlet/deposit
  Log in with the Reactome depositor credentials. Do not POST the file
  programmatically — use the web interface.

3. Save the output XML to the Reactome Team Drive in the DOI batch archive
  folder for the release.

## Notes

- The script does not validate against the CrossRef XSD before writing output.
 If CrossRef rejects the batch, check the error message for schema violations
 and compare against https://data.crossref.org/schemas/crossref5.3.1.xsd
- `--email` is required and sets the CrossRef depositor address for the batch.
 There is no default — pass the address of the person running the deposit
 (typically one registered with CrossRef for the Reactome depositor account).
- The script is idempotent — running it twice for the same version overwrites
 the output file. The batch_id is version-derived (not timestamp-derived),
 so resubmissions will have the same batch_id. CrossRef treats resubmissions
 with the same batch_id as updates.