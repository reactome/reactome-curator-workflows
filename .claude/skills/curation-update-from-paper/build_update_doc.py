#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render a Reactome "curation update spec" (JSON) into a formatted .docx.

Usage:
    build_update_doc.py <spec.json> [-o OUTPUT.docx]
    build_update_doc.py <spec.json> --validate

The spec describes a proposed Reactome curation update derived from a single
source paper: what the target pathway already contains, what the paper changes,
the new physical entities and events to be added, the ontology terms needed,
and the literature backing every event.

The rendered document is a *pre-curation* working document for a curator; it
does not touch the database.

Target runtime: Python 3.9+ (no match statements, no PEP 604 unions).
Requires: python-docx
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    import docx  # noqa: F401
    from docx import Document
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Inches, Pt, RGBColor
except ImportError:  # pragma: no cover - environment problem, not a spec problem
    sys.stderr.write(
        "error: python-docx is not installed. Install it with:\n"
        "    pip3 install --user python-docx\n"
    )
    raise SystemExit(2)


# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

BASE_FONT = "Calibri"
BASE_SIZE = Pt(10.5)

GREY = RGBColor(0x59, 0x59, 0x59)
LINK_BLUE = "0563C1"
HEADER_SHADE = "D9E2F3"
LABEL_SHADE = "F2F2F2"

REACTOME_DETAIL = "https://reactome.org/content/detail/"
PUBMED_BASE = "https://pubmed.ncbi.nlm.nih.gov/"

SECTIONS: Sequence[Tuple[str, str]] = (
    ("1", "Summary"),
    ("2", "Curation rationale and logic"),
    ("3", "Gap analysis against the existing pathway"),
    ("4", "Proposed new physical entities"),
    ("5", "Proposed new events"),
    ("6", "Ontology terms required"),
    ("7", "References"),
    ("8", "Open questions for the curator"),
    ("9", "Pre-submission checklist"),
)

# pmid_source vocabulary. Anything else is a validation error.
FIXED_PMID_SOURCES = frozenset(
    ("esummary:pmid", "esearch:doi", "esearch:title-author")
)
INLINE_PREFIX = "inline:"


# ──────────────────────────────────────────────────────────────────────────────
# Small defensive helpers
# ──────────────────────────────────────────────────────────────────────────────


def get(obj: Any, key: str, default: Any = None) -> Any:
    """dict.get() that tolerates None / non-dict input."""
    if isinstance(obj, dict):
        value = obj.get(key, default)
        return default if value is None else value
    return default


def raw(obj: Any, key: str) -> Any:
    """dict.get() preserving None (needed to distinguish None from False/'')."""
    if isinstance(obj, dict):
        return obj.get(key)
    return None


def as_list(value: Any) -> List[Any]:
    """Coerce a spec value into a list; tolerate a bare string or None."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [v for v in value if v is not None]
    return [value]


def as_text(value: Any) -> str:
    """Render a scalar spec value as display text."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, str):
        return value.strip()
    return str(value)


def is_blank(value: Any) -> bool:
    """True when a value should be treated as absent for rendering purposes."""
    if value is None:
        return True
    if isinstance(value, bool):
        return False
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, dict)):
        return len(value) == 0
    return False


# ──────────────────────────────────────────────────────────────────────────────
# Low-level docx helpers (hyperlinks, shading, fields)
# ──────────────────────────────────────────────────────────────────────────────


def add_hyperlink(paragraph, url: str, text: str, color: str = LINK_BLUE,
                  underline: bool = True, size: Optional[Pt] = None,
                  italic: bool = False):
    """Append a real Word hyperlink to `paragraph`.

    python-docx has no public helper for this, so build the w:hyperlink element
    by hand and register an external relationship on the owning part.
    """
    url = (url or "").strip()
    text = text if text else url
    if not url:
        # Nothing to link to - degrade to plain text so we never lose content.
        run = paragraph.add_run(text)
        if size is not None:
            run.font.size = size
        run.italic = italic
        return None

    part = paragraph.part
    r_id = part.relate_to(url, RT.HYPERLINK, is_external=True)

    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)

    new_run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")

    rStyle = OxmlElement("w:rStyle")
    rStyle.set(qn("w:val"), "Hyperlink")
    rPr.append(rStyle)

    if color:
        c = OxmlElement("w:color")
        c.set(qn("w:val"), color)
        rPr.append(c)
    if underline:
        u = OxmlElement("w:u")
        u.set(qn("w:val"), "single")
        rPr.append(u)
    if italic:
        i = OxmlElement("w:i")
        rPr.append(i)
    if size is not None:
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), str(int(size.pt * 2)))
        rPr.append(sz)

    new_run.append(rPr)

    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    new_run.append(t)

    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)
    return hyperlink


