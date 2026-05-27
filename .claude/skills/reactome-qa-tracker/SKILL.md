---
name: reactome-qa-tracker
description: >
  Use this skill whenever the user wants to convert a Reactome QA comparison
  spreadsheet (e.g. V97_Slice*_fixes, or any sheet containing commandlinerunner,
  diagram-qa, graph-qa, or release-qa comparison data) into a structured curator
  tracker workbook. Triggers include phrases like "organize this QA sheet",
  "format the fixes sheet for curators", "add a status dropdown to the QA tracker",
  "make a curator tracker from the comparison sheet", or any mention of a Reactome
  slice, QA fixes spreadsheet, or curator status tracking. Also triggers when the
  user wants to run the QA comparison script (compare_dirs.sh) and produce the
  curator tracker in one workflow. Always use this skill when a Google Sheets or
  .xlsx QA comparison file is provided and the user wants curators to be able to
  record fix status or add comments.
---

# Reactome QA Curator Tracker — Skill

End-to-end workflow: runs `compare_dirs.sh` against two QA output directories,
filters out skipped sections, and produces a polished multi-sheet `.xlsx` curator
tracker with status dropdowns, color-coded fill, and a comments column on every
data row.

Can also be used starting from Step 3 if comparison files already exist
(e.g., a Google Sheets URL or uploaded `.xlsx`/`.csv` is provided directly).

---

## Step 1 — Ask for directories

Ask the user for:

1. **OLD_DIR** — path to the previous-version QA output directory  
   (e.g. `/data/qa/v96`)
2. **NEW_DIR** — path to the current-version QA output directory  
   (e.g. `/data/qa/v97_slice1`)
3. **compare_dirs.sh location** — default: `<repo-root>/.claude/skills/reactome-qa-tracker/../../../compare_dirs.sh` or ask the user if it is not found.

Confirm both directories exist before proceeding:

```bash
[[ -d "$OLD_DIR" ]] || echo "ERROR: OLD_DIR not found"
[[ -d "$NEW_DIR" ]] || echo "ERROR: NEW_DIR not found"
```

### Version label extraction

Derive human-readable version labels from the directory basenames:

```python
import os, re

def version_label(path):
    name = os.path.basename(path.rstrip('/'))
    # "v96" → "V96", "v97_slice1" → "V97 Slice 1"
    name = re.sub(r'^v(\d+)', lambda m: f'V{m.group(1)}', name, flags=re.IGNORECASE)
    name = name.replace('_', ' ').title()
    return name

old_label = version_label(OLD_DIR)   # e.g. "V96"
new_label = version_label(NEW_DIR)   # e.g. "V97 Slice 1"
comparison_label = f"{old_label} vs {new_label}"  # e.g. "V96 vs V97 Slice 1"
```

Use `new_label` as the base for the output filename:
`<new_label_underscored>_QA_Curator_Tracker.xlsx`  
e.g. `V97_Slice_1_QA_Curator_Tracker.xlsx`

---

## Step 2 — Run compare_dirs.sh

The script expects a flat directory of QA output files, or a directory containing
subdirectories named `commandlinerunner`, `diagram-qa`, `graph-qa`, `release-qa`.

### Detecting directory structure

```bash
# Check whether the QA tools produce subdirectories or flat files
if [[ -d "$NEW_DIR/commandlinerunner" ]]; then
    STRUCTURE="subdirs"
else
    STRUCTURE="flat"
fi
```

### Running the comparison

**Subdirectory structure** — run once per QA tool:

```bash
SCRIPT="<path-to-compare_dirs.sh>"
chmod +x "$SCRIPT"

for TOOL in commandlinerunner diagram-qa graph-qa release-qa; do
    OLD_TOOL="$OLD_DIR/$TOOL"
    NEW_TOOL="$NEW_DIR/$TOOL"
    if [[ -d "$OLD_TOOL" && -d "$NEW_TOOL" ]]; then
        "$SCRIPT" "$OLD_TOOL" "$NEW_TOOL" > "/tmp/${TOOL}_comparison.txt" 2>&1
        echo "Produced: /tmp/${TOOL}_comparison.txt"
    else
        echo "Skipping $TOOL — one or both directories missing"
    fi
done
```

