#!/usr/bin/env python3
"""
update_drive_readme.py
======================
Regenerates the Reactome Team Drive README as a richly formatted Google Doc:
  - Heading 1 / Heading 2 styles
  - Bold labels, monospace inline code, coloured hyperlinks
  - Native Google Docs tables (top-level structure, contacts)
  - Live folder inventory from the Team Drive API

On every run the script:
  1. Clears the existing doc content
  2. Walks the Team Drive (live folder inventory)
  3. Writes all content via Docs API batchUpdate requests

Usage
-----
    python update_drive_readme.py [--dry-run] [--depth 2]

    --dry-run   Print the first 10 requests to stdout; do not write to the doc.
    --depth N   Folder levels to inventory (default: 2).

Requirements
------------
    pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

Credentials
-----------
OAuth user credentials (recommended):
  Set USE_SERVICE_ACCOUNT = False. Place credentials.json (OAuth client secrets
  from Google Cloud Console) at ~/.config/reactome/credentials.json. On first
  run a browser opens for the OAuth consent flow; the token is cached at
  ~/.config/reactome/token.json for subsequent runs. Neither file is inside
  the repo, so credentials are never accidentally committed.

  Override the credentials path via the GOOGLE_APPLICATION_CREDENTIALS env var:
    GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json python update_drive_readme.py

Service account:
  Set USE_SERVICE_ACCOUNT = True and place service_account.json at
  ~/.config/reactome/service_account.json (or set GOOGLE_APPLICATION_CREDENTIALS).
  The service account must be a Content Manager on the Team Drive.
"""

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

# ── CONFIG ─────────────────────────────────────────────────────────────────────

TEAM_DRIVE_ID  = "0AEA6CN2wPFm-Uk9PVA"
TEAM_DRIVE_URL = "https://drive.google.com/drive/folders/0AEA6CN2wPFm-Uk9PVA"

# Existing Google Doc — created 2026-05-11.
# https://docs.google.com/document/d/1kYvy6eIj-BnmbSoD7Fbo6H-Fzx4jiOvazY5xdi_xmHc/edit
README_DOC_ID = "1kYvy6eIj-BnmbSoD7Fbo6H-Fzx4jiOvazY5xdi_xmHc"

SKIP_FOLDER_TITLES = {"Google Documentation Migration"}

# Top-level folder metadata (purpose, audience, Drive folder ID).
FOLDER_META = {
    "Admin - Internal":             ("Budget and other PII material",                                                                              "PI / admin leads",               "1EnesPT4enJifPjsOwV7nDPa0NNW53FCF"),
    "Admin":                        ("Grants, internal management, including teleconferences, group procedures, and compliance",                "PI / admin leads",               "1TpnqN-kIXvJhHnbx1U4g-nhkApsW0q1V"),
    "Curation":                     ("Active curation projects, standards, training, QA materials",   "All team members",               "13mstCTkLINdyJNAjORxzGw8Kh6C0wwYj"),
    "Development":                  ("Software and tooling work",                                     "All team members",               "1U1Dmk1G7IJLcbZElvaoLdcpkpjE3J0-b"),
    "Documentation":                ("Internal documentation",                                        "All team members",               "1JhxhxjzDRjblmP-td1VFLxwaQRU7J6hm"),
    "Google Documentation Migration":("Legacy migration artifacts (candidate for archive)",           "—",                              "1BkXOoSp0ek6ph4roEvMIM5MlOiAYqsCW"),
    "Graphics":                     ("EHLD illustrations, logos, visual assets",                      "All team members",               "1OX6BrVKm3eMG7JAeZvjXqAEA-qbZhk7-"),
    "Outreach":                     ("Conference materials, public communications",                   "All team members",               "1ugvTB8r3qgBIe5Mg1fVWCrMc9tT5pgMT"),
    "Projects":                     ("Cross-functional project workspaces",                           "All team members",               "1Wc5mBuJg8pD9z2EeDRgll0BNT2h6sopP"),
    "Public":                       ("Externally shareable materials (curation, release calendars)",  "External collaborators + all",   "1hH4YqJghnZWtREbqEk5Cy8-TbnYKdvMs"),
    "Release":                      ("Release pipeline, SOPs, QA, calendars, post-mortems",           "All team members",               "16PB91JuVZvCU-JHJrIrPYxK9xy_4VpTR"),
}

