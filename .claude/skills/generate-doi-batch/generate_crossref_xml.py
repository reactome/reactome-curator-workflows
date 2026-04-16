#!/usr/bin/env python3
"""
Generate CrossRef batch XML files for Reactome DOI deposits.

Usage:
    python generate_crossref_xml.py V94
    python generate_crossref_xml.py V94 --output my_output.xml
    python generate_crossref_xml.py V94 --email other@example.com
    python generate_crossref_xml.py V94 --excel /path/to/DOIs.xlsx
"""

import argparse
import sys
import re
from pathlib import Path

import pandas as pd


DEPOSITOR_NAME = "Reactome"
DEFAULT_EMAIL = "gillespm@gmail.com"
SCHEMA_VERSION = "5.3.1"
DATABASE_DOI = "10.3180/19341792"
DATABASE_URL = "http://www.reactome.org"


def parse_args():
    parser = argparse.ArgumentParser(description="Generate CrossRef batch XML for Reactome")
    parser.add_argument("worksheet", help="Worksheet name, e.g. V94")
    parser.add_argument("--excel", default=None,
                        help="Path to DOIs.xlsx (default: DOIs.xlsx in same directory as script)")
    parser.add_argument("--output", default=None,
                        help="Output XML file path (default: <version_number>.xml)")
    parser.add_argument("--email", default=DEFAULT_EMAIL,
                        help=f"Depositor email address (default: {DEFAULT_EMAIL})")
    return parser.parse_args()


def load_data(excel_path, worksheet):
    xl = pd.ExcelFile(excel_path)
    if worksheet not in xl.sheet_names:
        sys.exit(f"Error: worksheet '{worksheet}' not found. Available: {xl.sheet_names}")

    df = pd.read_excel(excel_path, sheet_name=worksheet)
    release = pd.read_excel(excel_path, sheet_name="Release")
    release.columns = release.columns.str.strip()

    return df, release


def get_release_date(release_df, version_number):
    row = release_df[release_df["Version"] == version_number]
    if row.empty:
        sys.exit(f"Error: version {version_number} not found in Release sheet.")
    row = row.iloc[0]
    return int(row["Release Year"]), int(row["Release Month"]), int(row["Release Day"])


def orcid_url(orcid_value):
    """Ensure ORCID is a full URL."""
    if pd.isna(orcid_value) or str(orcid_value).strip() == "":
        return None
    orcid = str(orcid_value).strip()
    if orcid.startswith("https://orcid.org/"):
        return orcid
    return f"https://orcid.org/{orcid}"


def xml_escape(text):
    if not isinstance(text, str):
        text = str(text)
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def render_person(given, surname, orcid_val, sequence, role):
    lines = []
    lines.append(f'\t\t<person_name sequence="{sequence}" contributor_role="{role}"> ')
    lines.append(f'<given_name>{xml_escape(given)}</given_name>')
    lines.append(f'<surname>{xml_escape(surname)}</surname>')
    url = orcid_url(orcid_val)
    if url:
        lines.append(f'<ORCID authenticated="true">{url}</ORCID>')
    lines.append('</person_name>')
    lines.append('')
    return "\n".join(lines)


def render_dataset(project_rows, release_month, release_day, release_year):
    """Render one <dataset> block from a group of rows sharing the same Project_ID."""
    first_row = project_rows.iloc[0]
    title = str(first_row["Project"]).strip()
    stable_id = str(first_row["StableID"]).strip()

    # Build contributor blocks
    contributor_blocks = []

    # External contributors (reviewers) from Contributor columns
    for i, (_, row) in enumerate(project_rows.iterrows()):
        given = str(row["Contributor Given"]).strip() if pd.notna(row["Contributor Given"]) else ""
        surname = str(row["Contributor Surname"]).strip() if pd.notna(row["Contributor Surname"]) else ""
        role = str(row["Contributor Role"]).strip().lower() if pd.notna(row["Contributor Role"]) else "reviewer"
        orcid = row["Contributor ORCID"]
        if given or surname:
            sequence = "first" if i == 0 else "additional"
            contributor_blocks.append(render_person(given, surname, orcid, sequence, role))

    # Curator as editor (always additional)
    cur_given = str(first_row["Curator Given"]).strip() if pd.notna(first_row["Curator Given"]) else ""
    cur_surname = str(first_row["Curator Surname"]).strip() if pd.notna(first_row["Curator Surname"]) else ""
    cur_orcid = first_row["Curator ORCID"]
    if cur_given or cur_surname:
        contributor_blocks.append(render_person(cur_given, cur_surname, cur_orcid, "additional", "editor"))

    contributors_xml = "\n".join(contributor_blocks)

    doi = f"10.3180/{stable_id}"
    resource = f"http://reactome.org/content/detail/{stable_id}"

    return f"""\
<dataset dataset_type="collection">

\t<contributors>

{contributors_xml}
\t</contributors>

\t<titles>

<title>{xml_escape(title)}</title>

\t</titles>

\t<database_date>\t\t\t\t\t
\t\t<update_date>
\t\t\t<month>{release_month:02d}</month>
\t\t\t<day>{release_day:02d}</day>
\t\t\t<year>{release_year}</year>
\t\t</update_date>
\t</database_date>

\t<doi_data>

<doi>{doi}</doi>
<resource>{resource}</resource>

\t</doi_data>

</dataset>"""


