---
name: release-qa-tracker
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
filters out skipped sections, presents an intermediate review summary for each of
the four tool categories, and produces a polished multi-sheet `.xlsx` curator
tracker with status dropdowns, color-coded fill, and a comments column on every
data row.

Can also be used starting from Step 3 if comparison files already exist
(e.g., a Google Sheets URL or uploaded `.xlsx`/`.csv` is provided directly).

**`compare_dirs.sh`** is included in this skill directory.

---

## Working directory — set this up first (keeps the repo clean)

To keep this repository clean, **never write generated files into it.** Before
doing any work, agree on one working directory for this run and write the final
curator tracker `.xlsx` there. Ask the curator:

- **Where** it should live — default is a gitignored `output/` folder in the repo
  (`./output/<name>/`; git already ignores `output/`), or give an absolute path
  outside the repo (e.g. `~/reactome-work/<name>/`).
- **What** to name it — suggested default: `<new-version>-qa-tracker` (e.g.
  `V97-qa-tracker`).

Create it with `mkdir -p` and write the workbook there; the intermediate
`compare_dirs.sh` outputs may stay in `/tmp` (already outside the repo). Report
the full path back. Do not write generated files to the repo root or `.claude/`.

---

## Step 1 — Ask for directories

Ask the user for:

1. **OLD_DIR** — path to the previous-version QA output directory  
   (e.g. `/data/qa/SliceQA96`)
2. **NEW_DIR** — path to the current-version QA output directory  
   (e.g. `/data/qa/SliceQA97`)
3. **compare_dirs.sh location** — default: skill directory
   (`<repo-root>/.claude/skills/release-qa-tracker/compare_dirs.sh`)

Confirm both directories exist before proceeding:

```bash
[[ -d "$OLD_DIR" ]] || echo "ERROR: OLD_DIR not found"
[[ -d "$NEW_DIR" ]] || echo "ERROR: NEW_DIR not found"
```

### Version label extraction

Use the directory basenames directly as version labels, preserving capitalisation:

```python
import os

old_label = os.path.basename(OLD_DIR.rstrip('/'))   # e.g. "SliceQA96"
new_label = os.path.basename(NEW_DIR.rstrip('/'))   # e.g. "SliceQA97"
comparison_label = f"{old_label} vs {new_label}"   # e.g. "SliceQA96 vs SliceQA97"
```

Use `new_label` as the base for the output filename:
`<new_label>_QA_Curator_Tracker.xlsx`

---

## Step 2 — Run compare_dirs.sh

### Directory alias mapping

QA tool output directories may use different names than the four logical tool
names. Map actual directory names to logical names before running comparisons:

| Actual directory name | Logical name (used in skip rules and sheet names) |
|---|---|
| `commandlinerunner` | `commandlinerunner` |
| `command-line-runner` | `commandlinerunner` |
| `diagram-qa` | `diagram-qa` |
| `diagram-converter` | `diagram-qa` |
| `graph-qa` | `graph-qa` |
| `release-qa` | `release-qa` |

```python
DIR_ALIAS = {
    "commandlinerunner":  "commandlinerunner",
    "command-line-runner":"commandlinerunner",
    "diagram-qa":         "diagram-qa",
    "diagram-converter":  "diagram-qa",
    "graph-qa":           "graph-qa",
    "release-qa":         "release-qa",
}
```

### Detecting directory structure

```bash
# Probe for any known subdirectory name
for PROBE in commandlinerunner command-line-runner; do
    if [[ -d "$NEW_DIR/$PROBE" ]]; then
        STRUCTURE="subdirs"; break
    fi
done
STRUCTURE="${STRUCTURE:-flat}"
```

### Running the comparison

Make the script executable, then run once per QA tool, capturing output to
`/tmp/<tool>_comparison.txt`:

```bash
SCRIPT="<path-to-compare_dirs.sh>"
chmod +x "$SCRIPT"

for DIR_NAME in commandlinerunner command-line-runner diagram-qa diagram-converter graph-qa release-qa; do
    OLD_TOOL="$OLD_DIR/$DIR_NAME"
    NEW_TOOL="$NEW_DIR/$DIR_NAME"
    [[ -d "$OLD_TOOL" && -d "$NEW_TOOL" ]] || continue

    # Map to logical tool name
    case "$DIR_NAME" in
        commandlinerunner|command-line-runner) TOOL="commandlinerunner" ;;
        diagram-qa|diagram-converter)          TOOL="diagram-qa" ;;
        graph-qa)                              TOOL="graph-qa" ;;
        release-qa)                            TOOL="release-qa" ;;
    esac

    "$SCRIPT" "$OLD_TOOL" "$NEW_TOOL" > "/tmp/${TOOL}_comparison.txt" 2>&1
    echo "Produced: /tmp/${TOOL}_comparison.txt"
done
```

