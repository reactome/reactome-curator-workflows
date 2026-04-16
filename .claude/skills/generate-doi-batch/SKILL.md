# Generate DOI Batch Skill

## Purpose

Run the Reactome CrossRef DOI batch XML generator for a given release version.
This skill wraps generate_crossref_xml.py — the script handles all XML construction,
contributor ordering, ORCID normalization, and output formatting. Claude's role is
to help set up inputs correctly, run the script, and interpret any errors.

The script is at: @generate_crossref_xml.py

## Invocation

 /generate-doi-batch $ARGUMENTS

$ARGUMENTS should be the worksheet name (release version), e.g.:

 /generate-doi-batch V94
 /generate-doi-batch V95

## Prerequisites

Confirm the following before running:

1. Python 3 is installed:
    python3 --version

2. pandas is installed:
    pip install pandas openpyxl

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

Basic usage — run from the directory containing generate_crossref_xml.py:

 python3 generate_crossref_xml.py V94

This generates: V94.xml (or the version number extracted from the worksheet name)

With options:

 # Specify DOIs.xlsx location explicitly
 python3 generate_crossref_xml.py V94 --excel /path/to/DOIs.xlsx

 # Specify output file path
 python3 generate_crossref_xml.py V94 --output /path/to/output/V94_batch.xml

 # Override depositor email (default is gillespm@gmail.com)
 python3 generate_crossref_xml.py V94 --email depositor@reactome.org

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
 → Run: pip install pandas openpyxl

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
- The default depositor email (gillespm@gmail.com) is the address registered
 with CrossRef for the Reactome depositor account. Override with --email only
 if this changes.
- The script is idempotent — running it twice for the same version overwrites
 the output file. The batch_id is version-derived (not timestamp-derived),
 so resubmissions will have the same batch_id. CrossRef treats resubmissions
 with the same batch_id as updates.