**Flat structure** — run once, then split by file type:

```bash
"$SCRIPT" "$OLD_DIR" "$NEW_DIR" > /tmp/all_comparison.txt 2>&1
```

Split the output by file extension: files matching `DT*` → diagram-qa;
`GT*` → graph-qa; `Review_Status*`, `Multiple_Attributes*`, `One_Hop*`,
`Attribute_Has_Only_One*`, `Two_Attributes*`, `EHLD*` → release-qa;
everything else → commandlinerunner.

### compare_dirs.sh output format

Each file section looks like:

```
==================================================
File: Mandatory_Attributes.tsv
New lines:
9985860	Unkown	Person	initial|surname	Shamovsky, Veronica, 2026-03-26
9985954	Unkown	Person	initial|surname	Shamovsky, Veronica, 2026-03-26

==================================================
File: Reaction_Compartment.tsv
No new lines.
```

Parse this into a dict of `{filename: [list_of_tab_separated_rows]}`.
Only collect sections with `"New lines:"` (skip `"No new lines."` and
`"Entire file is new:"` unless that file is also in the keep list).

---

## Step 3 — Apply skip rules

### Files to skip entirely (do not include in curator tracker)

**commandlinerunner** — skip these output files:

| File | Reason |
|---|---|
| `Reaction_Compartment.tsv` | Backlog too large; reported to developers |
| `Reaction_Participants_Species_Mismatch.tsv` | Backlog too large; reported to developers |
| `Complex_Compartment_Inconsistency.tsv` | Backlog too large; reported to developers |
| `PathwayEvents_Species_Mismatch.tsv` | Backlog too large; reported to developers |
| `Extra_Compartments_In_Entity_Set_Or_Members.tsv` | Backlog too large; reported to developers |

**graph-qa** — skip these GT files:

| File | Reason |
|---|---|
| `GT018-DatabaseObjectsWithoutCreated.csv` | Developer report only |
| `GT022-PhysicalEntityWithoutCompartment.csv` | Developer report only |
| `GT027-EntriesWithOtherCyclicRelations.csv` | Developer report only |
| `GT033-OtherRelationsThatPointToTheSameEntry.csv` | Developer report only |
| `GT036-EventsWithoutCompartment.csv` | Developer report only |
| `GT048-InstanceEditCreatesInstanceEdit.csv` | Developer report only |
| `GT049-InstanceEditModifiesInstanceEdit.csv` | Developer report only |
| `GT053-PrecedingEventOutputsNotUsedInReaction.csv` | Developer report only |
| `GT101-CompartmentWithCyclicSurroundedByAndInstanceOf.csv` | Developer report only |

**diagram-qa** — skip these files:

| File | Reason |
|---|---|
| `DT113-ReactionShapeMismatch.csv` | Volume too large for curator tracker; diagram team handles separately |
| `DT114-ReplacedNodeAttachmentLabel.csv` | Auto-fix labels; not actionable by curators |

**release-qa** — skip entirely:

| File | Reason |
|---|---|
| `One_Hop_Circular_Reference.tsv` | All rows involve markerReference/cell — script adjustment needed |
| `Human_Reactions_Without_Disease_And_Have_NonHuman_PhysicalEntities.tsv` | Developer-only backlog; not actionable by curators |

**diagram-qa** — summary table only:

The summary table (DT code, priority, entry count) is NOT included as
data rows in the tracker. Only files with actionable new entries are included.

### Row-level filters (applied after file-level skip)

Apply these filters to every remaining file before writing to the tracker.
Drop any row where:

1. **markerReference / cell**: any field contains both `"markerReference"` and
   `"cell"` (case-insensitive). These require a script adjustment and are not
   actionable by curators.

2. **Uniprot / Interactions Importer**: any field contains `"UniProt"` or
   `"Interactions Importer"`. These require a script change.

3. **NO_HEADER sections**: any section whose filename resolves to `NO_HEADER` or
   whose header row is blank — skip all rows in the section.

