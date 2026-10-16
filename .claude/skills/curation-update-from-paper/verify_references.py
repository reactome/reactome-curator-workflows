#!/usr/bin/env python3
"""Confirm every PMID in a curation update spec really is the paper cited.

Why this exists
---------------
A PMID can be wrong in a way that no amount of careful reading catches: a DOI
reconstructed from a reference list (rather than read verbatim off the paper)
resolves through ESearch to a real, confidently-returned, completely unrelated
record. That happened while drafting the rotavirus update - a rebuilt DOI for
Elaid et al. 2014 returned PMID 24796500, a Cav1.4 night-blindness paper,
instead of 24746450. It was caught only because a human compared the fields by
hand.

So compare them mechanically. For every reference, fetch the PubMed record and
check it against the citation the spec claims:

    first author surname | first author initials | year | journal | title

A title that does not overlap, or a different first author, means the PMID
points at a different paper: that is an ERROR and the document must not be
rendered. A year that is off by one is normal (epub ahead of print) and is a
WARN. Anything unparseable is reported as UNCHECKED, never as correct.

Standard library only - urllib against eutils.ncbi.nlm.nih.gov.

    python3 verify_references.py spec.json
    python3 verify_references.py spec.json --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Sequence, Tuple

ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
BATCH = 180
TIMEOUT = 30

ERROR = "ERROR"
WARN = "WARN"
UNCHECKED = "UNCHECKED"

# Words that carry no discriminating power when comparing two titles.
_STOP = frozenset("""
a an and are as at by for from in into is its of on or the to via with within
""".split())

_WORD = re.compile(r"[a-z0-9]+")


# ──────────────────────────────────────────────────────────────────────────────
# Citation parsing
# ──────────────────────────────────────────────────────────────────────────────


def parse_citation(citation: str) -> Dict[str, str]:
    """Pull first author, title, journal and year out of a spec citation.

    Expected shape, as written by this skill:
        "Surname AB, Other CD. Title of the paper. Journal 12 (2024): 1-9."
    Every field degrades to "" rather than raising; an unparsed field is simply
    not compared.
    """
    out = {"first_author": "", "initials": "", "title": "", "journal": "",
           "year": ""}
    if not citation:
        return out
    text = " ".join(str(citation).split())

    # Only year-shaped numbers count. "Nature. 2026;640(8012):221-9" puts the
    # issue number in the parentheses, so a bare \(\d{4}\) picks up 8012.
    year_match = re.search(r"\((19|20)(\d{2})\)", text)
    if year_match:
        out["year"] = year_match.group(1) + year_match.group(2)
    else:
        loose = re.search(r"\b(?:19|20)\d{2}\b", text)
        if loose:
            out["year"] = loose.group(0)

    # Authors run up to the first sentence break; initials carry no periods in
    # this house style, so ". " is a safe split.
    chunks = text.split(". ")
    if chunks:
        authors = chunks[0]
        first = authors.split(",")[0].strip()
        bits = first.split()
        if len(bits) >= 2 and re.fullmatch(r"[A-Z]{1,4}", bits[-1]):
            out["initials"] = bits[-1]
            out["first_author"] = " ".join(bits[:-1])
        elif bits:
            out["first_author"] = first
    if len(chunks) >= 2:
        out["title"] = chunks[1].strip()
    if len(chunks) >= 3:
        tail = ". ".join(chunks[2:])
        journal = re.split(r"\s+\d", tail, maxsplit=1)[0]
        out["journal"] = journal.strip(" .,;")
    return out


def title_tokens(title: str) -> set:
    words = _WORD.findall((title or "").lower())
    return {w for w in words if w not in _STOP and len(w) > 2}


def title_overlap(a: str, b: str) -> Optional[float]:
    """Containment of the smaller token set in the larger, 0.0-1.0."""
    ta, tb = title_tokens(a), title_tokens(b)
    if not ta or not tb:
        return None
    return len(ta & tb) / float(min(len(ta), len(tb)))


def normalise_surname(name: str) -> str:
    return re.sub(r"[^a-z]", "", (name or "").lower())


# ──────────────────────────────────────────────────────────────────────────────
# PubMed
# ──────────────────────────────────────────────────────────────────────────────


def fetch_summaries(pmids: Sequence[str], timeout: int = TIMEOUT
                    ) -> Dict[str, Dict[str, Any]]:
    """ESummary for a list of PMIDs. Raises on network failure - callers must
    not silently treat an unreachable NCBI as 'everything verified'."""
    records: Dict[str, Dict[str, Any]] = {}
    unique = [p for p in dict.fromkeys(pmids) if p]
    for start in range(0, len(unique), BATCH):
        chunk = unique[start:start + BATCH]
        params = urllib.parse.urlencode(
            {"db": "pubmed", "retmode": "json", "id": ",".join(chunk)}
        )
        request = urllib.request.Request(
            ESUMMARY + "?" + params,
            headers={"User-Agent": "reactome-curation-update/1.1"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8", "replace"))
        result = payload.get("result", {}) or {}
        for pmid in chunk:
            record = result.get(pmid)
            if isinstance(record, dict):
                records[pmid] = record
    return records


def record_fields(record: Dict[str, Any]) -> Dict[str, str]:
    authors = record.get("authors") or []
    first = ""
    if authors and isinstance(authors[0], dict):
        first = str(authors[0].get("name") or "")
    surname, initials = "", ""
    if first:
        bits = first.split()
        if len(bits) >= 2 and re.fullmatch(r"[A-Za-z]{1,4}", bits[-1]):
            surname, initials = " ".join(bits[:-1]), bits[-1].upper()
        else:
            surname = first
    if not surname:
        surname = str(record.get("sortfirstauthor") or "")
    return {
        "first_author": surname,
        "initials": initials,
        "title": str(record.get("title") or "").rstrip("."),
        "journal": str(record.get("source") or ""),
        "year": (str(record.get("pubdate") or "")[:4]),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Comparison
# ──────────────────────────────────────────────────────────────────────────────

TITLE_ERROR_BELOW = 0.45
TITLE_WARN_BELOW = 0.70


def compare(claimed: Dict[str, str], actual: Dict[str, str]
            ) -> List[Tuple[str, str, str, str]]:
    """Return (severity, field, claimed, actual) for each disagreement."""
    findings: List[Tuple[str, str, str, str]] = []

    overlap = title_overlap(claimed["title"], actual["title"])
    if overlap is None:
        findings.append((UNCHECKED, "title", claimed["title"], actual["title"]))
    elif overlap < TITLE_ERROR_BELOW:
        findings.append((ERROR, "title", claimed["title"], actual["title"]))
    elif overlap < TITLE_WARN_BELOW:
        findings.append((WARN, "title", claimed["title"], actual["title"]))

    ca, aa = normalise_surname(claimed["first_author"]), normalise_surname(
        actual["first_author"])
    if ca and aa and ca != aa:
        # A different first author on a paper that is otherwise the same is
        # still worth stopping for: it usually means the wrong record.
        findings.append(
            (ERROR, "first author", claimed["first_author"],
             actual["first_author"])
        )

    ci, ai = claimed["initials"].upper(), actual["initials"].upper()
    if ci and ai and ci != ai and ca == aa:
        findings.append((WARN, "initials", ci, ai))

    cj, aj = claimed["journal"].lower(), actual["journal"].lower()
    if cj and aj:
        j_overlap = title_overlap(cj, aj)
        if j_overlap is not None and j_overlap < 0.5:
            findings.append(
                (WARN, "journal", claimed["journal"], actual["journal"])
            )

    cy, ay = claimed["year"], actual["year"]
    if cy and ay and cy != ay:
        severity = WARN if abs(int(cy) - int(ay)) <= 1 else ERROR
        findings.append((severity, "year", cy, ay))

    return findings


def verify_spec(spec: Dict[str, Any], timeout: int = TIMEOUT) -> Dict[str, Any]:
    """Verify every reference (and the source paper). Network errors raise."""
    refs = [r for r in (spec.get("references") or []) if isinstance(r, dict)]

    targets: List[Dict[str, Any]] = []
    for idx, ref in enumerate(refs, start=1):
        pmid = str(ref.get("pmid") or "").strip()
        targets.append({
            "where": "references[%d]" % (ref.get("n") or idx),
            "pmid": pmid,
            "citation": str(ref.get("citation") or ""),
        })

    source = spec.get("source_paper")
    if isinstance(source, dict) and str(source.get("pmid") or "").strip():
        targets.append({
            "where": "source_paper",
            "pmid": str(source["pmid"]).strip(),
            "citation": str(source.get("citation") or source.get("title") or ""),
        })

    pmids = [t["pmid"] for t in targets if t["pmid"]]
    records = fetch_summaries(pmids, timeout=timeout) if pmids else {}

    findings: List[Dict[str, Any]] = []
    checked = 0
    for target in targets:
        pmid = target["pmid"]
        if not pmid:
            findings.append({
                "severity": UNCHECKED, "where": target["where"], "pmid": "",
                "field": "pmid", "claimed": target["citation"][:90],
                "actual": "no PMID recorded",
            })
            continue
        record = records.get(pmid)
        if record is None or record.get("error"):
            findings.append({
                "severity": ERROR, "where": target["where"], "pmid": pmid,
                "field": "pmid", "claimed": target["citation"][:90],
                "actual": "PubMed returned no record for this PMID",
            })
            continue
        checked += 1
        claimed = parse_citation(target["citation"])
        actual = record_fields(record)
        for severity, field, cval, aval in compare(claimed, actual):
            findings.append({
                "severity": severity, "where": target["where"], "pmid": pmid,
                "field": field, "claimed": cval, "actual": aval,
            })

    return {
        "checked": checked,
        "total": len(targets),
        "findings": findings,
        "errors": [f for f in findings if f["severity"] == ERROR],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Reporting
# ──────────────────────────────────────────────────────────────────────────────


def format_report(result: Dict[str, Any]) -> str:
    lines = []
    lines.append("Reference verification: %d of %d resolved against PubMed"
                 % (result["checked"], result["total"]))
    findings = result["findings"]
    if not findings:
        lines.append("  all citations match their PMID on author, year, "
                     "journal and title.")
        return "\n".join(lines)

    order = {ERROR: 0, WARN: 1, UNCHECKED: 2}
    for finding in sorted(findings, key=lambda f: order.get(f["severity"], 3)):
        lines.append("")
        lines.append("  [%s] %s  PMID %s  field: %s"
                     % (finding["severity"], finding["where"],
                        finding["pmid"] or "-", finding["field"]))
        lines.append("      spec says : %s" % (finding["claimed"] or "(blank)"))
        lines.append("      PubMed has: %s" % (finding["actual"] or "(blank)"))
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", help="curation update spec JSON")
    parser.add_argument("--json", action="store_true",
                        help="emit findings as JSON")
    parser.add_argument("--timeout", type=int, default=TIMEOUT)
    args = parser.parse_args(argv)

    with open(args.spec, "r", encoding="utf-8") as handle:
        spec = json.load(handle)

    try:
        result = verify_spec(spec, timeout=args.timeout)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        sys.stderr.write(
            "error: could not reach NCBI E-utilities: %s\n"
            "Nothing was verified. Do not record these references as checked.\n"
            % exc
        )
        return 2

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_report(result))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
