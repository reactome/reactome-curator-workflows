#!/usr/bin/env python3
"""
reactome_icons.py — deterministic access to the Reactome Icon Library.

The ONLY sanctioned source of image parts for /build-reactome-illustration.
Uses the public Reactome ContentService (search) and the static icon endpoint
(SVG/PNG download). No API key, no third-party dependencies — Python 3 stdlib
(urllib) only.

Subcommands
-----------
  search "<term>" [--category CAT] [--max N] [--species SP]
      Query the icon library. Prints a JSON array of candidate icons, each with
      its stable id (R-ICO-######), name, categories, external references
      (e.g. UniProt), the Reactome PhysicalEntities the icon is mapped to, a
      short summation, attribution (designer + curator + ORCID), and the direct
      SVG/PNG download URLs. This is the match step — never invent an icon that
      does not appear here.

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