**Flat structure** — run once, then split by filename pattern:

```bash
"$SCRIPT" "$OLD_DIR" "$NEW_DIR" > /tmp/all_comparison.txt 2>&1
```

Split: files matching `DT*` → diagram-qa; `GT*` → graph-qa;
`Review_Status*`, `One_Hop*`, `Attribute_Has_Only_One*`, `Two_Attributes*`,
`EHLD*`, `Missing_*`, `Attribute_Value_Missing*`, `Entities_With_CoV*`,
`ReactionlikeEvent*` → release-qa; everything else → commandlinerunner.

### compare_dirs.sh output format

```
==================================================
File: Mandatory_Attributes.tsv
New lines:
9985860	Unknown	Person	initial|surname	Shamovsky, Veronica, 2026-03-26

==================================================
File: Reaction_Compartment.tsv
No new lines.

==================================================
File: Diagram_EWAS_Modification_Mismatch.tsv
No matching old file found.
Entire file is new:
Diagram_DBID	Pathway_DisplayName	...
512996	DNA Double Strand Break Response	...
```

Parse this into a dict `{filename: {'status': str, 'lines': [str]}}`.
- `"New lines:"` → `status = "new_lines"` — collect following lines as data rows (no header; header is the same in both files and filtered by comm)
- `"Entire file is new:"` → `status = "entire_new"` — first collected line is the header, rest are data rows
- `"No new lines."` → `status = "no_new"` — skip entirely

**Include "entire_new" sections** for any file that is not in the skip list. These are files that exist in NEW_DIR but not in OLD_DIR — all their rows are new and curator-actionable.

---

## Step 2.5 — Intermediate review (STOP before building tracker)

After running all four comparisons but **before building the workbook**, generate
a summary of what will be included (after skip rules) and present it to the curator.

### Summary format

```
═══════════════════════════════════════════════════════
QA Comparison Summary — SliceQA96 vs SliceQA97
═══════════════════════════════════════════════════════

━━━ commandlinerunner ━━━
  ✓  Mandatory_Attributes.tsv                   24 rows
  –  Diagram_EWAS_Modification_Mismatch.tsv      [skipped]
  –  Diagram_Unsynchronized_Reactions.tsv        [skipped]
  ·  Reaction_Input_Output_Imbalance.tsv         [no new lines]

━━━ diagram-qa ━━━
  ✓  DT701-ReactionParticipantsMismatch.csv       1 row
  –  DT103-ExtraParticipantInDiagram.csv          [skipped]
  ·  DT107-WronglyPlacedReactionShape.csv         [no new lines]

━━━ graph-qa ━━━
  ✓  GT037-LiteratureReferenceRelationshipDuplication.csv   2 rows
  ✓  GT090-CatalystActivityCompartmentDoesNotMatchReactionCompartment.csv   2 rows
  –  GT017-NOT_FailedReactionsWithoutOutputs.csv  [skipped]

━━━ release-qa ━━━
  ✓  Entities_With_CoV_Species_Without_Corresponding_Disease.tsv   4 rows
  ✓  ReactionlikeEvent_Regulations_Not_Reviewed.tsv                2 rows
  ✓  Review_Status.tsv                                             3 rows
  –  EHLD_Subpathway_Change.tsv                                    [skipped]

───────────────────────────────────────────────────────
TOTAL: 34 rows across 4 sheets (commandlinerunner, diagram-qa, graph-qa, release-qa)

Proceed? (Reply "yes" to build the tracker, or request adjustments.)
═══════════════════════════════════════════════════════
```

**STOP here.** Wait for the curator to reply "yes" (or equivalent) before
proceeding to Step 3. If the curator requests changes (e.g., "also skip GT037"),
update the skip rules for this run and regenerate the summary before proceeding.

---

## Step 3 — Apply skip rules

### Files to skip entirely

**commandlinerunner**