def set_cell_shading(cell, hex_fill: str) -> None:
    """Apply a solid background fill to a table cell via <w:shd>."""
    tcPr = cell._tc.get_or_add_tcPr()
    for existing in tcPr.findall(qn("w:shd")):
        tcPr.remove(existing)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def repeat_header_row(row) -> None:
    """Mark a table row as a header row that repeats across page breaks."""
    trPr = row._tr.get_or_add_trPr()
    for existing in trPr.findall(qn("w:tblHeader")):
        trPr.remove(existing)
    tblHeader = OxmlElement("w:tblHeader")
    tblHeader.set(qn("w:val"), "true")
    trPr.append(tblHeader)


def set_table_autofit(table) -> None:
    """Force the autofit (content-sized) layout algorithm on a table."""
    table.autofit = True
    tblPr = table._tbl.tblPr
    for existing in tblPr.findall(qn("w:tblLayout")):
        tblPr.remove(existing)
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "autofit")
    tblPr.append(layout)

    for existing in tblPr.findall(qn("w:tblW")):
        tblPr.remove(existing)
    tblW = OxmlElement("w:tblW")
    tblW.set(qn("w:type"), "pct")
    tblW.set(qn("w:w"), "5000")  # 100% of the text column
    tblPr.append(tblW)


def add_field(paragraph, instruction: str) -> None:
    """Insert a Word field code (e.g. PAGE, NUMPAGES) into a paragraph."""
    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " %s " % instruction
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    for el in (fld_begin, instr, fld_sep, fld_end):
        run._r.append(el)


# ──────────────────────────────────────────────────────────────────────────────
# Paragraph / table conveniences
# ──────────────────────────────────────────────────────────────────────────────


def tidy_cell_paragraph(paragraph) -> None:
    """Tighten spacing inside table cells."""
    paragraph.paragraph_format.space_before = Pt(1)
    paragraph.paragraph_format.space_after = Pt(1)


def cell_paragraph(cell):
    """Return the cell's first paragraph, cleared of placeholder text."""
    paragraph = cell.paragraphs[0]
    for run in list(paragraph.runs):
        run._r.getparent().remove(run._r)
    tidy_cell_paragraph(paragraph)
    return paragraph


def write_cell_lines(cell, lines: Sequence[str], bold: bool = False,
                     size: Optional[Pt] = None) -> None:
    """Write one item per line into a cell (soft line breaks, single paragraph)."""
    paragraph = cell_paragraph(cell)
    first = True
    for line in lines:
        text = as_text(line)
        run = paragraph.add_run()
        if not first:
            run.add_break()
        run.add_text(text)
        run.bold = bold
        if size is not None:
            run.font.size = size
        first = False
    if first:  # nothing written at all
        run = paragraph.add_run("")
        if size is not None:
            run.font.size = size


def new_table(doc, headers: Sequence[str], shade: str = HEADER_SHADE):
    """Create a Table Grid table with a shaded, repeating header row."""
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    set_table_autofit(table)
    header_cells = table.rows[0].cells
    for idx, heading in enumerate(headers):
        write_cell_lines(header_cells[idx], [heading], bold=True)
        set_cell_shading(header_cells[idx], shade)
    repeat_header_row(table.rows[0])
    return table


def add_body_paragraphs(doc, paragraphs: Any) -> None:
    """Add a list of plain body paragraphs, skipping blanks."""
    items = as_list(paragraphs)
    if not items:
        add_placeholder(doc)
        return
    for item in items:
        text = as_text(item)
        if text:
            doc.add_paragraph(text)