CONTACTS = [
    ("PI (OICR)",             "Lincoln Stein",     "OICR",     "lstein@oicr.on.ca"),
    ("PI (EMBL-EBI)",         "Henning Hermjakob", "EMBL-EBI", "HenningHermjakob@gmail.com"),
    ("PI (OHSU)",             "Guanming Wu",       "OHSU",     "guanmingwu@gmail.com"),
    ("PI (SJU/NYU)",          "Marc Gillespie",    "SJU",      "gillespm@stjohns.edu"),
    ("Curation lead (NYU)",   "Lisa Matthews",     "NYU",      "lmatthews.nyumc@gmail.com"),
    ("Software lead (OICR)",  "Adam Wright",       "OICR",     "adam.j.wright82@gmail.com"),
    ("Outreach coordinator",  "Nancy Li",          "OICR",     "nancy.li@reactome.org"),
]

KNOWN_ISSUES = [
    "Google Documentation Migration — completed migration artifact; verify contents then archive or delete.",
    "Admin (original) — legacy folder predating Admin - Internal; review and consolidate.",
    "Loose Curator Tool survey form at drive root — move into Curation/ or Development/.",
    "Curation/ contains folders unmodified since Jan 2022 (Worm Reactome, Igor list validation testing, "
    "Tissue Specificity, Regulation class restructure, Hierarchy restructuring) — candidates for archiving.",
    "No institution-level folders yet (SJU/NYU, OICR, EBI, Oslo, OHSU) — recommended future addition.",
]

CREDENTIALS_PATH = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS",
    str(Path.home() / ".config" / "reactome" / "credentials.json"),
)
USE_SERVICE_ACCOUNT = False  # True = service account, False = OAuth user credentials

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]

FOLDER_MIME = "application/vnd.google-apps.folder"

# Colour constants (RGB 0–1)
BLUE   = {"red": 0.07, "green": 0.36, "blue": 0.65}
GREY   = {"red": 0.45, "green": 0.45, "blue": 0.45}
NAVY   = {"red": 0.12, "green": 0.12, "blue": 0.55}
HDR_BG = {"red": 0.88, "green": 0.91, "blue": 0.97}


# ── AUTH ───────────────────────────────────────────────────────────────────────

def build_services():
    try:
        from googleapiclient.discovery import build
        from google.oauth2 import service_account
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
    except ImportError:
        sys.exit(
            "Missing dependencies:\n"
            "  pip install google-auth google-auth-oauthlib "
            "google-auth-httplib2 google-api-python-client"
        )

    if USE_SERVICE_ACCOUNT:
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_PATH, scopes=SCOPES)
    else:
        token_path = Path.home() / ".config" / "reactome" / "token.json"
        creds = None
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text(creds.to_json())

    return (build("drive", "v3", credentials=creds),
            build("docs",  "v1", credentials=creds))


# ── DRIVE WALK ─────────────────────────────────────────────────────────────────

def list_children(drive_svc, parent_id):
    page_token = None
    while True:
        resp = drive_svc.files().list(
            q=f"'{parent_id}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, mimeType, modifiedTime, webViewLink)",
            pageSize=100,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="drive",
            driveId=TEAM_DRIVE_ID,
            pageToken=page_token,
        ).execute()
        yield from resp.get("files", [])
        page_token = resp.get("nextPageToken")
        if not page_token:
            break


def walk_drive(drive_svc, parent_id, max_depth=2, depth=0):
    if depth > max_depth:
        return []
    items = []
    for f in list_children(drive_svc, parent_id):
        node = dict(id=f["id"], name=f.get("name", ""),
                    mimeType=f["mimeType"],
                    modifiedTime=f.get("modifiedTime", ""),
                    url=f.get("webViewLink", ""),
                    depth=depth, children=[])
        if node["mimeType"] == FOLDER_MIME and node["name"] not in SKIP_FOLDER_TITLES:
            node["children"] = walk_drive(drive_svc, f["id"], max_depth, depth + 1)
        items.append(node)
    items.sort(key=lambda x: (x["mimeType"] != FOLDER_MIME, x["name"].lower()))
    return items