| File | Reason |
|---|---|
| `Reaction_Compartment.tsv` | Backlog too large; reported to developers |
| `Reaction_Participants_Species_Mismatch.tsv` | Backlog too large; reported to developers |
| `Complex_Compartment_Inconsistency.tsv` | Backlog too large; reported to developers |
| `PathwayEvents_Species_Mismatch.tsv` | Backlog too large; reported to developers |
| `Extra_Compartments_In_Entity_Set_Or_Members.tsv` | Backlog too large; reported to developers |
| `Diagram_EWAS_Modification_Mismatch.tsv` | Diagram-team issue; EWAS modification sync in diagrams not actionable by curators |
| `Diagram_Unsynchronized_Reactions.tsv` | Diagram sync issues handled by diagram team when reactions are updated |
| `summary.tsv` | Aggregate counts only; no per-entity rows |

**diagram-qa**

| File | Reason |
|---|---|
| `DT103-ExtraParticipantInDiagram.csv` | Extra participants in diagram layout; diagram team removes orphaned glyphs |
| `DT105-RenderableClassMismatch.csv` | Renderable class assignment; fixed by diagram team or auto-fixed |
| `DT106-SchemaClassMismatch.csv` | Schema class mismatches (e.g., CellLineagePath vs Pathway); developer/data model fix |
| `DT113-ReactionShapeMismatch.csv` | Volume too large; diagram team handles separately |
| `DT114-ReplacedNodeAttachmentLabel.csv` | Auto-fix labels; not actionable by curators |
| `DT117-ParticipantWrongRole.csv` | Participant role in diagram layout; diagram team handles |

**graph-qa**

| File | Reason |
|---|---|
| `GT017-NOT_FailedReactionsWithoutOutputs.csv` | Reactions without outputs not flagged as FailedReaction; known backlog, specialist review |
| `GT018-DatabaseObjectsWithoutCreated.csv` | Developer report only |
| `GT022-PhysicalEntityWithoutCompartment.csv` | Developer report only |
| `GT026-EventsWithCyclicPrecedingEvents.csv` | Cyclic preceding-event chains; developer fix |
| `GT027-EntriesWithOtherCyclicRelations.csv` | Developer report only |
| `GT033-OtherRelationsThatPointToTheSameEntry.csv` | Developer report only |
| `GT036-EventsWithoutCompartment.csv` | Developer report only |
| `GT048-InstanceEditCreatesInstanceEdit.csv` | Developer report only |
| `GT049-InstanceEditModifiesInstanceEdit.csv` | Developer report only |
| `GT053-PrecedingEventOutputsNotUsedInReaction.csv` | Developer report only |
| `GT055-DuplicatedCuratedComplexes.csv` | Duplicate complex backlog; handled case-by-case outside tracker |
| `GT058-ComplexesWhereCompartmentDoesNotMatchWithAnyOfTheParticipants.csv` | Complex compartment mismatch backlog; reported to developers |
| `GT070-ReactionsWithoutRegulatorWithMoreCompartmentsThanItsParticipants.csv` | Compartment-count check; developer/data model review |
| `GT071-ReactionsWithOnlyOneInputAndOutputWhereSchemaClassDoNotMatch.csv` | Input/output schema class mismatch; developer review |
| `GT101-CompartmentWithCyclicSurroundedByAndInstanceOf.csv` | Developer report only |

**release-qa**

| File | Reason |
|---|---|
| `One_Hop_Circular_Reference.tsv` | All rows involve markerReference/cell — script adjustment needed |
| `Human_Reactions_Without_Disease_And_Have_NonHuman_PhysicalEntities.tsv` | Developer-only backlog; not actionable by curators |
| `Attribute_Has_Only_One_Value.tsv` | Single-member sets/pathways; known QA artifact, reviewed separately |
| `Attribute_Value_Missing.tsv` | Missing attribute values (e.g., BlackBoxEvent without output); reviewed separately |
| `EHLD_Subpathway_Change.tsv` | EHLD subpathway changes notified to EHLD team directly; not curator tracker |
| `Missing_Editorial_Attribute.tsv` | Missing edited/reviewed attributes; tracked separately via editorial workflow |
| `Two_Attributes_Refer_To_Same_Instance.tsv` | Duplicate attribute references; developer/data model fix |
| `summary.tsv` | Aggregate counts only; no per-entity rows |

**All tools — pattern-based skip**

Skip any file whose name contains `_Summary_` (case-sensitive) — these are
version-tagged summary files (e.g., `DiagramQA_Summary_v97.csv`,
`GraphQA_Summary_v97.csv`) that contain aggregate counts, not per-entity rows.