def add_placeholder(doc, text: str = "(none recorded)") -> None:
    paragraph = doc.add_paragraph()
    run = paragraph.add_run(text)
    run.italic = True
    run.font.color.rgb = GREY


def add_bullets(doc, items: Any, prefix: Optional[str] = None) -> None:
    """Bulleted list; with `prefix` set, use plain paragraphs with that prefix."""
    values = [as_text(v) for v in as_list(items)]
    values = [v for v in values if v]
    if not values:
        add_placeholder(doc)
        return
    for value in values:
        if prefix:
            paragraph = doc.add_paragraph("%s%s" % (prefix, value))
            paragraph.paragraph_format.left_indent = Cm(0.5)
            paragraph.paragraph_format.space_after = Pt(2)
        else:
            doc.add_paragraph(value, style="List Bullet")


def add_labelled_block(doc, label: str, text: str, italic_body: bool = False,
                       quoted: bool = False) -> None:
    """A bold label paragraph followed by its body paragraph."""
    body = as_text(text)
    if not body:
        return
    label_p = doc.add_paragraph()
    label_p.paragraph_format.space_before = Pt(6)
    label_p.paragraph_format.space_after = Pt(0)
    label_run = label_p.add_run(label)
    label_run.bold = True

    if quoted and not (body.startswith("“") or body.startswith('"')):
        body = "“%s”" % body

    body_p = doc.add_paragraph()
    body_p.paragraph_format.left_indent = Cm(0.5)
    body_p.paragraph_format.space_after = Pt(4)
    body_run = body_p.add_run(body)
    body_run.italic = italic_body


# ──────────────────────────────────────────────────────────────────────────────
# Validation
# ──────────────────────────────────────────────────────────────────────────────


def pmid_source_ok(value: Any) -> bool:
    """None is allowed; otherwise the controlled vocabulary or inline:<something>."""
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    value = value.strip()
    if value in FIXED_PMID_SOURCES:
        return True
    if value.startswith(INLINE_PREFIX) and value[len(INLINE_PREFIX):].strip():
        return True
    return False


def has_pmid(obj: Any) -> bool:
    """True when the object carries a bare PMID value."""
    value = raw(obj, "pmid")
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    return True


def validate_spec(spec: Any) -> List[str]:
    """Return a list of human-readable validation errors (empty == valid)."""
    errors: List[str] = []

    if not isinstance(spec, dict):
        return ["spec root must be a JSON object, got %s" % type(spec).__name__]

    allowed_desc = (
        "expected one of esummary:pmid, esearch:doi, esearch:title-author, "
        "inline:<something>, or null"
    )

    # --- events: controlled vocabulary + required when a PMID is present -----
    events = as_list(spec.get("new_events"))
    for idx, event in enumerate(events):
        where = "new_events[%d]" % idx
        label = as_text(raw(event, "label")) or as_text(raw(event, "name"))
        if label:
            where = "%s (%s)" % (where, label)
        if not isinstance(event, dict):
            errors.append("%s: must be a JSON object" % where)
            continue

        source = raw(event, "pmid_source")
        if not pmid_source_ok(source):
            errors.append(
                "%s: invalid pmid_source %r - %s" % (where, source, allowed_desc)
            )
        if has_pmid(event) and source is None:
            errors.append(
                "%s: carries pmid %r but pmid_source is null - every bare PMID "
                "must record how it was resolved" % (where, raw(event, "pmid"))
            )

    # --- other places pmid_source appears: vocabulary check only ------------
    source_paper = spec.get("source_paper")
    if isinstance(source_paper, dict):
        source = raw(source_paper, "pmid_source")
        if not pmid_source_ok(source):
            errors.append(
                "source_paper: invalid pmid_source %r - %s" % (source, allowed_desc)
            )

    for idx, ref in enumerate(as_list(spec.get("references"))):
        if not isinstance(ref, dict):
            errors.append("references[%d]: must be a JSON object" % idx)
            continue
        source = raw(ref, "pmid_source")
        if not pmid_source_ok(source):
            errors.append(
                "references[%d]: invalid pmid_source %r - %s"
                % (idx, source, allowed_desc)
            )

    return errors