def fmt_date(iso):
    return iso[:10] if iso else "—"


# ── DOCUMENT BUILDER ───────────────────────────────────────────────────────────

class DocBuilder:
    """
    Accumulates Google Docs API batchUpdate requests.
    Tracks a cursor (current insertion point) so callers don't need to manage indices.
    All public methods append to self.requests and advance self._cursor.
    """

    def __init__(self):
        self.requests = []
        self._cursor = 1  # Docs content starts at index 1

    # ── primitives ─────────────────────────────────────────────────────────

    def _insert(self, text):
        """Insert text at cursor; return (start, end); advance cursor."""
        start = self._cursor
        self.requests.append({
            "insertText": {"location": {"index": start}, "text": text}
        })
        self._cursor += len(text)
        return start, self._cursor

    def _para_style(self, start, named_style, space_above=0, space_below=0):
        ps = {"namedStyleType": named_style,
              "spaceAbove": {"magnitude": space_above, "unit": "PT"},
              "spaceBelow": {"magnitude": space_below, "unit": "PT"}}
        self.requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": start, "endIndex": start + 1},
                "paragraphStyle": ps,
                "fields": "namedStyleType,spaceAbove,spaceBelow",
            }
        })

    def _text_style(self, start, end, bold=False, italic=False,
                    font=None, size=None, link=None, fg=None):
        if start >= end:
            return
        ts, fields = {}, []
        if bold:        ts["bold"]               = True;                              fields.append("bold")
        if italic:      ts["italic"]             = True;                              fields.append("italic")
        if font:        ts["weightedFontFamily"] = {"fontFamily": font};              fields.append("weightedFontFamily")
        if size:        ts["fontSize"]           = {"magnitude": size, "unit": "PT"}; fields.append("fontSize")
        if link:        ts["link"]               = {"url": link};                     fields.append("link")
        if fg:          ts["foregroundColor"]    = {"color": {"rgbColor": fg}};       fields.append("foregroundColor")
        if not fields:
            return
        self.requests.append({
            "updateTextStyle": {
                "range": {"startIndex": start, "endIndex": end},
                "textStyle": ts,
                "fields": ",".join(fields),
            }
        })

    # ── block helpers ───────────────────────────────────────────────────────

    def heading1(self, text):
        s, e = self._insert(text + "\n")
        self._para_style(s, "HEADING_1", space_above=14, space_below=4)
        self._text_style(s, e - 1, bold=True, size=20)

    def heading2(self, text):
        s, e = self._insert(text + "\n")
        self._para_style(s, "HEADING_2", space_above=10, space_below=2)
        self._text_style(s, e - 1, bold=True, size=13)

    def para(self, segments, space_above=0, space_below=0):
        """
        segments: list of (text, style_dict).
        style_dict keys: bold, italic, font, size, link, fg (RGB dict).
        """
        para_s = self._cursor
        for text, kw in segments:
            s, e = self._insert(text)
            self._text_style(s, e,
                             bold=kw.get("bold", False),
                             italic=kw.get("italic", False),
                             font=kw.get("font"),
                             size=kw.get("size"),
                             link=kw.get("link"),
                             fg=kw.get("fg"))
        self._insert("\n")
        self._para_style(para_s, "NORMAL_TEXT", space_above, space_below)

    def bullet(self, segments, level=0):
        indent = "\u00a0\u00a0\u00a0\u00a0" * level  # non-breaking spaces for indent
        para_s = self._cursor
        self._insert(indent + "\u2022 ")
        for text, kw in segments:
            s, e = self._insert(text)
            self._text_style(s, e,
                             bold=kw.get("bold", False),
                             italic=kw.get("italic", False),
                             font=kw.get("font"),
                             size=kw.get("size"),
                             link=kw.get("link"),
                             fg=kw.get("fg"))
        self._insert("\n")
        self._para_style(para_s, "NORMAL_TEXT")

    def blank(self):
        s, _ = self._insert("\n")
        self._para_style(s, "NORMAL_TEXT")

    def rule(self):
        s, e = self._insert("\u2500" * 40 + "\n")
        self._text_style(s, e - 1, size=7, fg=GREY)
        self._para_style(s, "NORMAL_TEXT", space_above=6, space_below=6)

    # ── table ───────────────────────────────────────────────────────────────

    def table(self, rows):
        """
        rows: list of rows; each row is a list of cells;
              each cell is a list of (text, style_dict).
        Row 0 is the header (light-blue background, bold text).
        Inserts content back-to-front so earlier indices stay stable.
        """
        n_rows = len(rows)
        n_cols = len(rows[0])
        table_idx = self._cursor

        self.requests.append({
            "insertTable": {
                "rows": n_rows, "columns": n_cols,
                "location": {"index": table_idx},
            }
        })

        # The API places the table at table_idx+1 (after the paragraph char at table_idx).
        # Skeleton per row = row_start(1) + n_cols*(cell_marker(1) + para_content(1)) = 1+n_cols*2.
        # Table skeleton = table_open(1) + n_rows*(1+n_cols*2) + table_close(1) = 2+n_rows*(1+n_cols*2).
        # Cell (i,j) paragraph index = (table_idx+1) + 1(table_open) + i*(1+n_cols*2) + 1(row_open)
        #   + j*2(cells before) + 1(cell_marker) = table_idx + 4 + i*(1+n_cols*2) + j*2
        def cell_para(i, j):
            return table_idx + 4 + i * (1 + n_cols * 2) + j * 2

        # Fill cells in reverse order (last→first) so earlier indices stay valid
        for i in reversed(range(n_rows)):
            for j in reversed(range(n_cols)):
                idx = cell_para(i, j)
                for text, kw in rows[i][j]:
                    self.requests.append({
                        "insertText": {"location": {"index": idx}, "text": text}
                    })
                    if any(kw.get(k) for k in ("bold","italic","font","size","link","fg")):
                        ts, fields = {}, []
                        if kw.get("bold"):   ts["bold"]               = True;                                      fields.append("bold")
                        if kw.get("italic"): ts["italic"]             = True;                                      fields.append("italic")
                        if kw.get("font"):   ts["weightedFontFamily"] = {"fontFamily": kw["font"]};                fields.append("weightedFontFamily")
                        if kw.get("size"):   ts["fontSize"]           = {"magnitude": kw["size"], "unit": "PT"};   fields.append("fontSize")
                        if kw.get("link"):   ts["link"]               = {"url": kw["link"]};                       fields.append("link")
                        if kw.get("fg"):     ts["foregroundColor"]    = {"color": {"rgbColor": kw["fg"]}};         fields.append("foregroundColor")
                        self.requests.append({
                            "updateTextStyle": {
                                "range": {"startIndex": idx, "endIndex": idx + len(text)},
                                "textStyle": ts, "fields": ",".join(fields),
                            }
                        })

            # Header row background
            if i == 0:
                for j in range(n_cols):
                    self.requests.append({
                        "updateTableCellStyle": {
                            "tableRange": {
                                "tableCellLocation": {
                                    "tableStartLocation": {"index": table_idx + 1},
                                    "rowIndex": 0, "columnIndex": j,
                                },
                                "rowSpan": 1, "columnSpan": 1,
                            },
                            "tableCellStyle": {
                                "backgroundColor": {"color": {"rgbColor": HDR_BG}}
                            },
                            "fields": "backgroundColor",
                        }
                    })

        # Advance cursor to the new trailing paragraph created after the table.
        # The API places the table at table_idx+1; skeleton = 2 + n_rows*(1+n_cols*2).
        # The new trailing paragraph starts right after the skeleton.
        # Plus all text inserted into cells — each insertText shifts the table end.
        total_cell_chars = sum(
            len(text) for row in rows for cell in row for text, kw in cell
        )
        self._cursor = table_idx + 3 + n_rows * (1 + n_cols * 2) + total_cell_chars
        self.blank()


