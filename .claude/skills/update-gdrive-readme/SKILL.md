---
name: update-gdrive-readme
description: Regenerate the Reactome Team Drive README Google Doc. Clears the existing doc, walks the live Team Drive folder inventory, and rewrites the doc with formatted headings, tables, hyperlinks, and a live folder inventory. Use after Team Drive structure changes or for periodic refresh.
---

# Update Google Drive README Skill

## Purpose

Regenerate the Reactome Team Drive README as a richly formatted Google Doc.
On every run the script:

1. Clears the existing doc content
2. Walks the Team Drive (live folder inventory via Drive API)
3. Writes all content via Google Docs API batchUpdate

Target doc: https://docs.google.com/document/d/1kYvy6eIj-BnmbSoD7Fbo6H-Fzx4jiOvazY5xdi_xmHc/edit

The script is at: @update_drive_readme.py

## Invocation

    /update-gdrive-readme [--dry-run] [--depth N]

    --dry-run   Print the first 10 API requests to stdout; do not write to the doc.
    --depth N   Folder levels to inventory (default: 2).

## Prerequisites

1. Python 3:
       python3 --version

2. Google API client libraries:
       pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

3. OAuth credentials (default mode, USE_SERVICE_ACCOUNT = False):
   - Obtain a `credentials.json` client secrets file from the Google Cloud Console
     for the project that has Drive and Docs API enabled.
   - Place `credentials.json` beside `update_drive_readme.py`.
   - On first run a browser window opens for the OAuth consent flow.
   - The token is cached in `token.json` beside the script for subsequent runs.

   Service account alternative:
   - Set USE_SERVICE_ACCOUNT = True in the script.
   - Place `service_account.json` beside the script (or set
     GOOGLE_APPLICATION_CREDENTIALS to its path).
   - The service account must be a Content Manager on the Team Drive.

4. The caller must have edit access to the target Google Doc.

If any prerequisite is missing, stop and help the user resolve it before running.

## Running the Script

Run from the skill directory:

    # Live update — clears and rewrites the doc
    python3 update_drive_readme.py

    # Preview only — prints first 10 requests, does not touch the doc
    python3 update_drive_readme.py --dry-run

    # Inventory 3 folder levels deep instead of the default 2
    python3 update_drive_readme.py --depth 3

On success the script prints:
- Progress lines (authenticating, walking, building, request count)
- Chunked send progress (500 requests per batch)
- Final doc URL

## What the Script Writes

The regenerated doc contains these sections in order:

| Section | Content |
|---|---|
| Title block | Drive ID, Drive URL, last-updated date, maintainer |
| Top-level structure | Table: Folder / Purpose / Primary audience (with Drive folder links) |
| Folder detail | Narrative + bullet sub-items for key top-level folders |
| Conventions | File naming, new folder policy, archiving, permissions |
| Contacts | Table: Role / Name / Institution / Email |
| Live folder inventory | Auto-generated tree from Drive API at run time |
| Known issues | Bulleted list of recommended clean-up actions |

## Safety Notes

- `--dry-run` is safe — it does not modify the doc.
- Every live run **completely clears** the doc before rewriting. Do not run on
  a doc that contains hand-edited content you want to keep.
- `token.json` contains OAuth refresh credentials. Do not commit it to git.
  It is listed in `.gitignore` by convention; confirm before committing.

## Updating FOLDER_META / CONTACTS / KNOWN_ISSUES

These are hardcoded in the script's CONFIG block (lines 58–89). Edit the script
directly when the Team Drive structure changes, contacts change, or known issues
are resolved. Then re-run to push the update to the doc.

## Interpreting Errors

### Missing dependencies
    ModuleNotFoundError: No module named 'googleapiclient'
    → pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

### credentials.json not found / OAuth failure
    FileNotFoundError: [Errno 2] No such file or directory: '.../credentials.json'
    → Download OAuth client secrets from Google Cloud Console and place beside the script.

### Insufficient Drive permissions
    HttpError 403 when calling drive().files().list()
    → Confirm the authenticated account is a member of the Team Drive with at least
      Viewer access. Content Manager or above is required for the Docs write step.

### Doc write failure
    HttpError 403 when calling documents().batchUpdate()
    → Confirm the authenticated account has edit access to the target Google Doc
      (README_DOC_ID = 1kYvy6eIj-BnmbSoD7Fbo6H-Fzx4jiOvazY5xdi_xmHc).