# ──────────────────────────────────────────────────────────────────────────────
# Document assembly
# ──────────────────────────────────────────────────────────────────────────────


def configure_document(doc) -> None:
    """Letter page, 2 cm margins, Calibri 10.5pt base font."""
    for section in doc.sections:
        section.page_width = Inches(8.5)
        section.page_height = Inches(11)
        section.left_margin = Cm(2)
        section.right_margin = Cm(2)
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)

    normal = doc.styles["Normal"]
    normal.font.name = BASE_FONT
    normal.font.size = BASE_SIZE
    rpr = normal.element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), BASE_FONT)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.space_before = Pt(0)

    for style_name in ("Title", "Heading 1", "Heading 2", "Heading 3",
                       "List Bullet", "List Number"):
        try:
            style = doc.styles[style_name]
        except KeyError:
            continue
        style.font.name = BASE_FONT
        srpr = style.element.get_or_add_rPr()
        srfonts = srpr.get_or_add_rFonts()
        for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            srfonts.set(qn(attr), BASE_FONT)


def add_footer_page_number(doc) -> None:
    for section in doc.sections:
        footer = section.footer
        footer.is_linked_to_previous = False
        paragraph = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        for run in list(paragraph.runs):
            run._r.getparent().remove(run._r)
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        prefix = paragraph.add_run("Page ")
        prefix.font.size = Pt(8.5)
        prefix.font.color.rgb = GREY
        add_field(paragraph, "PAGE")
        mid = paragraph.add_run(" of ")
        mid.font.size = Pt(8.5)
        mid.font.color.rgb = GREY
        add_field(paragraph, "NUMPAGES")
        for run in paragraph.runs:
            run.font.size = Pt(8.5)
            run.font.color.rgb = GREY


def add_title_block(doc, spec: Dict[str, Any]) -> None:
    title = as_text(spec.get("title")) or "Reactome curation update"
    doc.add_heading(title, level=0)

    subtitle = as_text(spec.get("subtitle"))
    if subtitle:
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(10)
        run = paragraph.add_run(subtitle)
        run.italic = True
        run.font.color.rgb = GREY
        run.font.size = Pt(11)

    pathway = spec.get("target_pathway") or {}
    paper = spec.get("source_paper") or {}

    rows: List[Tuple[str, Any, Optional[str]]] = []

    topic = as_text(spec.get("topic"))
    if topic:
        rows.append(("Topic", topic, None))

    pathway_name = as_text(get(pathway, "name"))
    pathway_st_id = as_text(get(pathway, "st_id"))
    pathway_db_id = as_text(get(pathway, "db_id"))
    pathway_url = as_text(get(pathway, "url")) or (
        REACTOME_DETAIL + pathway_st_id if pathway_st_id else ""
    )
    if pathway_name or pathway_st_id or pathway_db_id:
        bits = [b for b in (pathway_name, pathway_st_id) if b]
        label = " — ".join(bits) if bits else pathway_url
        if pathway_db_id:
            label = "%s (DB_ID %s)" % (label, pathway_db_id)
        rows.append(("Target pathway", label, pathway_url))

    citation = as_text(get(paper, "citation"))
    paper_pmid = as_text(get(paper, "pmid"))
    paper_url = as_text(get(paper, "pmid_url")) or (
        PUBMED_BASE + paper_pmid + "/" if paper_pmid else ""
    )
    paper_label = citation or ("PMID %s" % paper_pmid if paper_pmid else "")
    if paper_label:
        if paper_pmid and citation:
            paper_label = "%s  [PMID %s]" % (citation, paper_pmid)
        rows.append(("Source paper", paper_label, paper_url))

    doi = as_text(get(paper, "doi"))
    doi_url = as_text(get(paper, "doi_url")) or (
        "https://doi.org/" + doi if doi else ""
    )
    if doi:
        rows.append(("DOI", doi, doi_url))

    paper_source = raw(paper, "pmid_source")
    if not is_blank(paper_source):
        rows.append(("PMID source", as_text(paper_source), None))

    date = as_text(spec.get("date"))
    if date:
        rows.append(("Date", date, None))

    author = as_text(spec.get("author"))
    if author:
        rows.append(("Prepared by", author, None))

    if not rows:
        return

    table = doc.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    set_table_autofit(table)
    for label, value, url in rows:
        cells = table.add_row().cells
        write_cell_lines(cells[0], [label], bold=True, size=Pt(9.5))
        set_cell_shading(cells[0], LABEL_SHADE)
        paragraph = cell_paragraph(cells[1])
        if url:
            add_hyperlink(paragraph, url, as_text(value), size=Pt(9.5))
        else:
            run = paragraph.add_run(as_text(value))
            run.font.size = Pt(9.5)
    doc.add_paragraph()