# ── DOCUMENT CONTENT ───────────────────────────────────────────────────────────

def build_document(doc: DocBuilder, nodes: list):
    today = datetime.date.today().isoformat()

    # Title
    doc.heading1("Reactome Team Drive — README")

    doc.para([("Drive ID:  ", {"bold": True}),
              ("0AEA6CN2wPFm-Uk9PVA", {"font": "Courier New", "fg": NAVY})])
    doc.para([("Drive URL: ", {"bold": True}),
              ("Team Drive root", {"link": TEAM_DRIVE_URL, "fg": BLUE})])
    doc.para([("Last updated: ", {"bold": True}), (today, {})])
    doc.para([("Maintained by: ", {"bold": True}),
              ("Editor-in-Chief — gillespm@stjohns.edu", {})])
    doc.blank()
    doc.para([
        ("This document is the authoritative map of the Reactome Team Drive. "
         "It is regenerated by ", {"italic": True}),
        ("update_drive_readme.py", {"italic": True, "font": "Courier New"}),
        (" in ", {"italic": True}),
        ("reactome-curator-workflows", {
            "italic": True,
            "link": "https://github.com/reactome/reactome-curator-workflows",
            "fg": BLUE,
        }),
        (". Do not edit by hand — changes will be overwritten on the next run.",
         {"italic": True}),
    ])

    doc.rule()

    # ── Top-level structure ──
    doc.heading2("Top-level structure")

    tbl = [[
        [("Folder",           {"bold": True})],
        [("Purpose",          {"bold": True})],
        [("Primary audience", {"bold": True})],
    ]]
    for name, (purpose, audience, fid) in FOLDER_META.items():
        url = f"https://drive.google.com/drive/folders/{fid}"
        tbl.append([
            [(name,     {"link": url, "fg": BLUE})],
            [(purpose,  {})],
            [(audience, {})],
        ])
    doc.table(tbl)

    doc.rule()

    # ── Folder detail ──
    doc.heading2("Folder detail")

    detail = [
        ("Admin - Internal",
         "Budget and other PII material. Restricted to PI and administrative leads.",
         []),

        ("Curation",
         "Main working area for all curators (~30 sub-folders).",
         [("Standards & guides",       "Curator_Guide, Event_Entity_naming_typing, Annotating modified residues, Compartments and adjacency"),
          ("Active topic projects",    "Arbovirus, Regulation of PD-L1, GO, RNACentral, DOID to EFO mapping"),
          ("Training",                 "New Curator Training, Expert recruitment and communications"),
          ("QA & metrics",             "Statistics and Coverage and Quality metrics, Missing preceding events, General_graph_queries_and_results_files"),
          ("DOIs",                     "DOIs, Automated creation of release DOIs"),
          ("Legacy / archive candidates", "Worm Reactome, Hierarchy restructuring, Regulation class restructure, Igor list validation testing, Update_wiki_reports, Search analysis, Tissue Specificity, Pathways Cross-talk"),
          ("Planning",                 "Curation planning template (spreadsheet), Miscellaneous")]),

        ("Development",
         "Software engineering workspace, separate from Release pipeline tooling.",
         []),

        ("Graphics",
         "Illustrations and visual assets including EHLDs. Used by curators and outreach.",
         []),

        ("Public",
         "Externally shareable mirror of key materials.",
         [("Curation/",      "public-facing curation docs"),
          ("Release Calendars/", "release schedule"),
          ("Documentation/, Development/, Outreach/, Projects/", "mirrored internal folders")]),

        ("Release",
         "Full release lifecycle management.",
         [("Release SOP Documents",     "canonical release procedures"),
          ("Release Calendar",          "upcoming and past release dates"),
          ("Release QA",               "quality checks per release"),
          ("Release document preparation", "release notes, changelogs"),
          ("Release post mortem",      "retrospective notes"),
          ("Release date history",     "historical record (spreadsheet)"),
          ("cumulative_statistics/",   "per-release stats archive"),
          ("Pipeline sub-projects",    "Pipeline refactoring, Release Pipeline Improvements, Orthology prediction overhaul, AWS migration changes"),
          ("Supporting",               "BFRHyperlinks, Stable_IDs, X-refs, Release repository cleanup")]),

    ]

    for folder_name, description, bullets in detail:
        doc.heading2(folder_name)
        doc.para([(description, {})])
        for label, content in bullets:
            doc.bullet([(label + ": ", {"bold": True}), (content, {})])
        if bullets:
            doc.blank()

    doc.rule()

    # ── Conventions ──
    doc.heading2("Conventions")

    for label, text in [
        ("File naming",  "YYYY-MM_Title_vN for versioned documents (e.g. 2026-04_CurationSOP_v3). "
                         "Use underscores, not spaces, in names intended for programmatic access."),
        ("New folders",  "Add to the most specific applicable top-level folder. Content spanning "
                         "multiple folders → use Projects/ with cross-links. New top-level folders "
                         "require Editor-in-Chief approval."),
        ("Archiving",    "Folders inactive for >2 years should be moved to a dated _archive_YYYY "
                         "sub-folder within their parent, or flagged at the quarterly tidy cycle."),
        ("Permissions",  "Access is managed at the Team Drive membership level. External "
                         "collaborators → folder-level commenter access with defined expiry. "
                         "Do not share individual files."),
    ]:
        doc.bullet([(label + ": ", {"bold": True}), (text, {})])
    doc.blank()

    doc.rule()

    # ── Contacts ──
    doc.heading2("Contacts")

    ctbl = [[
        [("Role",        {"bold": True})],
        [("Name",        {"bold": True})],
        [("Institution", {"bold": True})],
        [("Email",       {"bold": True})],
    ]]
    for role, name, inst, email in CONTACTS:
        ctbl.append([
            [(role,  {})],
            [(name,  {"bold": True})],
            [(inst,  {})],
            [(email, {"link": f"mailto:{email}", "fg": BLUE} if email != "—" else {})],
        ])
    doc.table(ctbl)

    doc.rule()

    # ── Live inventory ──
    doc.heading2("Live folder inventory")
    doc.para([("Auto-generated from the Team Drive at time of last script run.",
               {"italic": True, "fg": GREY})])
    doc.blank()

    def render(items, depth=0):
        for n in items:
            icon = "\u25b8 " if n["mimeType"] == FOLDER_MIME else "  "
            segs = [("    " * depth + icon, {})]
            if n["url"]:
                segs.append((n["name"], {"link": n["url"], "fg": BLUE}))
            else:
                segs.append((n["name"], {}))
            segs.append((f"   modified {fmt_date(n['modifiedTime'])}",
                         {"fg": GREY, "italic": True, "size": 9}))
            doc.para(segs)
            if n["children"]:
                render(n["children"], depth + 1)

    render(nodes)
    doc.blank()

    doc.rule()

    # ── Known issues ──
    doc.heading2("Known issues / recommended next steps")
    for issue in KNOWN_ISSUES:
        doc.bullet([(issue, {})])
    doc.blank()


