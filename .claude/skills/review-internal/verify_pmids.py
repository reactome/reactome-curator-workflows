#!/usr/bin/env python3
"""
Verify the literature references in a Reactome pathway report against PubMed.

Reads the report DOCX directly, pulls every PubMed URL, resolves the PMIDs in one
batched NCBI E-utilities ESummary call, and reports:

  * author / year / journal disagreements between the report and the PubMed record
  * PMIDs NCBI does not recognise
  * the same PMID cited twice in one reference list (duplicate LiteratureReference)
  * in-text citations with no matching reference in the same section

Nothing is fabricated: every fact comes from the report or from the ESummary
response. A PMID that cannot be checked is reported as unchecked, never as correct.

Standard library only. Requires network access to eutils.ncbi.nlm.nih.gov, which
.claude/settings.json already allowlists.

Usage:
    python3 verify_pmids.py <report.docx> [--json out.json] [--email you@org]
"""

import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
TOOL = "reactome-curator-workflows"
BATCH = 200
TIMEOUT = 45

# "1.4 HIV-1 protease cleaves CARD8 ... (BlackBoxEvent)"  /  "1 The CARD8 inflammasome (Pathway)"
SECTION_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)\s+(.*?)\s*\((Pathway|Reaction|BlackBoxEvent|"
                        r"Polymerisation|Polymerization|Depolymerisation|Depolymerization|"
                        r"FailedReaction)\)\s*$")
PMID_URL_RE = re.compile(r"pubmed/(\d+)")
YEAR_RE = re.compile(r"\((\d{4})\)")
# "Surname AB, Other CD, ... Title. Journal 12 (2018): 827-840."
REF_RE = re.compile(r"^\s*((?:[A-Z][\w'\u00c0-\u024f-]+\s+){0,2}[A-Z][\w'\u00c0-\u024f-]+)[,]?\s+([A-Z]{1,3})\b")
# in-text: "Sharif H et al., 2021" / "Wang et al., 2021" / "Castro and Daugherty, 2023"
INTEXT_RE = re.compile(r"([A-Z][\w'À-ɏ-]+)"          # surname
                       r"(?:\s+([A-Z]{1,3}))?"                  # optional initials
                       r"(?:\s+(?:et\s+al\.?|and\s+[A-Z][\w'-]+))"
                       r"[,\s]+(?:\()?(\d{4})")                 # year


def docx_lines(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf8", "replace")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab/>", "\t", xml)
    xml = re.sub(r"<[^>]+>", "", xml)
    return [ln.strip() for ln in html.unescape(xml).split("\n") if ln.strip()]


def parse_report(lines):
    """Split the report into sections, each with its summation text and references."""
    sections, cur = [], None
    in_refs = False
    for ln in lines:
        m = SECTION_RE.match(ln)
        if m:
            cur = {"id": m.group(1), "title": m.group(2), "cls": m.group(3),
                   "summation": [], "refs": []}
            sections.append(cur)
            in_refs = False
            continue
        if cur is None:
            continue
        low = ln.lower()
        if low.startswith("literature reference"):
            in_refs = True
            continue
        if low.startswith(("summation", "see web page", "regulators of this")):
            if low.startswith("summation"):
                in_refs = False
            continue
        (cur["refs"] if in_refs else cur["summation"]).append(ln)
    return sections


def ref_records(sections):
    """One record per reference line that carries a PubMed URL."""
    out = []
    for s in sections:
        for ln in s["refs"]:
            pm = PMID_URL_RE.search(ln)
            if not pm:
                continue
            am = REF_RE.match(ln)
            ym = YEAR_RE.search(ln)
            # Everything before " <vol> (<year>)" — the journal is its tail. Kept whole
            # rather than split on periods, because abbreviations contain them
            # ("Acta Crystallogr. Sect. F Struct. Biol.").
            jm = re.search(r"^(.*?)\s+\d+\s*\(\d{4}\)", ln)
            out.append({
                "section": s["id"], "section_title": s["title"], "pmid": pm.group(1),
                "surname": am.group(1) if am else None,
                "initials": am.group(2) if am else None,
                "year": ym.group(1) if ym else None,
                "journal_tail": jm.group(1).strip()[-80:] if jm else None,
                "line": ln,
            })
    return out


def esummary(pmids, email=None):
    """Batched ESummary. Returns {pmid: record}. Network failure raises."""
    got = {}
    uniq = sorted(set(pmids), key=int)
    for i in range(0, len(uniq), BATCH):
        chunk = uniq[i:i + BATCH]
        q = {"db": "pubmed", "retmode": "json", "id": ",".join(chunk), "tool": TOOL}
        if email:
            q["email"] = email
        url = EUTILS + "?" + urllib.parse.urlencode(q)
        req = urllib.request.Request(url, headers={"User-Agent": TOOL})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = json.loads(r.read().decode("utf8", "replace"))
        res = data.get("result", {})
        for uid in res.get("uids", []):
            got[uid] = res[uid]
    return got


def norm_journal(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


def compare(recs, ncbi):
    findings = []
    for r in recs:
        rec = ncbi.get(r["pmid"])
        loc = f"§{r['section']}"
        if rec is None or rec.get("error"):
            findings.append(("HIGH", loc, r["pmid"], "PMID not found in PubMed",
                             f"report: {r['surname'] or '?'} {r['year'] or '?'}", "—"))
            continue
        first = (rec.get("sortfirstauthor") or "").strip()
        # Surnames can be multi-word ("Robert Hollingsworth L"), so the initials are the
        # LAST token, not everything after the first space.
        n_sur, n_ini = (first.rsplit(" ", 1) + [""])[:2] if " " in first else (first, "")
        n_year = (rec.get("pubdate") or "")[:4]
        n_src = rec.get("source") or ""

        if r["surname"] and n_sur and r["surname"].lower() != n_sur.lower():
            findings.append(("HIGH", loc, r["pmid"], "First-author surname disagrees",
                             f"report: {r['surname']}", f"PubMed: {n_sur}"))
        elif r["initials"] and n_ini and r["initials"].upper() != n_ini.upper().replace(" ", ""):
            findings.append(("MEDIUM", loc, r["pmid"], "First-author initials disagree",
                             f"report: {r['surname']} {r['initials']}",
                             f"PubMed: {n_sur} {n_ini}"))
        if r["year"] and n_year and r["year"] != n_year:
            findings.append(("HIGH", loc, r["pmid"], "Publication year disagrees",
                             f"report: {r['year']}", f"PubMed: {n_year}"))
        if r["journal_tail"] and n_src and norm_journal(n_src) not in norm_journal(r["journal_tail"]):
            findings.append(("LOW", loc, r["pmid"], "Journal name not found in the reference",
                             f"report: ...{r['journal_tail'][-40:]}", f"PubMed: {n_src}"))
    return findings


def duplicates(recs):
    by_sec = defaultdict(lambda: defaultdict(list))
    for r in recs:
        by_sec[r["section"]][r["pmid"]].append(r["line"])
    out = []
    for sec, pmids in by_sec.items():
        for pmid, lines in pmids.items():
            if len(lines) > 1:
                same = len(set(lines)) == 1
                out.append(("HIGH", f"§{sec}", pmid,
                            f"PMID listed {len(lines)}x in one reference list",
                            "identical text" if same else "differing author formatting",
                            "Merge duplicate LiteratureReference instances (cf. GT037)"))
    return out


def unmatched_citations(sections, recs):
    """In-text citations with no reference carrying that surname+year in the same section."""
    by_sec = defaultdict(set)
    for r in recs:
        if r["surname"] and r["year"]:
            full = r["surname"].lower()
            by_sec[r["section"]].add((full, r["year"]))
            by_sec[r["section"]].add((full.split()[-1], r["year"]))
    out = []
    for s in sections:
        known = by_sec.get(s["id"], set())
        seen = set()
        for line in s["summation"]:
            for sur, ini, yr in INTEXT_RE.findall(line):
                key = (sur.lower(), yr)
                if key in known or key in seen:
                    continue
                seen.add(key)
                near = sorted({y for (su, y) in known if su == sur.lower()})
                if near:
                    out.append(("HIGH", f"§{s['id']}", "—",
                                f"'{(sur + ' ' + (ini or '')).strip()} {yr}' cited; same author "
                                f"listed under a different year", f"cited: {yr}",
                                f"listed: {', '.join(near)}"))
                else:
                    out.append(("HIGH", f"§{s['id']}", "—",
                                f"'{sur} {(ini or '').strip()} {yr}' cited; no matching reference "
                                f"in this section", "—",
                                "Add the reference or remove the citation"))
    return out


def uncited_refs(sections, recs):
    out = []
    by_sec = defaultdict(list)
    for r in recs:
        by_sec[r["section"]].append(r)
    for s in sections:
        text = " ".join(s["summation"])
        cited = {(su.lower(), yr) for su, _i, yr in INTEXT_RE.findall(text)}
        for r in by_sec.get(s["id"], []):
            if not (r["surname"] and r["year"]):
                continue
            sur = r["surname"].lower()
            if (sur, r["year"]) not in cited and (sur.split()[-1], r["year"]) not in cited:
                out.append(("LOW", f"§{s['id']}", r["pmid"],
                            f"{r['surname']} {r['year']} listed but not cited in the summation",
                            "—", "Cite in the text or remove"))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report", help="pathway report .docx")
    ap.add_argument("--json", help="also write findings as JSON")
    ap.add_argument("--email", help="contact email sent to NCBI (courtesy, optional)")
    a = ap.parse_args()

    lines = docx_lines(a.report)
    sections = parse_report(lines)
    recs = ref_records(sections)
    pmids = sorted({r["pmid"] for r in recs}, key=int)

    print(f"Report      : {a.report}")
    print(f"Sections    : {len(sections)}")
    print(f"References  : {len(recs)} with a PubMed URL, {len(pmids)} unique PMIDs")

    if not pmids:
        print("\nNo PubMed URLs found — nothing to verify.")
        return 0

    try:
        ncbi = esummary(pmids, a.email)
    except Exception as e:
        print(f"\nESUMMARY FAILED: {e}", file=sys.stderr)
        print("No PMID was verified. Do NOT record these references as checked.",
              file=sys.stderr)
        return 2

    print(f"Resolved    : {len(ncbi)}/{len(pmids)} against PubMed")

    findings = (compare(recs, ncbi) + duplicates(recs)
                + unmatched_citations(sections, recs) + uncited_refs(sections, recs))
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    findings.sort(key=lambda f: (order[f[0]], f[1]))

    if not findings:
        print("\nNo discrepancies found.")
    else:
        print(f"\n{len(findings)} finding(s):\n")
        w = [8, 9, 10, 52, 30, 30]
        hdr = ["PRIORITY", "LOCATION", "PMID", "ISSUE", "REPORT SAYS", "PUBMED / ACTION"]
        print("  ".join(h.ljust(x) for h, x in zip(hdr, w)))
        print("  ".join("-" * x for x in w))
        for f in findings:
            print("  ".join(str(c)[:x].ljust(x) for c, x in zip(f, w)))

    unchecked = [p for p in pmids if p not in ncbi]
    if unchecked:
        print(f"\nUNCHECKED ({len(unchecked)}): {', '.join(unchecked)}")

    if a.json:
        with open(a.json, "w") as fh:
            json.dump([dict(zip(["priority", "location", "pmid", "issue", "report", "pubmed"], f))
                       for f in findings], fh, indent=2)
        print(f"\nJSON written to {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