def heading(doc, number: str, title: str):
    return doc.add_heading("%s  %s" % (number, title), level=1)


def render_gap_analysis(doc, rows: Any) -> None:
    items = [r for r in as_list(rows) if isinstance(r, dict)]
    if not items:
        add_placeholder(doc)
        return
    table = new_table(doc, ["Existing event", "ST_ID", "What this paper changes"])
    for item in items:
        cells = table.add_row().cells
        write_cell_lines(cells[0], [as_text(get(item, "existing_event"))])
        st_id = as_text(get(item, "st_id"))
        paragraph = cell_paragraph(cells[1])
        if st_id:
            add_hyperlink(paragraph, REACTOME_DETAIL + st_id, st_id)
        write_cell_lines(cells[2], [as_text(get(item, "what_the_paper_changes"))])


def render_new_entities(doc, rows: Any) -> None:
    items = [r for r in as_list(rows) if isinstance(r, dict)]
    if not items:
        add_placeholder(doc)
        return
    table = new_table(
        doc,
        ["Proposed name", "Class", "Compartment", "Reuses existing", "Status", "Notes"],
    )
    for item in items:
        cells = table.add_row().cells
        write_cell_lines(cells[0], [as_text(get(item, "proposed_name"))])
        write_cell_lines(cells[1], [as_text(get(item, "class"))])
        write_cell_lines(cells[2], [as_text(get(item, "compartment"))])
        reuses = raw(item, "reuses")
        write_cell_lines(cells[3], [as_text(reuses) if not is_blank(reuses) else "—"])
        write_cell_lines(cells[4], [as_text(get(item, "status"))])
        write_cell_lines(cells[5], [as_text(get(item, "notes"))])


def event_attribute_rows(event: Dict[str, Any]) -> List[Tuple[str, Any, Optional[str]]]:
    """Ordered (label, value, url) triples for one event's attribute table.

    `value` is either a string or a list of strings. Rows whose value is blank
    are dropped by the caller.
    """
    pmid = as_text(get(event, "pmid"))
    pmid_url = as_text(get(event, "pmid_url")) or (
        PUBMED_BASE + pmid + "/" if pmid else ""
    )
    pmc_url = as_text(get(event, "pmc_url"))
    pmc_label = ""
    if pmc_url:
        match = re.search(r"(PMC\d+)", pmc_url, re.IGNORECASE)
        pmc_label = match.group(1).upper() if match else pmc_url

    is_chimeric = raw(event, "is_chimeric")

    rows: List[Tuple[str, Any, Optional[str]]] = [
        ("Type", get(event, "type"), None),
        ("Compartment", get(event, "compartment"), None),
        ("Species", get(event, "species"), None),
        ("isChimeric", None if is_chimeric is None else as_text(is_chimeric), None),
        ("Inputs", as_list(raw(event, "inputs")), None),
        ("Outputs", as_list(raw(event, "outputs")), None),
        ("Catalyst", get(event, "catalyst"), None),
        ("Regulators", as_list(raw(event, "regulators")), None),
        ("Preceding event", get(event, "preceding_event"), None),
        ("GO BP", get(event, "go_bp"), None),
        ("GO MF", get(event, "go_mf"), None),
        ("Evidence type", get(event, "evidence_type"), None),
        ("Figure", get(event, "figure"), None),
        ("Authors/Year", get(event, "authors_year"), None),
        ("PMID", pmid, pmid_url),
        ("PMID source", get(event, "pmid_source"), None),
        ("PMC", pmc_label, pmc_url),
        ("Status", get(event, "status"), None),
    ]
    return rows