# ── APPLY ──────────────────────────────────────────────────────────────────────

def clear_doc(docs_svc, doc_id):
    doc = docs_svc.documents().get(documentId=doc_id).execute()
    end = doc["body"]["content"][-1].get("endIndex", 1)
    if end > 2:
        docs_svc.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": [{"deleteContentRange": {
                "range": {"startIndex": 1, "endIndex": end - 1}
            }}]},
        ).execute()


def apply(docs_svc, doc_id, requests, dry_run=False):
    if dry_run:
        print(json.dumps(requests[:10], indent=2))
        print(f"… ({len(requests)} total requests)")
        return
    chunk = 500
    for i in range(0, len(requests), chunk):
        docs_svc.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": requests[i:i+chunk]},
        ).execute()
        print(f"  Sent {min(i+chunk, len(requests))}/{len(requests)} requests")


# ── MAIN ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--depth",   type=int, default=2)
    args = parser.parse_args()

    print("Authenticating…")
    drive_svc, docs_svc = build_services()

    print(f"Walking Team Drive (depth={args.depth})…")
    nodes = walk_drive(drive_svc, TEAM_DRIVE_ID, max_depth=args.depth)
    print(f"  {len(nodes)} top-level items found.")

    print("Building document…")
    doc = DocBuilder()
    build_document(doc, nodes)
    print(f"  {len(doc.requests)} API requests generated.")

    if args.dry_run:
        apply(docs_svc, README_DOC_ID, doc.requests, dry_run=True)
        return

    print("Clearing existing content…")
    clear_doc(docs_svc, README_DOC_ID)

    print("Writing formatted content…")
    apply(docs_svc, README_DOC_ID, doc.requests)

    print(f"\nDone — https://docs.google.com/document/d/{README_DOC_ID}/edit")


if __name__ == "__main__":
    main()
