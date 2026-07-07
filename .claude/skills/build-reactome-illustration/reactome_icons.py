#!/usr/bin/env python3
"""
reactome_icons.py — deterministic access to the Reactome Icon Library.

The ONLY sanctioned source of image parts for /build-reactome-illustration.
Uses the public Reactome ContentService (search) and the static icon endpoint
(SVG/PNG download). No API key, no third-party dependencies — Python 3 stdlib
(urllib) only.

Subcommands
-----------
  map "<accession>" [--db DB]
      DETERMINISTIC lookup: resolve an external accession (UniProt, ChEBI, GO,
      CL, UBERON, Ensembl, Complex Portal, …) to the exact icon(s) it is mapped
      to, using the bundled `icon_mappings/<DB>2Icon.txt` tables (no network,
      no fuzzy matching). Prints a JSON array of {db, accession, stId, iconName,
      svgUrl, pngUrl}. This is the PREFERRED match step whenever the curator has
      an accession — it removes all name-guessing / hallucination risk. Handles
      prefixed or bare ids (CHEBI:16020 or 16020, UNIPROT:Q99638 or Q99638) and
      auto-detects the database from a known prefix; otherwise searches every
      table. Returns [] (empty) when the accession maps to no icon — that is a
      gap, never a reason to invent one.

  search "<term>" [--category CAT] [--max N] [--species SP]
      Query the icon library by NAME. Prints a JSON array of candidate icons,
      each with its stable id (R-ICO-######), name, categories, external
      references (e.g. UniProt), the Reactome PhysicalEntities the icon is mapped
      to, a short summation, attribution (designer + curator + ORCID), and the
      direct SVG/PNG download URLs. Use this when you have no accession; never
      invent an icon that does not appear here.

  fetch <R-ICO-id> [--outdir DIR] [--png]
      Download the icon's SVG (and optionally PNG) into DIR (default: ./icons).
      Prints the local path(s) as JSON. The downloaded SVG is verbatim library
      art — the sole permitted source of biological image parts.

  info "<term>"
      Alias for `search` with --max 1: the single best match plus full
      attribution, for building the CC-BY credit line.

No-fabrication rule
-------------------
An icon id, name, or download URL may enter the illustration ONLY if it was
returned by `search`/`fetch` in this run. Never emit an R-ICO id from memory,
never guess a download URL, never substitute a hand-drawn shape for a biological
entity that has no library icon — surface the gap instead.
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

CONTENT_SERVICE = "https://reactome.org/ContentService"
ICON_BASE = "https://reactome.org/icon"           # /<R-ICO-id>.svg  and  .png
UA = "reactome-curator-workflows/build-reactome-illustration"
TIMEOUT = 30

# Bundled accession -> icon mapping tables (icon_mappings/<DB>2Icon.txt), each a
# tab-separated  <accession>\t<R-ICO-id>\t<icon name>  file. Ships with the skill
# so accession lookup is deterministic and offline.
MAPPINGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon_mappings")

# Map a known accession prefix to its table stem, so `map "CHEBI:16020"` and
# `map "GO:0005884"` route to the right file without --db. Keys are matched
# case-insensitively against the text before the first ':' in the accession.
PREFIX_TO_DB = {
    "CHEBI": "CHEBI", "GO": "GO", "CL": "CL", "UBERON": "UBERON",
    "UNIPROT": "UNIPROT", "COMPLEXPORTAL": "COMPLEXPORTAL", "CPX": "COMPLEXPORTAL",
    "ENSEMBL": "ENSEMBL", "ENSG": "ENSEMBL", "INTERPRO": "INTERPRO", "IPR": "INTERPRO",
    "MESH": "MESH", "KEGG": "KEGG", "PUBCHEM": "PUBCHEM", "PFAM": "PFAM",
    "RFAM": "RFAM", "SO": "SO", "DOID": "DOID", "NCIT": "NCIT", "NCBI": "NCBI",
    "ENA": "ENA", "OMIT": "OMIT", "OPL": "OPL", "BTO": "BTO",
}


def _get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def _svg_url(ico_id):
    return f"{ICON_BASE}/{ico_id}.svg"


def _png_url(ico_id):
    return f"{ICON_BASE}/{ico_id}.png"


def _clean(html):
    """Strip the <span class="highlighting"> markup the search index injects."""
    if not html:
        return html
    return (html.replace('<span class="highlighting" >', "")
                .replace('<span class="highlighting">', "")
                .replace("</span>", ""))


def _entry_to_icon(e):
    ents = []
    for pe in (e.get("iconPhysicalEntities") or []):
        ents.append({
            "stId": pe.get("stId"),
            "type": pe.get("type"),
            "displayName": pe.get("displayName") or pe.get("name"),
        })
    return {
        "stId": e.get("stId") or e.get("id"),
        "iconName": e.get("iconName") or _clean(e.get("name")),
        "categories": e.get("iconCategories") or [],
        "references": e.get("iconReferences") or [],
        "mappedEntities": ents,
        "summation": _clean(e.get("summation")),
        "designer": e.get("iconDesignerName"),
        "designerUrl": e.get("iconDesignerUrl"),
        "curator": e.get("iconCuratorName"),
        "curatorOrcid": e.get("iconCuratorOrcidId"),
        "svgUrl": _svg_url(e.get("stId") or e.get("id")),
        "pngUrl": _png_url(e.get("stId") or e.get("id")),
    }


def _norm_variants(accession):
    """Candidate forms to match a table entry: the accession as given, its bare
    form (prefix stripped), and its uppercased variants. Tables are inconsistent
    — CHEBI/GO/CL keep the prefix, UBERON/SO/DOID strip it — so try both."""
    acc = accession.strip()
    forms = {acc, acc.upper()}
    if ":" in acc:
        bare = acc.split(":", 1)[1].strip()
        forms.update({bare, bare.upper()})
    return {f for f in forms if f}


def _table_path(db):
    return os.path.join(MAPPINGS_DIR, f"{db}2Icon.txt")


def _search_table(db, accession):
    """Return the icon rows in <db>2Icon.txt whose first column matches the
    accession (in any normalised form). Robust to stray empty fields."""
    path = _table_path(db)
    if not os.path.isfile(path):
        return []
    wanted = _norm_variants(accession)
    hits = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            fields = [f for f in line.split("\t")]
            key = fields[0].strip()
            # match symmetrically: normalise BOTH the input and the table key,
            # so a bare input (16020) matches a prefixed key (CHEBI:16020) and
            # vice versa.
            if not (wanted & _norm_variants(key)):
                continue
            rico = next((f.strip() for f in fields if f.strip().startswith("R-ICO-")), None)
            if not rico:
                continue
            # icon name = last non-empty field that is not the key or the R-ICO id
            name = ""
            for f in reversed(fields):
                fs = f.strip()
                if fs and fs != key and not fs.startswith("R-ICO-"):
                    name = fs
                    break
            hits.append({
                "db": db,
                "accession": key,
                "stId": rico,
                "iconName": name,
                "svgUrl": _svg_url(rico),
                "pngUrl": _png_url(rico),
            })
    return hits


def cmd_map(args):
    acc = args.accession.strip()
    if args.db:
        dbs = [args.db.upper()]
    else:
        prefix = acc.split(":", 1)[0].upper() if ":" in acc else None
        if prefix and prefix in PREFIX_TO_DB:
            dbs = [PREFIX_TO_DB[prefix]]
        else:
            # unknown/absent prefix (e.g. a bare UniProt like Q99638): scan all tables
            dbs = sorted({v for v in PREFIX_TO_DB.values()})

    if not os.path.isdir(MAPPINGS_DIR):
        print(json.dumps({"error": f"mapping tables not found at {MAPPINGS_DIR}; "
                                    "fall back to `search`"}), file=sys.stderr)
        return 2

    hits = []
    seen = set()
    for db in dbs:
        for h in _search_table(db, acc):
            k = (h["db"], h["stId"])
            if k not in seen:
                seen.add(k)
                hits.append(h)

    print(json.dumps(hits, indent=2, ensure_ascii=False))
    if not hits:
        print(f"# no icon mapped to accession '{acc}'"
              + (f" in {args.db}" if args.db else "") + " — this is a gap, do not invent one",
              file=sys.stderr)
    return 0


def cmd_search(args):
    params = {"query": args.term, "types": "Icon", "cluster": "true"}
    if args.species:
        params["species"] = args.species
    url = f"{CONTENT_SERVICE}/search/query?" + urllib.parse.urlencode(params)
    try:
        data = _get(url)
    except Exception as exc:  # noqa: BLE001 - report and exit, never fabricate
        print(json.dumps({"error": str(exc), "url": url}), file=sys.stderr)
        return 2

    icons = []
    for group in data.get("results", []):
        for e in group.get("entries", []):
            if (e.get("exactType") or e.get("type")) != "Icon":
                continue
            icon = _entry_to_icon(e)
            if args.category and args.category.lower() not in [c.lower() for c in icon["categories"]]:
                continue
            icons.append(icon)

    icons = icons[: args.max]
    print(json.dumps(icons, indent=2, ensure_ascii=False))
    if not icons:
        print(f"# no icon matches for '{args.term}'"
              + (f" in category '{args.category}'" if args.category else ""),
              file=sys.stderr)
    return 0


def cmd_fetch(args):
    ico_id = args.ico_id.strip()
    if not ico_id.startswith("R-ICO-"):
        print(json.dumps({"error": f"not a valid icon id: {ico_id!r} (expected R-ICO-######)"}),
              file=sys.stderr)
        return 2
    outdir = args.outdir
    os.makedirs(outdir, exist_ok=True)
    written = {}
    targets = [("svg", _svg_url(ico_id))]
    if args.png:
        targets.append(("png", _png_url(ico_id)))
    for ext, url in targets:
        dest = os.path.join(outdir, f"{ico_id}.{ext}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                payload = r.read()
            with open(dest, "wb") as fh:
                fh.write(payload)
            written[ext] = os.path.abspath(dest)
        except Exception as exc:  # noqa: BLE001
            written[f"{ext}_error"] = str(exc)
    print(json.dumps(written, indent=2))
    return 0 if any(k in written for k in ("svg", "png")) else 2


def cmd_info(args):
    args.max = 1
    args.category = getattr(args, "category", None)
    args.species = getattr(args, "species", None)
    return cmd_search(args)


def main():
    p = argparse.ArgumentParser(description="Reactome Icon Library access for /build-reactome-illustration")
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("map", help="deterministic accession -> icon lookup (bundled tables)")
    m.add_argument("accession", help="external id, e.g. CHEBI:16020, GO:0005884, Q99638, CPX-503")
    m.add_argument("--db", help="force a database table (e.g. UNIPROT, CHEBI, GO, CL, UBERON, COMPLEXPORTAL)")
    m.set_defaults(func=cmd_map)

    s = sub.add_parser("search", help="search the icon library")
    s.add_argument("term")
    s.add_argument("--category", help="filter to one category (protein, compound, cell, receptor, ion channel, cell element, human tissue)")
    s.add_argument("--species", help="species filter, e.g. 'Homo sapiens'")
    s.add_argument("--max", type=int, default=10)
    s.set_defaults(func=cmd_search)

    f = sub.add_parser("fetch", help="download an icon SVG/PNG by R-ICO id")
    f.add_argument("ico_id")
    f.add_argument("--outdir", default="./icons")
    f.add_argument("--png", action="store_true", help="also download the PNG")
    f.set_defaults(func=cmd_fetch)

    i = sub.add_parser("info", help="single best match + attribution")
    i.add_argument("term")
    i.add_argument("--category")
    i.add_argument("--species")
    i.set_defaults(func=cmd_info)

    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
