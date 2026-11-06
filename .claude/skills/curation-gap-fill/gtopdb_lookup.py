#!/usr/bin/env python3
"""Look up a ligand in the IUPHAR/BPS Guide to Pharmacology (GtoPdb).

Reactome drug entities carry a ReferenceTherapeutic whose referenceDatabase is
"Guide to Pharmacology - Ligands" and whose identifier is the GtoPdb ligand ID
(semaglutide: 9724). This helper finds that ID, and the fields the
ReferenceTherapeutic carries (name, INN, type, approved, synonyms), by name, ligand ID,
ChEBI ID or PubChem CID.

Source: the GtoPdb bulk download files, which need no account or API key. These
are the versioned CSVs GtoPdb publishes at https://www.guidetopharmacology.org/DATA/.
They are downloaded once into ~/.cache/reactome-curator-workflows/gtopdb/<version>/
and reused until GtoPdb publishes a new release (re-check with --refresh). Every
answer is stamped with the GtoPdb version it came from. The GtoPdb REST API is
not used, because it needs a per-user API key; the bulk files carry the same
ligand IDs.

Usage:
    python3 gtopdb_lookup.py tirzepatide
    python3 gtopdb_lookup.py --id 11429
    python3 gtopdb_lookup.py --chebi CHEBI:194186
    python3 gtopdb_lookup.py tirzepatide --json
    python3 gtopdb_lookup.py --refresh tirzepatide   # re-check for a newer release

Stdlib only. Exit code 1 when nothing matches, 2 on a network problem.
"""
import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.request

BASE = "https://www.guidetopharmacology.org"
FILES = {"ligands": "/DATA/ligands.csv", "mapping": "/DATA/ligand_id_mapping.csv"}
CACHE = os.path.expanduser("~/.cache/reactome-curator-workflows/gtopdb")
UA = {"User-Agent": "reactome-curator-workflows/gtopdb_lookup"}


# ── bulk files ──────────────────────────────────────────────────────────────
def _fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8")


def _version_of(text):
    m = re.search(r"GtoPdb Version:\s*([0-9.]+)", text.splitlines()[0] if text else "")
    return m.group(1) if m else "unknown"


def _latest_cached():
    if not os.path.isdir(CACHE):
        return None
    vs = sorted(d for d in os.listdir(CACHE) if os.path.isfile(os.path.join(CACHE, d, "ligands.csv")))
    return vs[-1] if vs else None


def load_bulk(refresh=False):
    """Return (version, ligands_rows, mapping_rows), downloading if needed."""
    ver = None if refresh else _latest_cached()
    if ver is None:
        texts = {k: _fetch(BASE + p) for k, p in FILES.items()}
        ver = _version_of(texts["ligands"])
        d = os.path.join(CACHE, ver)
        os.makedirs(d, exist_ok=True)
        for k, t in texts.items():
            with open(os.path.join(d, k + ".csv"), "w", encoding="utf-8") as fh:
                fh.write(t)
    d = os.path.join(CACHE, ver)

    def rows(name):
        with open(os.path.join(d, name + ".csv"), encoding="utf-8") as fh:
            r = list(csv.reader(fh))
        hdr = r[1]          # line 0 is the "# GtoPdb Version" banner
        return [dict(zip(hdr, x)) for x in r[2:]]
    return ver, rows("ligands"), rows("mapping")


def search_bulk(args):
    ver, ligs, maps = load_bulk(args.refresh)
    by_id = {m.get("Ligand id"): m for m in maps}
    hits = []
    q = (args.name or "").strip().lower()
    for L in ligs:
        lid = L.get("Ligand ID")
        m = by_id.get(lid, {})
        syn = [s.strip().lower() for s in re.split(r"\|", L.get("Synonyms", "")) if s.strip()]
        names = {L.get("Name", "").lower(), L.get("INN", "").lower(), *syn}
        names = {re.sub(r"&reg;|&trade;|<[^>]+>", "", n).strip() for n in names}
        if args.id and lid != str(args.id):
            continue
        if args.chebi and m.get("Chebi ID", "").upper() != args.chebi.upper():
            continue
        if args.pubchem_cid and L.get("PubChem CID") != str(args.pubchem_cid):
            continue
        if q and q not in names:
            continue
        hits.append({
            "gtopdb_version": ver, "source": "bulk download",
            "ligand_id": lid, "name": L.get("Name"), "inn": L.get("INN"), "type": L.get("Type"),
            "approved": L.get("Approved") == "yes", "withdrawn": L.get("Withdrawn") == "yes",
            "synonyms": [re.sub(r"&reg;|&trade;", "", s).strip() for s in L.get("Synonyms", "").split("|") if s.strip()],
            "chebi": m.get("Chebi ID") or None, "pubchem_cid": L.get("PubChem CID") or None,
            "pubchem_sid": L.get("PubChem SID") or None,
            "url": f"{BASE}/GRAC/LigandDisplayForward?ligandId={lid}",
            "reactome_referenceDatabase": "Guide to Pharmacology - Ligands",
        })
    return hits


def main(argv=None):
    ap = argparse.ArgumentParser(description="Find a ligand's Guide to Pharmacology ID.")
    ap.add_argument("name", nargs="?", help="ligand name, INN or synonym (exact, case-insensitive)")
    ap.add_argument("--id", help="GtoPdb ligand ID")
    ap.add_argument("--chebi", help="ChEBI ID, e.g. CHEBI:65349")
    ap.add_argument("--pubchem-cid", help="PubChem compound ID")
    ap.add_argument("--refresh", action="store_true", help="re-download the bulk files")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if not (a.name or a.id or a.chebi or a.pubchem_cid):
        ap.error("give a name, --id, --chebi or --pubchem-cid")
    try:
        hits = search_bulk(a)
    except urllib.error.HTTPError as e:
        print(f"GtoPdb returned HTTP {e.code}", file=sys.stderr)
        return 2
    except urllib.error.URLError as e:
        print(f"Could not reach GtoPdb: {e.reason}", file=sys.stderr)
        return 2
    if not hits:
        print("no match", file=sys.stderr)
        return 1
    if a.json:
        print(json.dumps(hits, indent=1))
    else:
        for h in hits:
            print(f"GtoPdb ligand {h['ligand_id']}: {h['name']} | type {h.get('type')} | "
                  f"approved {h.get('approved')} | ChEBI {h.get('chebi') or '-'} | "
                  f"{h.get('source')} {h.get('gtopdb_version', '')}\n  {h['url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