### Row-level filters (applied after file-level skip)

Drop any row where:

1. **markerReference / cell**: any field contains both `"markerReference"` and
   `"cell"` (case-insensitive).
2. **UniProt / Interactions Importer**: any field contains `"UniProt"` or
   `"Interactions Importer"`.
3. **Blank rows**: all fields are empty or whitespace.

### Skip-rule implementation

```python
SKIP_FILES = {
    'commandlinerunner': {
        'Reaction_Compartment.tsv',
        'Reaction_Participants_Species_Mismatch.tsv',
        'Complex_Compartment_Inconsistency.tsv',
        'PathwayEvents_Species_Mismatch.tsv',
        'Extra_Compartments_In_Entity_Set_Or_Members.tsv',
        'Diagram_EWAS_Modification_Mismatch.tsv',
        'Diagram_Unsynchronized_Reactions.tsv',
        'summary.tsv',
    },
    'diagram-qa': {
        'DT103-ExtraParticipantInDiagram.csv',
        'DT105-RenderableClassMismatch.csv',
        'DT106-SchemaClassMismatch.csv',
        'DT113-ReactionShapeMismatch.csv',
        'DT114-ReplacedNodeAttachmentLabel.csv',
        'DT117-ParticipantWrongRole.csv',
    },
    'graph-qa': {
        'GT017-NOT_FailedReactionsWithoutOutputs.csv',
        'GT018-DatabaseObjectsWithoutCreated.csv',
        'GT022-PhysicalEntityWithoutCompartment.csv',
        'GT026-EventsWithCyclicPrecedingEvents.csv',
        'GT027-EntriesWithOtherCyclicRelations.csv',
        'GT033-OtherRelationsThatPointToTheSameEntry.csv',
        'GT036-EventsWithoutCompartment.csv',
        'GT048-InstanceEditCreatesInstanceEdit.csv',
        'GT049-InstanceEditModifiesInstanceEdit.csv',
        'GT053-PrecedingEventOutputsNotUsedInReaction.csv',
        'GT055-DuplicatedCuratedComplexes.csv',
        'GT058-ComplexesWhereCompartmentDoesNotMatchWithAnyOfTheParticipants.csv',
        'GT070-ReactionsWithoutRegulatorWithMoreCompartmentsThanItsParticipants.csv',
        'GT071-ReactionsWithOnlyOneInputAndOutputWhereSchemaClassDoNotMatch.csv',
        'GT101-CompartmentWithCyclicSurroundedByAndInstanceOf.csv',
    },
    'release-qa': {
        'One_Hop_Circular_Reference.tsv',
        'Human_Reactions_Without_Disease_And_Have_NonHuman_PhysicalEntities.tsv',
        'Attribute_Has_Only_One_Value.tsv',
        'Attribute_Value_Missing.tsv',
        'EHLD_Subpathway_Change.tsv',
        'Missing_Editorial_Attribute.tsv',
        'Two_Attributes_Refer_To_Same_Instance.tsv',
        'summary.tsv',
    },
}

def should_skip_file(tool, filename):
    if '_Summary_' in filename:
        return True
    return filename in SKIP_FILES.get(tool, set())

def should_skip_row(row_values):
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
claude.ai Projects, or to the user's Desktop / current directory when running
locally. Call `present_files` at the end if available.

### Output filename

```python
filename = f"{new_label}_QA_Curator_Tracker.xlsx"
```

### Sheets

| Sheet | Content |
|---|---|
| 📋 Overview | Version info, status legend, sheet directory |
| commandlinerunner | All commandlinerunner sections (after filtering) |
| diagram-qa | All diagram-qa sections (after filtering) |
| graph-qa | All graph-qa sections (after filtering) |
| release-qa | All release-qa sections (after filtering) |

Only create sheets for tools that have at least one data row after filtering.

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
| Column header row | `D6E4F0` (dark-blue text `1F4E79`) |
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

Status and Comments header cells use the dark navy fill (`1F4E79`, white text)
to distinguish them from source-data column headers.

### Status dropdown

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

Each QA file gets a merged bold section-header row spanning all columns.

Emoji severity cues:

| Emoji | When to use |
|---|---|
| 🔴 | Missing or null required attributes |
| 🟠 | Compartment, structural, or species issues |
| 🟡 | Diagram warnings, review-status items |
| 🔵 | Diagram-QA entries (DT files) |
| 🔶 | Graph-QA entries (GT files) |
| 🟣 | Release-QA entries (EHLD, Two_Attributes, editorial, regulation, review) |

---

## Known column schemas

Headers are inferred from the first line of each section. These schemas are
provided as a reference for known files; fall back to `Col 1`, `Col 2`, … if
the header row is absent.

### commandlinerunner

| File | Columns |
|---|---|
| `Mandatory_Attributes.tsv` | DB_ID \| DisplayName \| SchemaClass \| NullAttributes \| LastAuthor |
| `Reaction_Input_Output_Imbalance.tsv` | DB_ID \| DisplayName \| LastAuthor |
| `summary.tsv` | Category \| Count (skip — aggregate data) |

### diagram-qa

| File | Columns |
|---|---|
| `DT701-ReactionParticipantsMismatch.csv` | Pathway \| PathwayName \| Reaction \| ReactionName \| Participant \| ParticipantName \| Role \| Created \| Modified |
| `DT110-OverlappingEntities.csv` | Diagram \| DiagramName \| Entity \| EntityName \| Created \| Modified |
| `DT115-NodeAttachmentMismatch.csv` | Diagram \| DiagramName \| Reaction \| ReactionName \| Entity \| EntityName \| Created \| Modified |
| Other `DT*.csv` | Infer from header row |

### graph-qa

| File | Columns |
|---|---|
| `GT037-LiteratureReferenceRelationshipDuplication.csv` | dbIdA \| stIdA \| NameA \| dbIdB \| NameB \| Created \| Modified |
| `GT090-CatalystActivityCompartmentDoesNotMatchReactionCompartment.csv` | Identifier \| Reaction \| Created \| Modified |
| `GT029-ReactionsLikeEventWithoutInput.csv` | Identifier \| Name \| Created \| Modified |
| `GT030-PhysicalEntitiesWithMoreThanOneCompartment.csv` | Infer from header |
| `GT032-PrecedingEventOrReverseReactionOrHasEventPointToSameEntry.csv` | Infer from header |
| `GT059-DuplicatedCandidateSets.csv` | Infer from header |
| `GT061-EntitySetsWithOnlyOneMember.csv` | Infer from header |
| `GT064-DuplicatedEntitySets.csv` | Infer from header |
| `GT091-ReactionsWithoutLiteratureReference.csv` | Infer from header |
| Other `GT*.csv` | Infer from header row |

### release-qa

| File | Columns |
|---|---|
| `Review_Status.tsv` | DB_ID \| DisplayName \| Issue \| LastIE \| Note \| Severity |
| `ReactionlikeEvent_Regulations_Not_Reviewed.tsv` | DBID \| DisplayName \| SchemaClass \| Issue \| MostRecentAuthor |
| `Entities_With_CoV_Species_Without_Corresponding_Disease.tsv` | DB_ID_Entity \| DisplayName_Entity \| ClassName_Entity \| MostRecentAuthor_Entity \| Issue |
| `Reaction_Single_Input_Output_Schema_Not_Matched.tsv` | Infer from header |
| `DatabaseObject_With_Self_Loop.tsv` | Infer from header |
| `Diagram_Disease_Color.tsv` | Infer from header |
| `Diagram_Wrong_Renderable_Class.tsv` | Infer from header |
| `Instance_Duplication.tsv` | Infer from header |
| `Reference_Database_Access_URL.tsv` | Infer from header |
| `Stable_Identifier.tsv` | Infer from header |
| `CoV-2_Entities_With_CoV-1_Species_Or_DisplayName.tsv` | Infer from header |
| `CoV-2_Infection_Pathway_Events_With_Summation_And_Literature_Reference_Issues.tsv` | Infer from header |
| `summary.tsv` | Category \| Count (skip — aggregate data) |

---

## Step-by-step workflow

1. Ask for OLD_DIR, NEW_DIR, and script location (Step 1).
2. Extract version labels from directory basenames.
3. Confirm directories exist.
4. Detect directory structure (subdirs vs flat); apply alias mapping.
5. Run `compare_dirs.sh` per QA tool; capture output to `/tmp/<tool>_comparison.txt` (Step 2).
6. Parse each temp file into `{tool: {filename: {status, lines}}}`.
7. Apply file-level skip rules to identify included vs skipped files per tool.
8. **STOP — present intermediate review summary** (Step 2.5). Wait for curator to reply "yes".
9. Apply row-level filters to included files.
10. Instantiate `openpyxl.Workbook()`.
11. Write `📋 Overview` sheet.
12. For each tool with remaining data, create a sheet:
    a. Write top header row (merged, navy, includes `comparison_label`).
    b. For each QA file (section):
       - Write section header row (merged, blue, with emoji).
       - Write column header row (light blue fill, navy text; Status/Comments in navy).
       - Write data rows with alternating fill.
       - Write Status cell (`Not Done`, red fill, dropdown).
       - Write Comments cell (blank).
       - Register DataValidation for the Status column range.
13. Set column widths; freeze panes at `A2` for every data sheet.
14. Save to output path; call `present_files`.

---

## Column width reference

| Content type | Width |
|---|---|
| DB_ID / numeric ID | 12–14 |
| Stable ID (R-HSA-…) | 18–20 |
| Short name / class / schema | 22–24 |
| Long name / display name | 36–44 |
| Issue description | 32–40 |
| Author / date | 24–26 |
| Status | 12 |
| Comments | 30 |

---

## Adapting to new files

When a source directory contains QA files not listed above:

- Infer column headers from the first (header) row of the TSV/CSV.
- Derive a readable section title from the filename (strip underscores, add spaces).
- Apply the same Status + Comments columns at the end.
- Choose emoji: 🔴 if "missing" appears in the name, 🔶 if it starts with GT, 🔵 if DT, 🟠 otherwise.
- Do **not** add the file to any skip list unless the curator instructs you to.

---

## Handling alternative inputs (no directories available)

If the user provides a Google Sheets URL or uploaded file instead of running
the comparison script:

1. Fetch the file with the Google Drive fetch tool using the document ID from
   the URL, or read the uploaded file with `pandas.read_excel`.
2. Skip Steps 1–2.
3. Apply skip rules (Step 3) to the fetched data.
4. Present intermediate review summary; wait for confirmation.
5. Proceed to Step 4 (produce the tracker workbook).

---

## Dependencies

- `openpyxl` (`pip install openpyxl --break-system-packages`)
- `compare_dirs.sh` — included in this skill directory
- Google Drive fetch tool (for Sheets URLs, when running in claude.ai Projects)
- `present_files` tool (to deliver output in claude.ai Projects)

---

## compare_dirs.sh

The comparison script is included in this skill directory at
`.claude/skills/release-qa-tracker/compare_dirs.sh`. Full content:

```bash
#!/bin/bash