def render_event(doc, event: Dict[str, Any], index: int) -> None:
    label = as_text(get(event, "label"))
    name = as_text(get(event, "name"))
    if label and name:
        head = "%s — %s" % (label, name)
    else:
        head = label or name or "Event %d" % index
    doc.add_heading(head, level=2)

    rows = [
        (lbl, val, url)
        for (lbl, val, url) in event_attribute_rows(event)
        if not is_blank(val)
    ]

    if rows:
        table = doc.add_table(rows=0, cols=2)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.LEFT
        set_table_autofit(table)
        for lbl, value, url in rows:
            cells = table.add_row().cells
            write_cell_lines(cells[0], [lbl], bold=True)
            set_cell_shading(cells[0], LABEL_SHADE)
            if url:
                paragraph = cell_paragraph(cells[1])
                add_hyperlink(paragraph, url, as_text(value))
            elif isinstance(value, (list, tuple)):
                write_cell_lines(cells[1], [as_text(v) for v in value])
            else:
                write_cell_lines(cells[1], [as_text(value)])
        # Keep the label column narrow; autofit handles the rest.
        for row in table.rows:
            row.cells[0].width = Cm(3.6)

    add_labelled_block(doc, "Summation", get(event, "summation"))
    add_labelled_block(
        doc, "Evidence sentence", get(event, "evidence_sentence"),
        italic_body=True, quoted=True,
    )

    flags = [as_text(f) for f in as_list(raw(event, "flags"))]
    flags = [f for f in flags if f]
    if flags:
        label_p = doc.add_paragraph()
        label_p.paragraph_format.space_before = Pt(6)
        label_p.paragraph_format.space_after = Pt(0)
        label_p.add_run("Flags").bold = True
        for flag in flags:
            doc.add_paragraph(flag, style="List Bullet")


def render_new_events(doc, events: Any) -> None:
    items = [e for e in as_list(events) if isinstance(e, dict)]
    if not items:
        add_placeholder(doc)
        return
    for idx, event in enumerate(items, start=1):
        render_event(doc, event, idx)


def render_ontology_terms(doc, rows: Any) -> None:
    items = [r for r in as_list(rows) if isinstance(r, dict)]
    if not items:
        add_placeholder(doc)
        return
    table = new_table(doc, ["Term label", "Ontology", "Accession / status", "Used by"])
    for item in items:
        cells = table.add_row().cells
        write_cell_lines(cells[0], [as_text(get(item, "term_label"))])
        write_cell_lines(cells[1], [as_text(get(item, "ontology"))])
        write_cell_lines(cells[2], [as_text(get(item, "accession_status"))])
        used_by = raw(item, "used_by")
        if isinstance(used_by, (list, tuple)):
            write_cell_lines(cells[3], [as_text(v) for v in used_by])
        else:
            write_cell_lines(cells[3], [as_text(used_by)])


def render_references(doc, refs: Any) -> None:
    items = [r for r in as_list(refs) if isinstance(r, dict)]
    if not items:
        add_placeholder(doc)
        return
    for idx, ref in enumerate(items, start=1):
        number = raw(ref, "n")
        number_text = as_text(number) if not is_blank(number) else str(idx)

        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.left_indent = Cm(0.9)
        paragraph.paragraph_format.first_line_indent = Cm(-0.9)
        paragraph.paragraph_format.space_after = Pt(2)

        num_run = paragraph.add_run("%s. " % number_text)
        num_run.bold = True
        paragraph.add_run(as_text(get(ref, "citation")))

        pmid = as_text(get(ref, "pmid"))
        pmid_url = as_text(get(ref, "pmid_url")) or (
            PUBMED_BASE + pmid + "/" if pmid else ""
        )
        if pmid:
            paragraph.add_run("  PMID ")
            add_hyperlink(paragraph, pmid_url, pmid)
        elif pmid_url:
            paragraph.add_run("  ")
            add_hyperlink(paragraph, pmid_url, pmid_url)

        note = as_text(get(ref, "note"))
        if note:
            note_run = paragraph.add_run("  — %s" % note)
            note_run.font.size = Pt(9.5)

        source = raw(ref, "pmid_source")
        if not is_blank(source):
            meta = doc.add_paragraph()
            meta.paragraph_format.left_indent = Cm(0.9)
            meta.paragraph_format.space_after = Pt(6)
            meta_run = meta.add_run("PMID source: %s" % as_text(source))
            meta_run.italic = True
            meta_run.font.size = Pt(8.5)
            meta_run.font.color.rgb = GREY