4. **summary.tsv** rows: the `summary.tsv` file contains aggregate counts, not
   per-entity issues. Include it as a contextual info block (non-data rows) if
   useful for the Overview sheet, but do not create curator status rows for it.

### Skip-rule implementation sketch

```python
SKIP_FILES = {
    'commandlinerunner': {
        'Reaction_Compartment.tsv',
        'Reaction_Participants_Species_Mismatch.tsv',
        'Complex_Compartment_Inconsistency.tsv',
        'PathwayEvents_Species_Mismatch.tsv',
        'Extra_Compartments_In_Entity_Set_Or_Members.tsv',
    },
    'graph-qa': {
        'GT018-DatabaseObjectsWithoutCreated.csv',
        'GT022-PhysicalEntityWithoutCompartment.csv',
        'GT027-EntriesWithOtherCyclicRelations.csv',
        'GT033-OtherRelationsThatPointToTheSameEntry.csv',
        'GT036-EventsWithoutCompartment.csv',
        'GT048-InstanceEditCreatesInstanceEdit.csv',
        'GT049-InstanceEditModifiesInstanceEdit.csv',
        'GT053-PrecedingEventOutputsNotUsedInReaction.csv',
        'GT101-CompartmentWithCyclicSurroundedByAndInstanceOf.csv',
    },
    'release-qa': {
        'One_Hop_Circular_Reference.tsv',
    },
}

def should_skip_file(tool, filename):
    """True if the entire file should be omitted from the tracker."""
    basename = os.path.basename(filename)
    return basename in SKIP_FILES.get(tool, set())

def should_skip_row(row_values):
    """True if this row should be filtered out."""
    joined = '\t'.join(str(v) for v in row_values).lower()
    if 'markerreference' in joined and 'cell' in joined:
        return True
    if 'uniprot' in joined or 'interactions importer' in joined:
        return True
    return False
```

---

## Step 4 — Produce the curator tracker workbook

Produce a single `.xlsx` workbook. Save to `/mnt/user-data/outputs/` in
claude.ai Projects, or to `./outputs/` when running locally.
Call `present_files` at the end if available.

### Output filename

```python
slug = new_label.replace(' ', '_')   # e.g. "V97_Slice_1"
filename = f"{slug}_QA_Curator_Tracker.xlsx"
```

### Sheets

| Sheet | Content |
|---|---|
| 📋 Overview | Version info, status legend, sheet directory |
| commandlinerunner | All commandlinerunner sections (after filtering) |
| diagram-qa | All diagram-qa sections (after filtering) |
| graph-qa | All graph-qa sections (after filtering) |
| release-qa | All release-qa sections (after filtering) |

Only create sheets for sections that have at least one data row after filtering.

---

## Formatting rules

### Global
- Font: **Arial** throughout
- No gridlines (`sheet_view.showGridLines = False`)
- Freeze row 1 on every data sheet (`ws.freeze_panes = "A2"`)
- Thin grey border (`#CCCCCC`) on every cell

### Color palette

| Element | Hex |
|---|---|
| Top header bar (version/tool title) | `1F4E79` (white text) |
| Section header bar (per-file) | `2E75B6` (white text) |
| Alternating row A | `EBF3FB` |
| Alternating row B | `FFFFFF` |
| Status – Not Done | `FF6B6B` (bold text) |
| Status – Fixed | `6AAF6A` (bold text) |
| Status – Skipped | `FFD966` (bold text) |

### Per-row mandatory columns (always last two)

| Column | Header | Default value | Width |
|---|---|---|---|
| N-1 | **Status** | `Not Done` | 12 |
| N | **Comments** | *(empty)* | 30 |

Override the Status and Comments header cells with the dark navy fill
(`1F4E79`) to distinguish curator columns from source-data columns.

### Status dropdown (data validation)

```python
from openpyxl.worksheet.datavalidation import DataValidation

dv = DataValidation(
    type="list",
    formula1='"Not Done,Fixed,Skipped"',
    allow_blank=False,
    showDropDown=False,
    showErrorMessage=True,
    error="Please choose: Not Done, Fixed, or Skipped",
    errorTitle="Invalid entry"
)
ws.add_data_validation(dv)
dv.sqref = f"{status_col_letter}{first_data_row}:{status_col_letter}{last_data_row}"
```