# Compare matching files in two directories and report
# lines that are new in the "new" directory versions.
#
# Usage:
#   ./compare_dirs.sh /path/to/old_dir /path/to/new_dir
#
# Example:
#   ./compare_dirs.sh ./old_output ./new_output

set -euo pipefail

OLD_DIR="${1:-}"
NEW_DIR="${2:-}"

if [[ -z "$OLD_DIR" || -z "$NEW_DIR" ]]; then
    echo "Usage: $0 OLD_DIR NEW_DIR"
    exit 1
fi

if [[ ! -d "$OLD_DIR" ]]; then
    echo "Error: OLD_DIR does not exist: $OLD_DIR"
    exit 1
fi

if [[ ! -d "$NEW_DIR" ]]; then
    echo "Error: NEW_DIR does not exist: $NEW_DIR"
    exit 1
fi

TMP_DIR=$(mktemp -d)

cleanup() {
    rm -rf "$TMP_DIR"
}

trap cleanup EXIT

echo "Comparing files..."
echo

find "$NEW_DIR" -type f | while read -r NEW_FILE; do

    # Relative path inside NEW_DIR
    REL_PATH="${NEW_FILE#$NEW_DIR/}"

    OLD_FILE="$OLD_DIR/$REL_PATH"

    echo "=================================================="
    echo "File: $REL_PATH"

    if [[ ! -f "$OLD_FILE" ]]; then
        echo "No matching old file found."
        echo "Entire file is new:"
        cat "$NEW_FILE"
        echo
        continue
    fi

    OLD_SORTED="$TMP_DIR/old.sorted"
    NEW_SORTED="$TMP_DIR/new.sorted"

    sort "$OLD_FILE" > "$OLD_SORTED"
    sort "$NEW_FILE" > "$NEW_SORTED"

    NEW_LINES=$(comm -13 "$OLD_SORTED" "$NEW_SORTED")

    if [[ -n "$NEW_LINES" ]]; then
        echo "New lines:"
        echo "$NEW_LINES"
    else
        echo "No new lines."
    fi

    echo
done
```