def build_document(spec: Dict[str, Any], output_path: str) -> str:
    doc = Document()
    configure_document(doc)
    add_footer_page_number(doc)
    add_title_block(doc, spec)

    for number, title in SECTIONS:
        heading(doc, number, title)
        if number == "1":
            add_body_paragraphs(doc, spec.get("summary"))
        elif number == "2":
            add_body_paragraphs(doc, spec.get("rationale"))
        elif number == "3":
            render_gap_analysis(doc, spec.get("gap_analysis"))
        elif number == "4":
            render_new_entities(doc, spec.get("new_entities"))
        elif number == "5":
            render_new_events(doc, spec.get("new_events"))
        elif number == "6":
            render_ontology_terms(doc, spec.get("ontology_terms"))
        elif number == "7":
            render_references(doc, spec.get("references"))
        elif number == "8":
            add_bullets(doc, spec.get("open_questions"))
        elif number == "9":
            add_bullets(doc, spec.get("checklist"), prefix="☐  ")

    doc.save(output_path)
    return output_path


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────


def default_output_path(spec: Dict[str, Any], spec_path: str) -> str:
    basename = as_text(spec.get("output_basename"))
    if not basename:
        basename = os.path.splitext(os.path.basename(spec_path))[0]
    if basename.lower().endswith(".docx"):
        basename = basename[: -len(".docx")]
    directory = os.path.dirname(os.path.abspath(spec_path))
    return os.path.join(directory, basename + ".docx")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render a Reactome curation update spec (JSON) into a .docx."
    )
    parser.add_argument("spec", help="path to the curation update spec JSON file")
    parser.add_argument(
        "-o", "--output", default=None,
        help="output .docx path (default: spec's output_basename + .docx, "
             "written beside the spec file)",
    )
    parser.add_argument(
        "--validate", action="store_true",
        help="validate the spec and exit without writing a document",
    )
    args = parser.parse_args(argv)

    spec_path = os.path.abspath(os.path.expanduser(args.spec))
    if not os.path.isfile(spec_path):
        sys.stderr.write("error: spec file not found: %s\n" % spec_path)
        return 1

    try:
        with open(spec_path, "r", encoding="utf-8") as handle:
            spec = json.load(handle)
    except ValueError as exc:
        sys.stderr.write("error: %s is not valid JSON: %s\n" % (spec_path, exc))
        return 1
    except OSError as exc:
        sys.stderr.write("error: could not read %s: %s\n" % (spec_path, exc))
        return 1

    errors = validate_spec(spec)
    if errors:
        sys.stderr.write("Spec validation failed (%d problem%s):\n"
                         % (len(errors), "" if len(errors) == 1 else "s"))
        for error in errors:
            sys.stderr.write("  - %s\n" % error)
        return 1

    if args.validate:
        print("Spec OK: %s" % spec_path)
        return 0

    output_path = (
        os.path.abspath(os.path.expanduser(args.output))
        if args.output else default_output_path(spec, spec_path)
    )
    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.isdir(out_dir):
        sys.stderr.write("error: output directory does not exist: %s\n" % out_dir)
        return 1

    try:
        build_document(spec, output_path)
    except OSError as exc:
        sys.stderr.write("error: could not write %s: %s\n" % (output_path, exc))
        return 1

    print("Wrote %s" % output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