### Status cell fill

```python
STATUS_FILLS = {
    "Not Done": PatternFill("solid", start_color="FF6B6B", end_color="FF6B6B"),
    "Fixed":    PatternFill("solid", start_color="6AAF6A", end_color="6AAF6A"),
    "Skipped":  PatternFill("solid", start_color="FFD966", end_color="FFD966"),
}
cell.value = "Not Done"
cell.fill  = STATUS_FILLS["Not Done"]
cell.font  = Font(name="Arial", bold=True, size=9)
cell.alignment = Alignment(horizontal="center", vertical="center")
```

---

## Section headers

Each QA file gets a merged bold section-header row spanning all columns:

```python
ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=NCOLS)
c = ws.cell(row=r, column=1, value="🔴  Mandatory_Attributes.tsv  – Missing required attributes")
c.fill = PatternFill("solid", start_color="2E75B6", end_color="2E75B6")
c.font = Font(name="Arial", bold=True, color="FFFFFF", size=10)
```

Use emoji severity cues:

| Emoji | When to use |
|---|---|
| 🔴 | Missing or null required attributes |
| 🟠 | Compartment or structural issues |
| 🟡 | Diagram warnings, review-status items |
| 🔵 | Diagram-QA entries (DT files) |
| 🔶 | Graph-QA entries (GT files) |
| 🟣 | Release-QA entries (EHLD, Two_Attributes, etc.) |

---

## Top header row per sheet

Each data sheet starts with a merged top-header row spanning all columns:

```python
ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=NCOLS)
c = ws.cell(row=1, column=1, value=f"commandlinerunner — {comparison_label}")
c.fill = PatternFill("solid", start_color="1F4E79", end_color="1F4E79")
c.font = Font(name="Arial", bold=True, color="FFFFFF", size=11)
```

Data sections start from row 2.

---

## 📋 Overview sheet

Three blocks:

1. **Version info** — one row: `Comparison: <comparison_label>` and
   `Generated: <today's date>`
2. **Status Legend** — three rows (Not Done / Fixed / Skipped) with fill and
   meaning.
3. **Sheet Directory** — one row per data sheet with a short description.

---

## Known column schemas

Use these schemas when parsing compare_dirs.sh output to produce readable headers.
Infer from the first non-empty line of each section; fall back to generic `Col 1`,
`Col 2`, … if the schema is unknown.

### commandlinerunner

| File | Columns |
|---|---|
| Mandatory_Attributes.tsv | DB_ID \| Display Name \| Class \| Missing Attributes \| Author / Date |
| Extra_Compartments_In_Entity_Set_Or_Members.tsv | DB_ID \| Display Name \| Issue \| Created By \| Modified By |
| Diagram_With_Unconnected_Entities.tsv | Diagram DBID \| Pathway Name \| Pathway DBID \| Unconnected Entity DBIDs \| Created \| Modified |
| summary.tsv | Category \| Count (do not create curator rows) |

### diagram-qa

| File | Columns |
|---|---|
| DT103-ExtraParticipantInDiagram.csv | Diagram (R-HSA) \| Diagram Name \| Physical Entity \| PE Name \| Author / Date |
| DT108-IsolatedGlyphs.csv | Diagram \| Diagram Name \| Entity \| Entity Name \| Created \| Modified |
| DT113-ReactionShapeMismatch.csv | Diagram (R-HSA) \| Pathway Name \| Reaction DBID \| Reaction Name \| DB Class \| Current Shape \| Expected Shape \| Created \| Modified |
| Other DT*.csv | Infer from header row |

### graph-qa

