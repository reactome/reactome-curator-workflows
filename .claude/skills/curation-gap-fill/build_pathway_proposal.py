#!/usr/bin/env python3
"""Render a /curation-gap-fill pathway proposal spec as a formatted DOCX.

The document uses the visual language of the internal review
(review-internal/Reactome_InternalReview_TEMPLATE.docx): navy section banners,
grey/white metadata rows, teal headings, and the red/amber/green priority fills.
It carries no reviewer instructions: it is laid out for the curator who reads
the proposal and decides what to build.

Order (decisions first, then the topology, then the logic and detail)
    Executive summary: at a glance, the Primary Curator Decisions, the
                       assessment after internal-review testing, the summary
    Contents (a Word TOC field; Word refreshes it on open), How to use
    Visual reference: figures from the source paper
    1  Proposed pathway hierarchy (map, tree table, topology)
    2  Proposed reactions (a chain diagram per subpathway, then one table per reaction)
    3  Placement and reorganisation of existing content
    4  Topology checks and design logic (event class and disease, resource
       comparison, chain continuity, design principles)
    5  Proposed physical entities
    6  Literature (verified against PubMed before rendering)
    7  How the proposal was built: the rounds and the arguments
    8  Internal review results
    9  Open questions for the curator, with how to apply each option
    Appendix: applying decisions and loading the staging file into WebBench

Usage
    python3 build_pathway_proposal.py proposal_spec.json -o "Proposal.docx"
    python3 build_pathway_proposal.py proposal_spec.json --validate
    python3 build_pathway_proposal.py proposal_spec.json --skip-ref-check   # offline only

Like build_update_doc.py, it refuses to render when a reference fails the PubMed
five-field check, and it links an ST_ID only when reactome.org serves it.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from typing import Any, Dict, List, Optional, Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
# Shared helpers (DOCX utilities, reaction diagrams, PubMed verification) live in the
# sibling /curation-update-from-paper skill, so both skills render the same way.
SHARED = os.path.join(os.path.dirname(HERE), "curation-update-from-paper")
for _p in (HERE, SHARED):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from docx import Document  # noqa: E402
from docx.enum.section import WD_ORIENT  # noqa: E402
from docx.enum.table import WD_TABLE_ALIGNMENT  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK  # noqa: E402
from docx.shared import Cm, Pt, RGBColor  # noqa: E402

import build_update_doc as bud  # noqa: E402

try:
    import reaction_graphic  # noqa: E402
except Exception:  # matplotlib missing: tables only
    reaction_graphic = None
try:
    import pathway_graphics  # noqa: E402
except Exception:
    pathway_graphics = None

import verify_references  # noqa: E402

NAVY = "1F3864"
TEAL = RGBColor(0x1F, 0x7A, 0x8C)
H3_BLUE = RGBColor(0x2E, 0x5F, 0x8A)
GREY = RGBColor(0x59, 0x59, 0x59)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LABEL_FILL = "F2F2F2"
PRIORITY_FILL = {"HIGH": "FCE4E4", "MEDIUM": "FEF3E2", "LOW": "EBF5E1", "INFO": "EAF1FB"}
PRIORITY_TEXT = {"HIGH": RGBColor(0xC0, 0x00, 0x00), "MEDIUM": RGBColor(0xB3, 0x6B, 0x00),
                 "LOW": RGBColor(0x38, 0x76, 0x1D), "INFO": RGBColor(0x2E, 0x5F, 0x8A)}
PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3}
STATUS_FILL = {"NEW": "E2EFD9", "SHARED": "DEEAF6", "EXISTING": "F2F2F2", "REUSE": "DEEAF6",
               "ADOPTED": "E2EFD9", "CORRECTED": "FEF3E2", "REJECTED": "FCE4E4",
               "OPEN": "FCE4E4", "RESOLVED": "E2EFD9", "DEFERRED": "F2F2F2"}
PUBMED = "https://pubmed.ncbi.nlm.nih.gov/"


# ── small helpers ───────────────────────────────────────────────────────────
def as_list(v):
    return bud.as_list(v)


def txt(v) -> str:
    return bud.as_text(v)


def banner(doc, text: str, fill: str = NAVY, toc: bool = True):
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    c = t.rows[0].cells[0]
    bud.set_column_widths(t, [bud.content_width(doc)])
    bud.set_cell_shading(c, fill)
    p = c.paragraphs[0]
    if toc:
        p.style = doc.styles["Heading 1"]
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(13)
    r.font.color.rgb = WHITE
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(3)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return t


def h2(doc, text):
    p = doc.add_heading(text, level=2)
    for r in p.runs:
        r.font.color.rgb = TEAL
        r.font.size = Pt(13)
    return p


def h3(doc, text):
    p = doc.add_heading(text, level=3)
    for r in p.runs:
        r.font.color.rgb = H3_BLUE
        r.font.size = Pt(12)
    return p


def para(doc, text, size=10.5, italic=False, color=None, bold=False, space_after=6):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.italic = italic
    r.bold = bold
    if color is not None:
        r.font.color.rgb = color
    p.paragraph_format.space_after = Pt(space_after)
    return p


def note(doc, text):
    return para(doc, text, size=9.5, italic=True, color=GREY)


def table(doc, headers: Sequence[str], widths_cm: Optional[Sequence[float]] = None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]
        bud.set_cell_shading(c, NAVY)
        p = c.paragraphs[0]
        r = p.add_run(h)
        r.bold = True
        r.font.size = Pt(9.5)
        r.font.color.rgb = WHITE
    bud.repeat_header_row(t.rows[0])
    if widths_cm:
        avail = bud.content_width(doc)
        total = float(sum(widths_cm))
        widths_cm = [w * avail / total for w in widths_cm]
    t._pp_widths = list(widths_cm) if widths_cm else None
    if widths_cm:
        bud.set_column_widths(t, widths_cm)
    return t


def row(t, values: Sequence[Any], fills: Optional[Dict[int, str]] = None, size=9.5,
        bold_cols=()):
    cells = t.add_row().cells
    for i, v in enumerate(values):
        p = cells[i].paragraphs[0]
        if callable(v):
            v(p)
        else:
            r = p.add_run(txt(v))
            r.font.size = Pt(size)
            if i in bold_cols:
                r.bold = True
        if fills and i in fills and fills[i]:
            bud.set_cell_shading(cells[i], fills[i])
    widths = getattr(t, "_pp_widths", None)
    if widths:
        for i, w in enumerate(widths):
            if i < len(cells):
                cells[i].width = Cm(w)
    return cells


def add_reference_lines(container, refs, size=9):
    """One line per reference: short cite, PMID and DOI links, system, then the verbatim quote."""
    first = True
    for r in as_list(refs):
        p = container.paragraphs[0] if (first and hasattr(container, "paragraphs") and not container.paragraphs[0].text) else container.add_paragraph()
        first = False
        p.paragraph_format.space_after = Pt(3)
        rr = p.add_run(txt(r.get("short")) + "  ")
        rr.bold = True
        rr.font.size = Pt(size)
        if r.get("pmid"):
            bud.add_hyperlink(p, PUBMED + str(r["pmid"]) + "/", "PMID:" + str(r["pmid"]), size=Pt(size))
        if r.get("doi"):
            p.add_run("  ").font.size = Pt(size)
            bud.add_hyperlink(p, "https://doi.org/" + r["doi"], "doi:" + r["doi"], size=Pt(size))
        if r.get("system"):
            rs = p.add_run("  (" + txt(r["system"]) + ")")
            rs.font.size = Pt(size - 0.5)
            rs.font.color.rgb = GREY
        if r.get("quote"):
            q = container.add_paragraph()
            q.paragraph_format.left_indent = Cm(0.4)
            q.paragraph_format.space_after = Pt(4)
            rq = q.add_run("“" + txt(r["quote"]) + "”")
            rq.italic = True
            rq.font.size = Pt(size - 0.5)
            if r.get("quote_source") and r["quote_source"] != "abstract":
                rs = q.add_run("  [" + txt(r["quote_source"]) + "]")
                rs.font.size = Pt(size - 1)
                rs.font.color.rgb = GREY


def chip(status: str):
    s = (status or "").upper()

    def _w(p):
        r = p.add_run(s)
        r.bold = True
        r.font.size = Pt(8.5)
    return _w, STATUS_FILL.get(s)


def prio_cell(priority: str):
    pr = (priority or "INFO").upper()

    def _w(p):
        r = p.add_run(pr)
        r.bold = True
        r.font.size = Pt(9)
        r.font.color.rgb = PRIORITY_TEXT.get(pr, GREY)
    return _w, PRIORITY_FILL.get(pr)


def st_id_writer(st_id, released):
    def _w(p):
        if st_id:
            bud.add_event_reference(p, st_id, released, size=Pt(9))
        else:
            r = p.add_run("—")
            r.font.size = Pt(9)
    return _w


def pmid_writer(pmid):
    def _w(p):
        if pmid:
            bud.add_hyperlink(p, PUBMED + str(pmid) + "/", "PMID:" + str(pmid), size=Pt(9))
        else:
            r = p.add_run("no PMID")
            r.italic = True
            r.font.size = Pt(9)
    return _w


def kv_rows(doc, pairs):
    for k, v in pairs:
        t = doc.add_table(rows=1, cols=2)
        t.style = "Table Grid"
        a, b = t.rows[0].cells
        bud.set_cell_shading(a, LABEL_FILL)
        ra = a.paragraphs[0].add_run(k)
        ra.bold = True
        ra.font.size = Pt(10)
        if callable(v):
            v(b.paragraphs[0])
        else:
            rb = b.paragraphs[0].add_run(txt(v))
            rb.font.size = Pt(10)
        bud.set_column_widths(t, [4.4, bud.content_width(doc) - 4.4])


def new_section(doc, landscape: bool):
    from docx.enum.section import WD_SECTION
    sec = doc.add_section(WD_SECTION.NEW_PAGE)
    bud.set_orientation(sec, landscape)
    return sec


# ── validation ──────────────────────────────────────────────────────────────
def validate(spec: Dict[str, Any]) -> List[str]:
    errs = []
    for k in ("title", "proposed_pathway", "source_paper", "hierarchy", "events", "references",
              "construction_log", "final_review", "open_questions"):
        if k not in spec:
            errs.append(f"missing top-level key: {k}")
    labels = set()
    for i, e in enumerate(as_list(spec.get("events"))):
        lab = e.get("label") or f"events[{i}]"
        if lab in labels:
            errs.append(f"{lab}: duplicate event label")
        labels.add(lab)
        if e.get("status", "NEW").upper() in ("NEW", "INFERRED", "INFERENCE_SOURCE"):
            for k in ("name", "type", "compartment", "species", "summation", "subpathway"):
                if bud.is_blank(e.get(k)):
                    errs.append(f"{lab}: NEW event missing {k}")
            if not as_list(e.get("pmids")) and not e.get("primary_ref"):
                errs.append(f"{lab}: NEW event has no primary reference")
            if e.get("evidence_sentence") and not e.get("evidence_citation"):
                errs.append(f"{lab}: evidence_sentence without evidence_citation")
            if e.get("evidence_sentence") and "evidence_page" not in e:
                errs.append(f"{lab}: evidence_page key must be present (null if not located)")
        for p in as_list(e.get("pmids")):
            if not bud.pmid_source_ok(p.get("pmid_source")) or not p.get("pmid_source"):
                errs.append(f"{lab}: PMID {p.get('pmid')} has no valid pmid_source")
    # The logic must be written out, not left to the tables (curator feedback, 2026-11-06).
    for k in ("summary", "hierarchy_intro", "topology_intro", "rationale"):
        if not as_list(spec.get(k)):
            errs.append(f"missing narrative: {k}")
    for sub in as_list(spec.get("subpathways")):
        for k in ("topology", "flow", "summation"):
            if bud.is_blank(sub.get(k)):
                errs.append(f"subpathway {sub.get('key')}: missing {k}")
    for e in as_list(spec.get("events")):
        if e.get("status", "NEW").upper() == "NEW":
            for k in ("rationale", "inputs", "outputs"):
                if bud.is_blank(e.get(k)):
                    errs.append(f"{e.get('label')}: NEW event missing {k}")
    def _need_class(label, x):
        if not (x.get("class_assessment") or {}).get("chosen"):
            errs.append(f"{label}: missing class_assessment (chosen class, why, classes ruled out)")
        if bud.is_blank(x.get("disease")):
            errs.append(f"{label}: missing disease statement")
    _need_class("proposed_pathway", spec.get("proposed_pathway") or {})
    for sub in as_list(spec.get("subpathways")):
        _need_class(f"subpathway {sub.get('key')}", sub)
    for e in as_list(spec.get("events")):
        if e.get("status", "NEW").upper() in ("NEW", "INFERRED", "INFERENCE_SOURCE"):
            _need_class(str(e.get("label")), e)
    for q in as_list(spec.get("open_questions")):
        if not as_list(q.get("options")):
            errs.append(f"{q.get('id')}: open question has no options (each needs a choice and how to apply it)")
    ref_pmids = {str(r.get("pmid")) for r in as_list(spec.get("references")) if r.get("pmid")}
    for e in as_list(spec.get("events")):
        for p in as_list(e.get("pmids")):
            if str(p.get("pmid")) not in ref_pmids:
                errs.append(f"{e.get('label')}: PMID {p.get('pmid')} is not in references")
    for r in as_list(spec.get("references")):
        if r.get("pmid") and not bud.pmid_source_ok(r.get("pmid_source")):
            errs.append(f"reference PMID {r.get('pmid')}: invalid pmid_source")
    # Critical decisions must be a subset of HIGH open questions
    highs = {q.get("id") for q in as_list(spec.get("open_questions"))
             if str(q.get("priority", "")).upper() == "HIGH"}
    for d in as_list((spec.get("executive") or {}).get("decision_ids")):
        if d not in highs:
            errs.append(f"executive decision {d} is not a HIGH open question")
    return errs


# ── sections ────────────────────────────────────────────────────────────────
def title_block(doc, spec, ref_status, released):
    banner(doc, "REACTOME PATHWAY PROPOSAL", toc=False)
    pp = spec["proposed_pathway"]
    src = spec["source_paper"]

    def src_w(p):
        r = p.add_run(txt(src.get("citation")) + " ")
        r.font.size = Pt(10)
        if src.get("doi"):
            bud.add_hyperlink(p, "https://doi.org/" + src["doi"], "doi:" + src["doi"], size=Pt(10))

    def anchors_w(p):
        cell = p._parent
        for i, a in enumerate(as_list(spec.get("anchor_nodes"))):
            q = p if i == 0 else cell.add_paragraph()
            q.paragraph_format.space_after = Pt(1)
            q.add_run("•  ").font.size = Pt(10)
            bud.add_event_reference(q, a.get("st_id", ""), released, size=Pt(10))
            r = q.add_run("  " + txt(a.get("name")))
            r.font.size = Pt(10)

    m = spec.get("meta") or {}
    kv_rows(doc, [
        ("Proposed pathway", pp.get("name")),
        ("Proposed parent(s)", "; ".join(f"{x.get('name')} ({x.get('st_id')})" for x in as_list(pp.get("parents")))),
        ("Source paper", src_w),
        ("Curator's anchor nodes", anchors_w),
        ("Prepared", f"{m.get('date', '')} · {m.get('prepared_by', '')}"),
        ("Release", m.get("release") or "not assigned"),
        ("Live database checks", m.get("live_checks", "not run")),
        ("Literature check", ref_status),
        ("Review rounds", m.get("review_rounds", "")),
        ("Staging file", m.get("staging_file", "")),
    ])
    doc.add_paragraph()


def executive(doc, spec):
    banner(doc, "Executive Summary")
    ex = spec.get("executive") or {}
    h2(doc, "At a Glance")
    t = table(doc, ["Item", "Count"], [10, 3])
    for k, v in (ex.get("counts") or {}).items():
        row(t, [k, v])
    doc.add_paragraph()

    h2(doc, "Primary Curator Decisions")
    qs = {q.get("id"): q for q in as_list(spec.get("open_questions"))}
    ids = as_list(ex.get("decision_ids"))
    if not ids:
        para(doc, "No HIGH-priority decisions are outstanding.")
    else:
        note(doc, "The HIGH-priority items from Section 9, which must be settled before any instances are built.")
        t = table(doc, ["#", "Decision", "Affects", "Why it matters"], [1.2, 7.3, 3.0, 6.0])
        for d in ids:
            q = qs.get(d, {})
            row(t, [d, q.get("question"), q.get("affects"), q.get("why")], fills={0: PRIORITY_FILL["HIGH"]})
    doc.add_paragraph()

    h2(doc, "Assessment After Internal-Review Testing")
    fr = spec.get("final_review") or {}
    choice = (fr.get("recommendation") or "").lower()
    opts = [("ready", "Ready to build in the Curator Tool"),
            ("decisions", "Ready once the curator settles the decisions above"),
            ("revision", "Needs significant revision before building")]
    t = doc.add_table(rows=0, cols=2)
    for key, label in opts:
        c = t.add_row().cells
        c[0].paragraphs[0].add_run("☒" if key in choice else "☐").font.size = Pt(12)
        r = c[1].paragraphs[0].add_run(label)
        r.font.size = Pt(10.5)
        r.bold = key in choice
    bud.set_column_widths(t, [1.0, 16.5])
    if fr.get("summary"):
        para(doc, fr["summary"], size=10)

    h3(doc, "Summary")
    for ptxt in as_list(spec.get("summary")):
        para(doc, ptxt)


def how_to_use_section(doc, spec):
    banner(doc, "How to Use This Proposal")
    para(doc, "This proposal is a draft for you to decide on, not a finished curation. Nothing has "
              "been written to gk_central. The new instances it proposes are in the companion staging "
              "file, and you load them into WebBench only after you have made the decisions below.")
    steps = as_list(spec.get("how_to_use")) or [
        "Read the Executive Summary and the Primary Curator Decisions, then use the Contents to go to Section 1 (the hierarchy) and Section 2 (the proposed reactions).",
        "Work through Section 9. Each question lists its options and exactly what to change for each one. Record your choice in the 'Your decision' line.",
        "Apply your decisions to the staging file, or ask Claude to apply them and regenerate this document.",
        "Convert the staging file to the WebBench file and load it.",
        "In the Curator Tool, make the changes to existing events listed in Section 3, then save or commit as usual.",
    ]
    for i, st in enumerate(steps, 1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.6)
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(f"{i}.  ")
        r.bold = True
        r.font.size = Pt(10.5)
        p.add_run(txt(st)).font.size = Pt(10.5)
    note(doc, "The Appendix gives the exact commands for steps 3 and 4.")


def hierarchy_section(doc, spec, released):
    banner(doc, "Section 1 — Proposed Pathway Hierarchy")
    for ptxt in as_list(spec.get("hierarchy_intro")):
        para(doc, ptxt)
    mp = spec.get("_figs", {}).get("_map")
    if mp:
        bud.add_scaled_picture(doc, mp, bud.content_width(doc), 13.5)
        note(doc, "Hierarchy map: the proposed pathway, its subpathways and their members. "
                  "The tree table below gives the same structure with ST_IDs and reasons.")
    note(doc, "NEW = proposed instance (in the staging file). SHARED = existing gk_central event "
              "added as a second child; it is linked, not copied or edited.")
    t = table(doc, ["Pathway hierarchy", "Type", "Status", "ST_ID", "GO biological process / note"],
              [8.6, 1.9, 1.8, 2.4, 3.8])
    LEVEL_FILL = {0: "C9D7EE", 1: "E4ECF7"}
    TYPE_MARK = {"Pathway": "▣ Pathway", "Reaction": "● Reaction", "BlackBoxEvent": "◐ Black box"}

    def walk(nodes, prefix, depth):
        nodes = as_list(nodes)
        for i, n in enumerate(nodes):
            last = i == len(nodes) - 1
            branch = "" if depth == 0 else ("└─ " if last else "├─ ")
            kind = n.get("kind") or ("Pathway" if (n.get("children") or depth < 2 or n.get("note") == "Pathway") else "Reaction")
            status = (n.get("status") or "NEW").upper()

            def name_w(p, n=n, branch=branch, prefix=prefix, depth=depth, status=status):
                if prefix or branch:
                    rp = p.add_run(prefix + branch)
                    rp.font.name = "Menlo"
                    rp.font.size = Pt(8.5)
                    rp.font.color.rgb = GREY
                rn = p.add_run(txt(n.get("name")))
                rn.font.size = Pt(10 if depth == 0 else 9.5 if depth == 1 else 9)
                rn.bold = depth < 2
                if status == "NEW" and depth >= 2:
                    rn.font.color.rgb = RGBColor(0x38, 0x76, 0x1D)
            cw, cf = chip(status if status != "SHARED" else "SHARED")
            note_txt = n.get("go_bp") if depth < 2 else (n.get("note_text") or "")
            if depth < 2 and n.get("note") and depth == 0:
                note_txt = f"{n.get('go_bp') or '—'}\n{n['note']}"
            cells = row(t, [name_w, TYPE_MARK.get(kind, kind), cw, st_id_writer(n.get("st_id"), released),
                            note_txt or "—"], fills={2: cf}, size=8.5)
            if depth in LEVEL_FILL:
                for j in (0, 1, 3, 4):
                    bud.set_cell_shading(cells[j], LEVEL_FILL[depth])
            walk(n.get("children"), prefix + ("" if depth == 0 else ("   " if last else "│  ")), depth + 1)
    walk(spec.get("hierarchy"), "", 0)
    doc.add_paragraph()
    note(doc, "▣ pathway (a linked existing pathway brings all its reactions with it)   ● reaction   "
              "Green names: new reactions proposed here.   Blue-shaded rows: the new pathway and its subpathways.")
    subs = [x for x in as_list(spec.get("subpathways")) if x.get("topology")]
    if subs or spec.get("topology_intro"):
        h2(doc, "Pathway Topology")
        note(doc, "How the pathway is organised, and how the events in each subpathway connect.")
        for ptxt in as_list(spec.get("topology_intro")):
            para(doc, ptxt)
        for i, sub in enumerate(subs, 1):
            h3(doc, f"{i}. {txt(sub.get('name'))}")
            for ptxt in as_list(sub.get("topology")):
                para(doc, ptxt)


def checks_section(doc, spec):
    banner(doc, "Section 4 — Topology Checks and Design Logic")
    note(doc, "The checks behind the hierarchy: event classes and disease status, what other pathway resources show, where the event chains are continuous, and the rules applied throughout.")
    h2(doc, "Event Class and Disease Assessment")
    para(doc, "Every new pathway and reaction was assessed against each event class in the data model "
              "(reaction-like events: Reaction, BlackBoxEvent, Polymerisation, Depolymerisation, "
              "FailedReaction, CellDevelopmentStep; pathways: Pathway, TopLevelPathway, CellLineagePath), "
              "and for disease status. Disease status follows the biology represented, such as an altered "
              "or failed function or a disease-state participant, not the presence of a drug.")
    t = table(doc, ["Event", "Class", "Why this class", "Classes ruled out", "Disease event"], [3.6, 1.8, 4.2, 5.2, 3.0])
    items = [(spec["proposed_pathway"].get("name"), spec["proposed_pathway"])]
    items += [(x.get("name"), x) for x in as_list(spec.get("subpathways"))]
    items += [(f"{e.get('label')}  {e.get('name')}", e) for e in as_list(spec.get("events"))
              if e.get("status", "NEW").upper() in ("NEW", "INFERRED", "INFERENCE_SOURCE")]
    for name, x in items:
        ca = x.get("class_assessment") or {}
        ro = "\n".join(f"{k}: {v}" for k, v in (ca.get("ruled_out") or {}).items())
        dis = txt(x.get("disease"))
        row(t, [name, ca.get("chosen"), ca.get("why"), ro, dis],
            fills={4: "E2EFD9" if dis.startswith("No") else "FCE4E4"}, size=8)
    doc.add_paragraph()
    comp = spec.get("comparison") or {}
    if as_list(comp.get("themes")):
        h2(doc, "Comparison with Other Pathway Resources")
        for ptxt in as_list(comp.get("intro")):
            para(doc, ptxt)
        cfill = {"LINK_PATHWAY": "E2EFD9", "CLOSES_CHAIN_GAP": "E2EFD9", "NEW_CANDIDATE": "FEF3E2",
                 "COVERED_ELSEWHERE": "F2F2F2", "OUT_OF_SCOPE": "F2F2F2"}
        t = table(doc, ["Theme (genes)", "Shown by", "In Reactome", "Result", "What the proposal does"],
                  [4.2, 2.8, 4.0, 2.3, 4.2])
        for th in as_list(comp["themes"]):
            cls = txt(th.get("class"))
            row(t, [f"{txt(th.get('theme'))} ({', '.join(as_list(th.get('genes'))[:6])})",
                    ", ".join(as_list(th.get("shown_by"))), th.get("reactome"), cls.replace("_", " "),
                    th.get("outcome") or th.get("action")], fills={3: cfill.get(cls)}, size=8.5)
        doc.add_paragraph()
        if comp.get("notice"):
            note(doc, comp["notice"])
    gaps = as_list(spec.get("chain_gaps"))
    if gaps:
        h2(doc, "Chain Continuity and Inference Check")
        for ptxt in as_list(spec.get("chain_intro")):
            para(doc, ptxt)
        fill = {"FILLED": "E2EFD9", "NEEDS": "FEF3E2", "INFERENCE": "FCE4E4", "NOT_A_BREAK": "F2F2F2"}
        t = table(doc, ["#", "Subpathway", "Step", "Result", "Evidence from gk_central"], [1.0, 2.4, 4.4, 3.2, 6.5])
        for g in gaps:
            cls = txt(g.get("class"))
            f = next((v for k, v in fill.items() if cls.upper().startswith(k)), None)
            row(t, [g.get("id"), g.get("subpathway"), g.get("step"), cls.replace("_", " "), g.get("evidence")],
                fills={3: f}, size=8.5)
        doc.add_paragraph()
    if spec.get("rationale"):
        h2(doc, "Design Principles")
        note(doc, "The rules applied to every part of the hierarchy.")
        for ptxt in as_list(spec["rationale"]):
            para(doc, ptxt)


def figures_section(doc, spec):
    figs = as_list(spec.get("source_figures"))
    if figs:
        banner(doc, "Visual Reference — Figures from the Source Paper")
        note(doc, "Figures from the source paper that the event extraction used. Each caption says which "
                  "subpathways and events the panels support. Reproduced for internal curation review only.")
        for f in figs:
            path = f.get("file")
            if path and not os.path.isabs(path):
                path = os.path.join(spec.get("_base_dir", ""), path)
            if path and os.path.exists(path):
                bud.add_scaled_picture(doc, path, bud.content_width(doc), 15.5)
            p = doc.add_paragraph()
            r = p.add_run(txt(f.get("label")) + " ")
            r.bold = True
            r.font.size = Pt(9.5)
            p.add_run(txt(f.get("caption"))).font.size = Pt(9.5)
            if f.get("supports"):
                p2 = doc.add_paragraph()
                r2 = p2.add_run("Used for: ")
                r2.bold = True
                r2.font.size = Pt(9)
                p2.add_run(txt(f["supports"])).font.size = Pt(9)
            if f.get("credit"):
                note(doc, f["credit"])


def toc_section(doc):
    banner(doc, "Contents", toc=False)
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    p = doc.add_paragraph()
    run = p.add_run()
    b = OxmlElement("w:fldChar"); b.set(qn("w:fldCharType"), "begin")
    i = OxmlElement("w:instrText"); i.set(qn("xml:space"), "preserve"); i.text = 'TOC \\o "1-2" \\h \\z \\u'
    sep = OxmlElement("w:fldChar"); sep.set(qn("w:fldCharType"), "separate")
    ph = OxmlElement("w:t"); ph.text = "Open in Word and choose Update Field (or press F9) to build the table of contents."
    e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), "end")
    for el in (b, i, sep, ph, e):
        run._r.append(el)
    # ask Word to refresh fields (the TOC page numbers) when the file opens
    settings = doc.settings.element
    upd = settings.find(qn("w:updateFields"))
    if upd is None:
        upd = OxmlElement("w:updateFields"); settings.append(upd)
    upd.set(qn("w:val"), "true")
    note(doc, "Sections 1 and 2 give the hierarchy and the proposed reactions; Section 3 places existing content; "
              "Section 4 holds the checks and design logic; Sections 5–8 hold entities, literature, the agents' "
              "arguments and the internal review; Section 9 lists every open question with how to apply each choice.")


def placement_section(doc, spec, released):
    banner(doc, "Section 3 — Placement and Reorganisation of Existing Content")
    for ptxt in as_list(spec.get("placement_intro")):
        para(doc, ptxt)
    note(doc, "The staging file creates only new instances. Every move or removal below is "
              "for the curator to make by hand in the Curator Tool.")
    t = table(doc, ["Node", "Where it is now", "Reuse level", "Proposed role", "Action", "Reasoning"],
              [3.6, 3.2, 2.0, 2.8, 2.8, 4.1])
    for a in as_list(spec.get("placement")):
        def nw(p, a=a):
            bud.add_event_reference(p, a.get("st_id", ""), released, size=Pt(9))
            r = p.add_run("\n" + txt(a.get("name")))
            r.font.size = Pt(9)
        row(t, [nw, a.get("current"), a.get("level", ""), a.get("role"), a.get("action"), a.get("reasoning")])
    doc.add_paragraph()


def event_card(doc, e, idx, released, figs, width_cm):
    """One reaction: heading, diagram, why it is proposed, then a single table that carries
    every mandatory and required slot, the summation, and the literature with links and quotes."""
    lab = e.get("label", f"E{idx}")
    status = e.get("status", "NEW").upper()
    h3(doc, f"{lab}  {txt(e.get('name'))}")
    meta = doc.add_paragraph()
    tag = {"NEW": "NEW", "REUSE": "SHARED (existing)", "INFERENCE_SOURCE": "NEW, non-human source reaction for inference",
           "INFERRED": "NEW, human reaction inferred from another species"}.get(status, status)
    r2 = meta.add_run(tag)
    r2.bold = True
    r2.font.size = Pt(9.5)
    if e.get("st_id"):
        meta.add_run("  ")
        bud.add_event_reference(meta, e["st_id"], released, size=Pt(9.5))
    png = figs.get(lab)
    if png:
        bud.add_scaled_picture(doc, png, width_cm, 9.5)
    if e.get("rationale"):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(4)
        rr = p.add_run("Why this reaction is proposed. ")
        rr.bold = True
        rr.font.size = Pt(10)
        p.add_run(txt(e["rationale"])).font.size = Pt(10)

    lines = lambda v: "\n".join(as_list(v)) if as_list(v) else "—"
    rows = [("Name", e.get("name")),
            ("Class", (e.get("type") or "") + (" — " + txt((e.get("class_assessment") or {}).get("why"))
                                               if (e.get("class_assessment") or {}).get("why") else "")),
            ("Disease event", e.get("disease") or "—"),
            ("Species", e.get("species")),
            ("Compartment", e.get("compartment")),
            ("Cell type", e.get("cell_type") or "—"),
            ("Inputs", lines(e.get("inputs"))),
            ("Outputs", lines(e.get("outputs"))),
            ("Catalyst", e.get("catalyst") or "none (binding or transport)"),
            ("GO molecular function", e.get("go_mf") or "—"),
            ("Regulators", lines(e.get("regulators"))),
            ("Preceding event", e.get("preceding_event") or "—"),
            ("Following event", e.get("following_event") or "—")]
    if e.get("inferred_from") or status == "INFERRED":
        rows.append(("Inferred from", e.get("inferred_from") or "—"))
    if e.get("evidence_type_eco") or status in ("INFERRED",):
        rows.append(("Evidence type (ECO)", e.get("evidence_type_eco") or "—"))
    rows += [("Evidence basis", e.get("evidence_type") or "—"),
             ("Human evidence", e.get("human_evidence") or "—"),
             ("Literature reference", "@primary"),
             ("Summation", e.get("summation") or "—"),
             ("Additional references for the summation", "@summation")]
    t = doc.add_table(rows=0, cols=2)
    t.style = "Table Grid"
    for k, v in rows:
        c = t.add_row().cells
        bud.set_cell_shading(c[0], LABEL_FILL)
        rk = c[0].paragraphs[0].add_run(k)
        rk.bold = True
        rk.font.size = Pt(9)
        if v == "@primary":
            prim = e.get("primary_ref") or (as_list(e.get("pmids"))[:1] or [None])[0]
            if prim:
                add_reference_lines(c[1], [prim])
            else:
                c[1].paragraphs[0].add_run("—").font.size = Pt(9)
        elif v == "@summation":
            extra = as_list(e.get("summation_refs"))
            if extra:
                add_reference_lines(c[1], extra)
            else:
                rr = c[1].paragraphs[0].add_run("None: the summation cites only the reaction's reference.")
                rr.italic = True
                rr.font.size = Pt(9)
        else:
            c[1].paragraphs[0].add_run(txt(v)).font.size = Pt(9 if k != "Summation" else 9.5)
    bud.set_column_widths(t, [4.0, width_cm - 4.0])
    for f in as_list(e.get("flags")):
        p = doc.add_paragraph()
        rf = p.add_run("⚑ " + txt(f))
        rf.font.size = Pt(9)
        rf.font.color.rgb = PRIORITY_TEXT["MEDIUM"]


def events_section(doc, spec, released, figs):
    banner(doc, "Section 2 — Proposed Reactions")
    for ptxt in as_list(spec.get("events_intro")):
        para(doc, ptxt)
    note(doc, "Grouped by subpathway. Each new event shows a diagram: participants with an ST_ID "
              "are drawn solid and are reused; dashed participants tagged NEW are proposed.")
    width = bud.content_width(doc)
    events = as_list(spec.get("events"))
    for sub in as_list(spec.get("subpathways")):
        h2(doc, txt(sub.get("name")))
        bits = [f"Parent: {sub.get('parent', '')}"]
        if sub.get("go_bp"):
            bits.append(f"GO BP: {sub['go_bp']}")
        note(doc, " · ".join(bits))
        chain_png = spec.get("_figs", {}).get("_chain_" + str(sub.get("key")))
        if chain_png:
            bud.add_scaled_picture(doc, chain_png, width, 11.0)
        elif sub.get("flow"):
            p = doc.add_paragraph()
            rr = p.add_run("How the events connect. ")
            rr.bold = True
            rr.font.size = Pt(10)
            p.add_run(txt(sub["flow"])).font.size = Pt(10)
        if sub.get("summation"):
            p = doc.add_paragraph()
            rr = p.add_run("Draft summation. ")
            rr.bold = True
            rr.font.size = Pt(10)
            p.add_run(txt(sub["summation"])).font.size = Pt(10)
        if as_list(sub.get("references")):
            p = doc.add_paragraph()
            rr = p.add_run("References for this summation")
            rr.bold = True
            rr.font.size = Pt(9.5)
            box = doc.add_table(rows=1, cols=1)
            box.style = "Table Grid"
            add_reference_lines(box.rows[0].cells[0], sub["references"])
            bud.set_column_widths(box, [width])
            doc.add_paragraph()
        if sub.get("figure"):
            note(doc, "Source paper figure: " + txt(sub["figure"]))
        mine = [e for e in events if e.get("subpathway") == sub.get("key")]
        shared = [e for e in mine if e.get("status", "NEW").upper() == "REUSE"]
        if shared:
            t = table(doc, ["Shared existing event", "ST_ID", "Why it is included"], [9.0, 3.0, width - 12.0])
            for e in shared:
                row(t, [e.get("name"), st_id_writer(e.get("st_id"), released), e.get("reason") or ""])
            doc.add_paragraph()
        for i, e in enumerate([e for e in mine if e.get("status", "NEW").upper() in ("NEW", "INFERRED", "INFERENCE_SOURCE")], 1):
            event_card(doc, e, i, released, figs, width)


def entities_section(doc, spec, released):
    banner(doc, "Section 5 — Proposed Physical Entities")
    for ptxt in as_list(spec.get("entities_intro")):
        para(doc, ptxt)
    note(doc, "RESOLVED: one match in gk_central. RESOLVED (branch usage): several matches, one "
              "already used in the branch. AMBIGUOUS: several, none in use. JUDGEMENT: identity "
              "is clear but the fit is the curator's call.")
    t = table(doc, ["Entity", "Class", "Compartment", "Status", "Reused instance / components",
                    "Resolution"], [5.2, 2.6, 2.8, 1.6, 6.4, 5.0])
    for x in as_list(spec.get("entities")):
        cw, cf = chip(x.get("status", "NEW"))

        def reuse_w(p, x=x):
            if x.get("st_id"):
                bud.add_event_reference(p, x["st_id"], released, size=Pt(9))
                if x.get("db_id"):
                    p.add_run(f" (dbId {x['db_id']})").font.size = Pt(8.5)
            if x.get("components"):
                r = p.add_run(("\n" if x.get("st_id") else "") + txt(x["components"]))
                r.font.size = Pt(9)
            if not x.get("st_id") and not x.get("components"):
                p.add_run("—").font.size = Pt(9)
        row(t, [x.get("name"), x.get("class"), x.get("compartment"), cw, reuse_w,
                x.get("resolution") or ""], fills={3: cf})
    doc.add_paragraph()


def literature_section(doc, spec):
    banner(doc, "Section 6 — Literature")
    for ptxt in as_list(spec.get("literature_intro")):
        para(doc, ptxt)
    note(doc, "Every PMID was resolved through NCBI E-utilities and matched on first author, "
              "initials, year, journal and title before this document was rendered.")
    t = table(doc, ["#", "Reference", "PMID", "Experimental system", "Supports"], [0.8, 8.6, 2.2, 3.0, 2.9])
    for i, r in enumerate(as_list(spec.get("references")), 1):
        row(t, [r.get("n", i), r.get("citation"), pmid_writer(r.get("pmid")), r.get("system") or "",
                ", ".join(as_list(r.get("supports")))])
    doc.add_paragraph()
    exc = as_list(spec.get("excluded_references"))
    if exc:
        h2(doc, "Papers Considered and Not Used")
        t = table(doc, ["Reference", "PMID", "Why not used"], [8.5, 2.2, 6.8])
        for r in exc:
            row(t, [r.get("citation"), pmid_writer(r.get("pmid")), r.get("reason")])
        doc.add_paragraph()


def log_section(doc, spec):
    banner(doc, "Section 7 — How the Proposal Was Built")
    log = spec.get("construction_log") or {}
    note(doc, "Separate agents extracted events from the paper, surveyed gk_central, searched "
              "for human primary literature, and tested the draft against the internal-review "
              "checks. Their disagreements and how each was settled are recorded below, so the "
              "curator can re-open any decision.")
    h2(doc, "Rounds")
    t = table(doc, ["Round", "Agents", "What happened"], [1.6, 5.0, 17.0])
    for r in as_list(log.get("rounds")):
        row(t, [r.get("round"), ", ".join(as_list(r.get("agents"))), r.get("label")])
    doc.add_paragraph()
    h2(doc, "Arguments and Resolutions")
    t = table(doc, ["#", "Round", "Topic", "Raised by", "Argument and evidence", "Counter-argument",
                    "Resolution", "Status"], [1.0, 1.3, 3.0, 2.2, 6.0, 4.6, 4.6, 1.9])
    for d in as_list(log.get("entries")):
        cw, cf = chip(d.get("status", ""))
        arg = txt(d.get("position"))
        if d.get("evidence"):
            arg += "\nEvidence: " + txt(d["evidence"])
        row(t, [d.get("id"), d.get("round"), d.get("topic"), d.get("raised_by"), arg,
                d.get("counter") or "—", d.get("resolution"), cw], fills={7: cf}, size=8.5)
    doc.add_paragraph()


def review_section(doc, spec):
    banner(doc, "Section 8 — Internal Review Results")
    fr = spec.get("final_review") or {}
    note(doc, "The draft was tested in each round against the /review-internal checks: "
              "literature validity, reaction connectivity and entity chains, required data-model "
              "slots, GO terms, summation construction and references, and naming conventions.")
    h2(doc, "Issue Count by Round")
    t = table(doc, ["Round", "HIGH", "MEDIUM", "LOW", "Resolved before next round"], [2.0, 2.0, 2.0, 2.0, 5.0])
    for r in as_list(fr.get("rounds")):
        row(t, [r.get("round"), r.get("HIGH", 0), r.get("MEDIUM", 0), r.get("LOW", 0), r.get("resolved", "")],
            fills={1: PRIORITY_FILL["HIGH"], 2: PRIORITY_FILL["MEDIUM"], 3: PRIORITY_FILL["LOW"]})
    doc.add_paragraph()
    h2(doc, "Issues Remaining for the Curator")
    rem = sorted(as_list(fr.get("issues")), key=lambda x: PRIORITY_ORDER.get(str(x.get("priority")).upper(), 9))
    if not rem:
        para(doc, "No issues remain open.")
    else:
        t = table(doc, ["Priority", "Check", "Location", "Issue", "Recommended action"], [1.8, 2.6, 2.6, 5.5, 5.0])
        for x in rem:
            pw, pf = prio_cell(x.get("priority"))
            row(t, [pw, x.get("check"), x.get("location"), x.get("issue"), x.get("action")], fills={0: pf})
    doc.add_paragraph()


def questions_section(doc, spec):
    banner(doc, "Section 9 — Open Questions for the Curator")
    qs = sorted(as_list(spec.get("open_questions")),
                key=lambda q: PRIORITY_ORDER.get(str(q.get("priority")).upper(), 9))
    for ptxt in as_list(spec.get("questions_intro")) or [
            "Each question lists its options and exactly what to change for each one. Settle the "
            "HIGH questions before loading anything into WebBench; the others can be settled while "
            "you build."]:
        para(doc, ptxt)
    for q in qs:
        pr = str(q.get("priority", "INFO")).upper()
        t = doc.add_table(rows=1, cols=3)
        t.style = "Table Grid"
        c = t.rows[0].cells
        bud.set_cell_shading(c[0], PRIORITY_FILL.get(pr, LABEL_FILL))
        r0 = c[0].paragraphs[0].add_run(f"{q.get('id')}\n{pr}")
        r0.bold = True
        r0.font.size = Pt(9.5)
        r0.font.color.rgb = PRIORITY_TEXT.get(pr, GREY)
        p1 = c[1].paragraphs[0]
        if q.get("tag"):
            rt = p1.add_run(f"{q['tag']}  ")
            rt.bold = True
            rt.font.size = Pt(9.5)
        p1.add_run(txt(q.get("question"))).font.size = Pt(9.5)
        if q.get("why"):
            rw = c[1].add_paragraph().add_run("Why it matters: " + txt(q["why"]))
            rw.italic = True
            rw.font.size = Pt(9)
            rw.font.color.rgb = GREY
        ra = c[2].paragraphs[0].add_run("Affects\n")
        ra.bold = True
        ra.font.size = Pt(8.5)
        c[2].paragraphs[0].add_run(txt(q.get("affects"))).font.size = Pt(8.5)
        for o in as_list(q.get("options")):
            oc = t.add_row().cells
            ro = oc[0].paragraphs[0].add_run("☐ " + txt(o.get("choice_id", "")))
            ro.font.size = Pt(9.5)
            rc = oc[1].paragraphs[0].add_run(txt(o.get("choice")))
            rc.bold = True
            rc.font.size = Pt(9.5)
            if o.get("recommended"):
                rr = oc[1].paragraphs[0].add_run("  (recommended)")
                rr.italic = True
                rr.font.size = Pt(9)
            rh = oc[2].paragraphs[0].add_run(txt(o.get("apply")))
            rh.font.size = Pt(8.5)
        last = t.add_row().cells
        last[0].merge(last[2])
        rd = last[0].paragraphs[0].add_run("Your decision: ______________________________________________")
        rd.font.size = Pt(9.5)
        rd.font.color.rgb = GREY
        bud.set_column_widths(t, [1.8, 9.3, bud.content_width(doc) - 11.1])
        doc.add_paragraph().paragraph_format.space_after = Pt(2)


def appendix(doc, spec):
    banner(doc, "Appendix — Applying Your Decisions and Loading into WebBench", fill="2E5F8A")
    st = spec.get("staging") or {}
    h2(doc, "Applying Your Decisions")
    para(doc, "Either way works:")
    for s_ in ["Ask Claude: run /curation-gap-fill and say, for example, 'apply decisions "
               "Q1=A, Q2=move, Q8=keep E5'. It edits the proposal source, regenerates this document "
               "and the staging file, and re-runs the checks.",
               "Or edit the staging file yourself, following the 'What to change' column of each "
               "question in Section 9. Every block in it starts with '### @key Class'; delete a "
               "block to drop an instance, and edit the '- slot: value' lines to change it."]:
        doc.add_paragraph(s_, style="List Bullet").runs[0].font.size = Pt(10)
    h2(doc, "Loading into WebBench")
    para(doc, "The companion markdown file holds every NEW instance in this proposal, one block "
              "per instance, with existing gk_central instances referenced by dbId. Convert it "
              "(the converter checks every class and slot first, and refuses a broken file):")
    p = doc.add_paragraph()
    r = p.add_run(f"python3 staging_from_md.py {st.get('md_file', '<proposal>_staging.md')}")
    r.font.name = "Menlo"
    r.font.size = Pt(9.5)
    for s in ["In WebBench, click file_upload (Load staged instances from a local file) and choose the JSON.",
              "Loading replaces your current staged changes. WebBench backs them up to the server "
              "first; recover them with Restore staged-changes backup.",
              "Review the loaded instances, set any slot marked for curator action, then save or commit as usual.",
              "Only new instances are staged. Existing events gain the new pathway as a second parent "
              "through its hasEvent; nothing existing is edited. Make the moves in Section 3 by hand."]:
        doc.add_paragraph(s, style="List Bullet").runs[0].font.size = Pt(10)
    if st.get("counts"):
        t = table(doc, ["Class", "New instances"], [8, 3])
        for k, v in st["counts"].items():
            row(t, [k, v])


# ── build ───────────────────────────────────────────────────────────────────
def build(spec, out, *, skip_ref=False, skip_link=False, graphics=True):
    if skip_ref:
        ref_status = "NOT verified against PubMed (offline render)"
    else:
        res = verify_references.verify_spec(spec)
        if res["errors"]:
            print(verify_references.format_report(res), file=sys.stderr)
            raise SystemExit("REFUSING TO RENDER: a reference does not match its PubMed record.")
        warn = [f for f in res["findings"] if f["severity"] != "ERROR"]
        ref_status = (f"{res['checked']} of {res['total']} references matched to PubMed on author, "
                      f"year, journal and title" + (f"; {len(warn)} warning(s)" if warn else ""))
    st_ids = set()

    def collect(nodes):
        for n in as_list(nodes):
            if n.get("st_id"):
                st_ids.add(n["st_id"])
            collect(n.get("children"))
    collect(spec.get("hierarchy"))
    for k in ("placement", "events", "entities", "anchor_nodes"):
        for x in as_list(spec.get(k)):
            if x.get("st_id"):
                st_ids.add(x["st_id"])
    for x in as_list(spec.get("events")):
        for s in re.findall(r"R-HSA-\d+", json.dumps(x)):
            st_ids.add(s)
    released = None if skip_link else (bud.check_released(sorted(st_ids)) or None)

    doc = Document()
    bud.configure_document(doc)
    s0 = doc.sections[0]
    for attr in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(s0, attr, Cm(1.9))
    bud.add_footer_page_number(doc)

    tmp0 = tempfile.mkdtemp(prefix="pathway_proposal_maps_")
    spec["_figs"] = {}
    if graphics and pathway_graphics is not None:
        m = pathway_graphics.render_hierarchy_map(spec, os.path.join(tmp0, "hierarchy_map.png"))
        if m:
            spec["_figs"]["_map"] = m
        for sub in as_list(spec.get("subpathways")):
            c = pathway_graphics.render_chain(sub, os.path.join(tmp0, f"chain_{sub.get('key')}.png"))
            if c:
                spec["_figs"]["_chain_" + str(sub.get("key"))] = c
    title_block(doc, spec, ref_status, released)
    executive(doc, spec)
    new_section(doc, False)
    toc_section(doc)
    how_to_use_section(doc, spec)
    new_section(doc, False)
    figures_section(doc, spec)
    new_section(doc, False)
    hierarchy_section(doc, spec, released)
    sec = new_section(doc, True)
    for attr in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, attr, Cm(1.6))
    figs = {}
    tmp = tempfile.mkdtemp(prefix="pathway_proposal_")
    if graphics and reaction_graphic is not None:
        new_events = [e for e in as_list(spec.get("events")) if e.get("status", "NEW").upper() in ("NEW", "INFERRED", "INFERENCE_SOURCE")]
        figs = reaction_graphic.render_all({"new_events": new_events}, tmp)
    events_section(doc, spec, released, figs)
    new_section(doc, False)
    placement_section(doc, spec, released)
    sec = new_section(doc, True)
    for attr in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, attr, Cm(1.6))
    checks_section(doc, spec)
    new_section(doc, True)
    entities_section(doc, spec, released)
    new_section(doc, False)
    literature_section(doc, spec)
    new_section(doc, True)
    log_section(doc, spec)
    new_section(doc, False)
    review_section(doc, spec)
    questions_section(doc, spec)
    appendix(doc, spec)
    p = doc.add_paragraph()
    r = p.add_run("Generated by /curation-gap-fill (new pathway proposal from a review paper) | "
                  "reactome-curator-workflows. Proposal only; nothing has been written to gk_central.")
    r.font.size = Pt(8.5)
    r.font.color.rgb = GREY
    doc.save(out)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render a /curation-gap-fill pathway proposal DOCX.")
    ap.add_argument("spec")
    ap.add_argument("-o", "--out")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--skip-ref-check", action="store_true")
    ap.add_argument("--skip-link-check", action="store_true")
    ap.add_argument("--no-graphics", action="store_true")
    a = ap.parse_args(argv)
    with open(a.spec) as fh:
        spec = json.load(fh)
    spec["_base_dir"] = os.path.dirname(os.path.abspath(a.spec))
    errs = validate(spec)
    if errs:
        print("SPEC INVALID:\n  " + "\n  ".join(errs), file=sys.stderr)
        return 1
    if a.validate:
        print("spec valid")
        return 0
    out = a.out or os.path.splitext(a.spec)[0] + ".docx"
    build(spec, out, skip_ref=a.skip_ref_check, skip_link=a.skip_link_check, graphics=not a.no_graphics)
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