def generate_xml(worksheet, df, release_df, email):
    version_number = int(re.sub(r"[^0-9]", "", worksheet))
    year, month, day = get_release_date(release_df, version_number)

    batch_id = f"{version_number * 100000:09d}"
    timestamp = f"{year}{month:02d}{day:02d}1230"

    # Group rows by Project_ID, preserving first-occurrence order
    seen = []
    groups = {}
    for _, row in df.iterrows():
        pid = row["Project_ID"]
        if pid not in groups:
            seen.append(pid)
            groups[pid] = []
        groups[pid].append(row)

    dataset_blocks = []
    for pid in seen:
        rows = pd.DataFrame(groups[pid])
        block = render_dataset(rows, month, day, year)
        dataset_blocks.append(block)

    datasets_xml = "\n                        \n<!-- ============== -->\n\n".join(dataset_blocks)

    return f"""\
<?xml version="1.0" encoding="UTF-8"?>
<doi_batch version="{SCHEMA_VERSION}" xmlns="http://www.crossref.org/schema/{SCHEMA_VERSION}" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.crossref.org/schema/{SCHEMA_VERSION} http://www.crossref.org/schemas/crossref{SCHEMA_VERSION}.xsd">
        <head>
                <doi_batch_id>{batch_id}</doi_batch_id>
                <timestamp>{timestamp}</timestamp>
                <depositor>
                        <depositor_name>{DEPOSITOR_NAME}</depositor_name>
                        <email_address>{xml_escape(email)}</email_address>
                </depositor>
                <registrant>{DEPOSITOR_NAME}</registrant>
        </head>
        <body>
                <database>
                        <database_metadata language="en">
                                <titles><title>Reactome</title></titles>
                                <institution>
                                        <institution_name>Reactome - a curated knowledgebase of biological pathways</institution_name>
                                        <institution_acronym>Reactome</institution_acronym>
                                </institution>
                                <doi_data>
                                        <doi>{DATABASE_DOI}</doi>
                                        <resource>{DATABASE_URL}</resource>
                                </doi_data>
                        </database_metadata>

<!-- ============== -->

{datasets_xml}

<!-- ============== -->


                </database>
        </body>
</doi_batch>"""


def main():
    args = parse_args()

    if args.excel:
        excel_path = Path(args.excel)
    else:
        excel_path = Path(__file__).parent / "Not Submitted" / "DOIs.xlsx"
        if not excel_path.exists():
            excel_path = Path(__file__).parent / "DOIs.xlsx"
        if not excel_path.exists():
            sys.exit("Error: DOIs.xlsx not found. Use --excel to specify the path.")

    version_number = int(re.sub(r"[^0-9]", "", args.worksheet))
    output_path = args.output or str(Path(__file__).parent / f"{version_number}.xml")

    df, release_df = load_data(excel_path, args.worksheet)
    xml_content = generate_xml(args.worksheet, df, release_df, args.email)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_content)

    print(f"Generated: {output_path}")
    print(f"  Version:      {args.worksheet} (batch ID {version_number * 100000:09d})")
    print(f"  Release date: {release_df[release_df['Version'] == version_number].iloc[0]['Release Month']:02d}/{release_df[release_df['Version'] == version_number].iloc[0]['Release Day']:02d}/{release_df[release_df['Version'] == version_number].iloc[0]['Release Year']}")
    print(f"  Datasets:     {df['Project_ID'].nunique()}")


if __name__ == "__main__":
    main()