| File | Columns |
|---|---|
| GT002-PersonWithoutProperName.csv | DB_ID \| Name \| Created |
| GT026-EventsWithCyclicPrecedingEvents.csv | Infer from header |
| GT037-LiteratureReferenceRelationshipDuplication.csv | Stable ID \| Reaction/Event Name \| DB_ID B \| Reference Name B \| Author / Date |
| GT055-DuplicatedCuratedComplexes.csv | Stable ID A \| Name A \| Stable ID B \| Name B \| Modified By |
| GT064-ReactionWithInputAndOutputSameSchemaClass.csv | Stable ID \| Name \| Class \| Input Schema \| Output Schema / Created |
| GT070-ReactionsWithoutRegulatorWithMoreCompartmentsThanItsParticipants.csv | Infer from header |
| GT071-ReactionsWithOnlyOneInputAndOutputWhereSchemaClassDoNotMatch.csv | Stable ID \| Name \| Class \| Input Schema \| Output Schema \| Created \| Modified |
| GT090-CatalystActivityCompartmentDoesNotMatchReactionCompartment.csv | Stable ID \| Reaction Name \| — \| — \| Created / Modified |
| Other GT*.csv | Infer from header row |

### release-qa

| File | Columns |
|---|---|
| Multiple_Attributes_Missing.tsv | DBID \| Display Name \| Class \| Attributes \| Most Recent Author |
| Review_Status.tsv | DB_ID \| Display Name \| Issue \| Last Instance Edit \| Note \| Severity |
| Attribute_Has_Only_One_Value.tsv | DB_ID \| Display Name \| Class \| Attribute \| Author / Date |
| Two_Attributes_Refer_To_Same_Instance.tsv | Stable ID A \| Name A \| Stable ID B \| Name B \| Created / Modified |
| EHLD_Subpathway_Change.tsv | EHLD Pathway Name \| EHLD Pathway ID \| Subpathway IDs added \| Subpathway Names added \| Subpathway IDs removed \| Subpathway Names removed |
| summary.tsv | Category \| Count (do not create curator rows) |

---

## Step-by-step workflow

1. Ask for OLD_DIR, NEW_DIR, and script location (Step 1).
2. Extract version labels; confirm directories exist.
3. Detect directory structure (subdirs vs flat).
4. Run `compare_dirs.sh` per QA tool; capture output to temp files (Step 2).
5. Parse each temp file into `{tool: {filename: [rows]}}`.
6. Apply file-level and row-level skip rules (Step 3).
7. Instantiate `openpyxl.Workbook()`.
8. Write Overview sheet.
9. For each tool with remaining data, create a sheet:
   a. Write top header row (merged, navy, includes comparison_label).
   b. For each QA file (section):
      - Write section header row (merged, blue, with emoji).
      - Write column header row.
      - Write data rows (alternating fill).
      - Write Status cell (`Not Done`, red fill, dropdown).
      - Write Comments cell (blank).
      - Register DataValidation for the Status column range.
10. Set column widths.
11. Freeze panes at A2 for every data sheet.
12. Save to output path; call `present_files`.

---

## Column width reference

| Content type | Width |
|---|---|
| DB_ID / numeric ID | 12 |
| Stable ID (R-HSA-…) | 18 |
| Short name / class / schema | 22 |
| Long name / display name | 30–44 |
| Issue description | 32–40 |
| Author / date | 24 |
| Status | 12 |
| Comments | 30 |

---

## Adapting to new files

When a source directory contains QA files not listed above:

- Infer column headers from the first (header) row of the TSV/CSV.
- Derive a readable section title from the filename (strip underscores, add spaces).
- Apply the same Status + Comments columns at the end.
- Choose emoji cue: 🔴 if "missing" appears in the name, 🔶 otherwise.
- Do not add the file to any skip list unless instructed.

---

## Handling alternative inputs (no directories available)

If the user provides a Google Sheets URL or uploaded file instead of running
the comparison script:

1. Fetch the file with the Google Drive fetch tool using the document ID from
   the URL, or read the uploaded file with `pandas.read_excel`.
2. Skip Steps 1–2.
3. Apply skip rules (Step 3) to the fetched data.
4. Proceed to Step 4 (produce the tracker workbook).

---

## Dependencies

- `openpyxl` (pip install openpyxl --break-system-packages)
- `compare_dirs.sh` in the reactome-curator-workflows repo
- Google Drive fetch tool (for Sheets URLs, when running in claude.ai Projects)
- `present_files` tool (to deliver the output in claude.ai Projects)
