#!/usr/bin/env python3
"""
reactome_icons.py — deterministic access to the Reactome Icon Library.

The ONLY sanctioned source of image parts for /curation-build-illustration.
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
      Valid --category tokens: protein, compound, receptor, transporter,
      cell_type, cell_element, human_tissue, background, therapeutic. (Note
      `transporter` — there is no `ion_channel` token.) An unknown token is a
      hard error, never an empty result, so a typo can't masquerade as a gap.

  fetch <R-ICO-id> [--outdir DIR] [--png]
      Download the icon's SVG (and optionally PNG) into DIR (default: ./icons).
      Prints the local path(s) as JSON. The downloaded SVG is verbatim library
      art — the sole permitted source of biological image parts.

  fetch-ehld <ST_ID> [--outdir DIR]
      Download an EXISTING Reactome EHLD SVG by pathway stable id (e.g.
      R-HSA-109581) into DIR (default: cwd). This is the sanctioned base diagram
      for Mode A (modify an existing EHLD): its structure — compartments,
      REGION-/OVERLAY- subpathway groups, ANALINFO boxes, and already-placed
      R-ICO icons — is preserved verbatim while new library icons are added
      around it. A 404 means the pathway has no published EHLD; report that,
      never fabricate a base diagram.

  place <icon.svg> --x X --y Y --prefix TOK [--scale S | --width W | --height H]
        [--class CAT] [--into <existing.svg>]
      Emit a ready-to-splice <g> that places a downloaded icon on the EHLD
      canvas at (X, Y), scaled, with EVERY internal id namespaced by --prefix and
      every reference to those ids (url(#…), href="#…", clip-path, gradients,
      masks) rewritten to match. Icon SVGs are Figma exports full of generic ids
      — `Vector`, `BG`, `Nucleus`, `paint0_linear_…` — so two placements, or two
      different icons, WILL collide and silently corrupt each other's gradients
      and clip-paths. This does that rewrite mechanically instead of by hand.
      The icon's vector paths are copied verbatim (only ids are touched), so the
      "never redraw library art" rule holds by construction. `--into` checks the
      chosen prefix against an existing SVG's ids first, which is what you want
      when splicing into a base EHLD in Mode A.

  check-plan <plan.json> [--online]
      Verify the placement plan handed to the bundled Figma plugin
      (figma-plugin/) before it is built: pathway/subpathway ST_ID form, at
      least two subpathways, R-ICO id form, category tokens, and whether any
      placement falls outside the canvas. `--online` additionally confirms that
      every R-ICO id resolves to a real icon — the plugin can only draw what the
      plan names, so the plan is the one place a fabricated id could enter the
      figure, and this closes it.

  validate <ehld.svg>
      Check a composed EHLD against the official spec and the corpus
      conventions: canvas size, duplicate ids, dangling url(#…) references,
      REGION-/OVERLAY- pairing and ST_ID form, arrows wrongly inside an OVERLAY-
      group, ANALINFO presence and opacity, raster content, outlined vs editable
      text, full-canvas background, placeholder ST_IDs, and label-box geometry.
      Prints JSON {ok, errors, warnings, info}; exit 1 if any error. Run it on
      every composed SVG before handing the file to the curator.

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
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

# A valid icon id is exactly "R-ICO-" followed by digits. Enforcing this (rather
# than a bare startswith) stops a crafted id like "R-ICO-../../x" from escaping
# the download directory when composing the output path.
ICO_ID_RE = re.compile(r"^R-ICO-\d+$")

# The category tokens the ContentService actually stores on an icon
# (`iconCategories`). Verified live against the whole library — these are the
# ONLY accepted values for `--category`. Note `transporter`, not `ion_channel`:
# the Icon Library Guidelines call the category "Ion channels", but the metadata
# token is `transporter`. Passing an unknown token used to return an empty list,
# which reads exactly like "no icon exists" — i.e. a fabricated gap — so an
# unknown token is now a hard error instead.
# Enumerated exhaustively over all 2,569 icons in the library (query *:* with
# rows=5000 — note `start` does not paginate this endpoint, so a single large
# pull is the only way to see the whole set). Counts at time of writing:
# protein 1429, compound 457, cell_element 242, receptor 203, cell_type 116,
# transporter 74, human_tissue 69, therapeutic 56, background 41, arrow 13.
CATEGORIES = (
    "protein",       # Proteins
    "compound",      # Compounds
    "receptor",      # Receptors
    "transporter",   # Ion channels / transporters
    "cell_type",     # Cell types
    "cell_element",  # Cell elements (incl. compartments: cell, nucleus, organelles)
    "human_tissue",  # Human tissue
    "background",    # Scene backgrounds (tissue/organ settings)
    "therapeutic",   # Therapeutic agents
    "arrow",         # Connector glyphs (e.g. R-ICO-012348 "Process arrow")
)

CONTENT_SERVICE = "https://reactome.org/ContentService"
ICON_BASE = "https://reactome.org/icon"           # /<R-ICO-id>.svg  and  .png
EHLD_BASE = "https://reactome.org/download/current/ehld"  # /<ST_ID>.svg  (existing EHLDs)
UA = "reactome-curator-workflows/curation-build-illustration"
TIMEOUT = 30

# A pathway stable id is "R-", a 3-letter species code, "-", digits (e.g.
# R-HSA-109581). Enforced when fetching an existing EHLD so a crafted id cannot
# escape the download directory or point off-endpoint.
ST_ID_RE = re.compile(r"^R-[A-Z]{3}-\d+$")

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
    if args.category and args.category.lower() not in CATEGORIES:
        print(json.dumps({"error": f"unknown category {args.category!r}",
                          "validCategories": list(CATEGORIES)}), file=sys.stderr)
        return 2

    # The ContentService returns only 10 entries per type unless `rows` is set.
    # Category filtering happens client-side, so a small page silently starves
    # the filter and reports a gap that isn't one. Pull a real pool, then
    # truncate to --max locally.
    rows = 200 if args.category else max(args.max * 3, 30)
    params = {"query": args.term, "types": "Icon", "cluster": "true", "rows": str(rows)}
    if args.species:
        params["species"] = args.species
    url = f"{CONTENT_SERVICE}/search/query?" + urllib.parse.urlencode(params)
    try:
        data = _get(url)
    except Exception as exc:  # noqa: BLE001 - report and exit, never fabricate
        print(json.dumps({"error": str(exc), "url": url}), file=sys.stderr)
        return 2

    icons = []
    seen = set()
    for group in data.get("results", []):
        for e in group.get("entries", []):
            if (e.get("exactType") or e.get("type")) != "Icon":
                continue
            icon = _entry_to_icon(e)
            if icon["stId"] in seen:      # the same icon can appear in >1 cluster
                continue
            if args.category and args.category.lower() not in [c.lower() for c in icon["categories"]]:
                continue
            seen.add(icon["stId"])
            icons.append(icon)

    truncated = len(icons)
    icons = icons[: args.max]
    print(json.dumps(icons, indent=2, ensure_ascii=False))
    if not icons:
        print(f"# no icon matches for '{args.term}'"
              + (f" in category '{args.category}'" if args.category else "")
              + " — this is a gap, do not invent one", file=sys.stderr)
    elif truncated > len(icons):
        print(f"# showing {len(icons)} of {truncated} matches; raise --max to see more",
              file=sys.stderr)
    return 0


def cmd_fetch(args):
    ico_id = args.ico_id.strip()
    if not ICO_ID_RE.match(ico_id):
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


def cmd_fetch_ehld(args):
    """Download an EXISTING Reactome EHLD SVG by pathway ST_ID, for Mode A
    (modify an existing EHLD). This is the sanctioned way to obtain the base
    diagram — its structure (compartments, REGION-/OVERLAY- groups, ANALINFO,
    existing R-ICO placements) is preserved verbatim and new library icons are
    added around it. A 404 means the pathway has no published EHLD — that is a
    fact to report, never a licence to fabricate a base diagram."""
    st_id = args.st_id.strip()
    if not ST_ID_RE.match(st_id):
        print(json.dumps({"error": f"not a valid pathway ST_ID: {st_id!r} "
                                    "(expected R-XXX-#######, e.g. R-HSA-109581)"}),
              file=sys.stderr)
        return 2
    outdir = args.outdir
    os.makedirs(outdir, exist_ok=True)
    dest = os.path.join(outdir, f"{st_id}.svg")
    url = f"{EHLD_BASE}/{st_id}.svg"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            payload = r.read()
    except urllib.error.HTTPError as exc:  # noqa: BLE001
        hint = " — this pathway has no published EHLD" if exc.code == 404 else ""
        print(json.dumps({"error": f"HTTP {exc.code} fetching {url}{hint}",
                          "stId": st_id, "url": url}), file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc), "url": url}), file=sys.stderr)
        return 2
    with open(dest, "wb") as fh:
        fh.write(payload)
    print(json.dumps({"stId": st_id, "svg": os.path.abspath(dest),
                      "bytes": len(payload), "sourceUrl": url}, indent=2))
    return 0


# ---------------------------------------------------------------------------
# place — namespace an icon's ids and emit a positioned <g> for splicing
# ---------------------------------------------------------------------------

# Every place an internal id can be referenced from inside an SVG. Icon exports
# use url(#…) for fills/gradients/clip-paths/masks/filters and href="#…" for
# <use>. Miss one of these and the reference dangles: the shape renders black or
# unclipped, which is exactly the corruption `place` exists to prevent.
_ID_DECL_RE = re.compile(r'\bid\s*=\s*"([^"]*)"')
_URL_REF_RE = re.compile(r'url\(\s*#([^)\s]+)\s*\)')
_HREF_REF_RE = re.compile(r'\b((?:xlink:)?href)\s*=\s*"#([^"]*)"')


def _split_root_svg(text):
    """Return (open_tag, inner, ) for the root <svg> element. Scans for the
    closing '>' outside quotes rather than regexing '<svg[^>]*>', so an
    attribute value containing '>' cannot truncate the tag."""
    start = text.find("<svg")
    if start < 0:
        return None, None
    i, quote = start + 4, None
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == ">":
            break
        i += 1
    else:
        return None, None
    open_tag = text[start:i + 1]
    end = text.rfind("</svg>")
    if end < 0:
        return None, None
    return open_tag, text[i + 1:end]


def _attr(tag, name):
    m = re.search(r'\b%s\s*=\s*"([^"]*)"' % re.escape(name), tag)
    return m.group(1) if m else None


def _num(value):
    """Parse an SVG length ('127', '127px', '104.5') to float, or None."""
    if value is None:
        return None
    m = re.match(r"\s*(-?[\d.]+)", value)
    return float(m.group(1)) if m else None


def _fmt(x):
    """3 decimal places, per the spec's Illustrator export setting, with
    trailing zeros trimmed so the output stays readable."""
    return f"{x:.3f}".rstrip("0").rstrip(".") or "0"


def cmd_place(args):
    try:
        with open(args.icon, encoding="utf-8") as fh:
            raw = fh.read()
    except OSError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2

    prefix = args.prefix
    if not prefix:
        print(json.dumps({"error": "--prefix must be non-empty; it is what keeps "
                                   "this placement's ids from colliding"}), file=sys.stderr)
        return 2

    open_tag, inner = _split_root_svg(raw)
    if inner is None:
        print(json.dumps({"error": f"{args.icon}: no parseable root <svg> element"}),
              file=sys.stderr)
        return 2

    # Intrinsic size: viewBox wins (it defines the user-unit coordinate system
    # the paths are drawn in); fall back to width/height.
    vb = _attr(open_tag, "viewBox")
    if vb:
        parts = [float(p) for p in re.split(r"[\s,]+", vb.strip()) if p]
        if len(parts) != 4:
            print(json.dumps({"error": f"malformed viewBox: {vb!r}"}), file=sys.stderr)
            return 2
        min_x, min_y, vb_w, vb_h = parts
    else:
        min_x = min_y = 0.0
        vb_w, vb_h = _num(_attr(open_tag, "width")), _num(_attr(open_tag, "height"))
        if not vb_w or not vb_h:
            print(json.dumps({"error": "icon has neither viewBox nor width/height; "
                                       "cannot compute scale"}), file=sys.stderr)
            return 2

    if args.scale is not None:
        scale = args.scale
    elif args.width is not None:
        scale = args.width / vb_w
    elif args.height is not None:
        scale = args.height / vb_h
    else:
        scale = 1.0
    if scale <= 0:
        print(json.dumps({"error": "scale must be > 0"}), file=sys.stderr)
        return 2

    # --- namespace every declared id, then every reference to one -----------
    declared = set(_ID_DECL_RE.findall(inner))
    if not declared:
        print(json.dumps({"warning": "icon declares no ids; nothing to namespace"}),
              file=sys.stderr)

    def _decl(m):
        name = m.group(1)
        return f'id="{prefix}{name}"' if name in declared else m.group(0)

    def _url(m):
        name = m.group(1)
        return f"url(#{prefix}{name})" if name in declared else m.group(0)

    def _href(m):
        attr, name = m.group(1), m.group(2)
        return f'{attr}="#{prefix}{name}"' if name in declared else m.group(0)

    out = _ID_DECL_RE.sub(_decl, inner)
    out = _URL_REF_RE.sub(_url, out)
    out = _HREF_REF_RE.sub(_href, out)

    # Dangling references are a real corruption mode: a url(#x) whose target
    # lives in a <style> block or another file will not be rewritten and will
    # now point at nothing. Surface it rather than emitting broken art.
    dangling = sorted({n for n in _URL_REF_RE.findall(out)
                       if not n.startswith(prefix)}
                      | {n for _, n in _HREF_REF_RE.findall(out)
                         if not n.startswith(prefix)})

    # A <style> block carries class selectors that are NOT namespaced here and
    # will collide across placements. None of the current library icons ship one.
    has_style = "<style" in inner

    # The icon's own R-ICO group is the natural place for the category class,
    # matching how production EHLDs tag placed icons (class="cell_type", …).
    # Take the OUTERMOST one — i.e. the earliest <g id="R-ICO-…"> in document
    # order. Compound icons nest other icons (the cell contains a nucleus, a
    # nucleolus, lysosomes), and those inner ids sort before the real root, so
    # sorting rather than scanning tags the wrong group.
    root_ico, root_pos = None, None
    for m in re.finditer(r'<g\b[^>]*\bid="(R-ICO-\d+)"', inner):
        if root_pos is None or m.start() < root_pos:
            root_ico, root_pos = m.group(1), m.start()
    if args.klass and root_ico:
        out = re.sub(r'(<g\b[^>]*\bid="%s")' % re.escape(prefix + root_ico),
                     r'\1 class="%s"' % args.klass, out, count=1)

    tx, ty = args.x, args.y
    transform = f"translate({_fmt(tx)},{_fmt(ty)})"
    if scale != 1.0:
        transform += f" scale({_fmt(scale)})"
    if min_x or min_y:
        transform += f" translate({_fmt(-min_x)},{_fmt(-min_y)})"

    body = out.strip("\n")
    if args.indent:
        pad = " " * args.indent
        body = "\n".join(pad + "  " + ln if ln.strip() else ln for ln in body.split("\n"))
        head, tail = pad, pad
    else:
        head = tail = ""
    snippet = f'{head}<g transform="{transform}">\n{body}\n{tail}</g>'

    # Collision check against the file this will be spliced into (Mode A).
    collisions = []
    if args.into:
        try:
            with open(args.into, encoding="utf-8") as fh:
                target_ids = set(_ID_DECL_RE.findall(fh.read()))
        except OSError as exc:
            print(json.dumps({"error": f"--into: {exc}"}), file=sys.stderr)
            return 2
        collisions = sorted({prefix + d for d in declared} & target_ids)

    meta = {
        "icon": os.path.abspath(args.icon),
        "rootIconId": root_ico,
        "prefix": prefix,
        "idsNamespaced": len(declared),
        "scale": round(scale, 6),
        "placedAt": {"x": tx, "y": ty},
        "placedSize": {"width": round(vb_w * scale, 3), "height": round(vb_h * scale, 3)},
        "boundingBox": {"x": tx, "y": ty,
                        "x2": round(tx + vb_w * scale, 3),
                        "y2": round(ty + vb_h * scale, 3)},
    }
    if dangling:
        meta["danglingReferences"] = dangling
    if has_style:
        meta["warning"] = ("icon contains a <style> block; its class selectors are NOT "
                           "namespaced and may collide with other placements")
    if collisions:
        meta["collisions"] = collisions
        meta["error"] = (f"prefix {prefix!r} still collides with "
                         f"{len(collisions)} id(s) already in {args.into} — pick another")

    print(snippet)
    print(json.dumps(meta, indent=2), file=sys.stderr)
    return 1 if collisions else 0


# ---------------------------------------------------------------------------
# validate — check a composed EHLD against the spec + corpus conventions
# ---------------------------------------------------------------------------

SVG_NS = "http://www.w3.org/2000/svg"

# Both are legitimate: 1366x768 is the authoring artboard (and what
# reactome.org serves for a published EHLD); 1396x798 is the same artboard with
# the 15 px export bleed on each side.
VALID_CANVASES = {(1366.0, 768.0), (1396.0, 798.0)}

# A subpathway region id encodes a real pathway ST_ID, or a flagged placeholder.
REGION_ST_ID_RE = re.compile(r"^(R-[A-Z]{3}-\d+|R-HSA-PLACEHOLDER-\d+)$")

LABEL_FILL = "#0F82BC"
ANALINFO_FILL = "#C6C6C6"


def _tag(el):
    return el.tag.split("}", 1)[-1] if "}" in el.tag else el.tag


def cmd_validate(args):
    import xml.etree.ElementTree as ET

    errors, warnings = [], []

    try:
        with open(args.svg, encoding="utf-8") as fh:
            raw = fh.read()
    except OSError as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}), file=sys.stderr)
        return 2
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        print(json.dumps({"ok": False, "file": args.svg,
                          "errors": [f"not well-formed XML: {exc}"]}, indent=2))
        return 1

    parents = {child: parent for parent in root.iter() for child in parent}

    def ancestors(el):
        while el in parents:
            el = parents[el]
            yield el

    els = list(root.iter())
    by_tag = {}
    for el in els:
        by_tag.setdefault(_tag(el), []).append(el)

    # --- canvas -------------------------------------------------------------
    w, h = _num(root.get("width")), _num(root.get("height"))
    vb = root.get("viewBox")
    canvas = None
    if vb:
        p = [float(x) for x in re.split(r"[\s,]+", vb.strip()) if x]
        if len(p) == 4:
            canvas = (p[2], p[3])
    if canvas is None and w and h:
        canvas = (w, h)
    if canvas is None:
        errors.append("root <svg> has neither a usable viewBox nor width/height")
    elif canvas not in VALID_CANVASES:
        errors.append(f"canvas is {canvas[0]:g}x{canvas[1]:g}; expected 1366x768 "
                      "(authoring) or 1396x798 (with 15px export bleed)")

    # --- ids: duplicates and dangling references ----------------------------
    # Duplicate ids are the signature failure of splicing an icon in without
    # namespacing it, and they break REGION-/OVERLAY- selection in the browser.
    declared = _ID_DECL_RE.findall(raw)
    seen, dupes = set(), set()
    for i in declared:
        (dupes if i in seen else seen).add(i)
    if dupes:
        errors.append(f"{len(dupes)} duplicate id(s): {', '.join(sorted(dupes)[:10])}"
                      + (" …" if len(dupes) > 10 else "")
                      + " — namespace each placement (see `place --prefix`)")

    refs = set(_URL_REF_RE.findall(raw)) | {n for _, n in _HREF_REF_RE.findall(raw)}
    dangling = sorted(refs - seen)
    if dangling:
        errors.append(f"{len(dangling)} reference(s) point at undefined ids: "
                      + ", ".join(dangling[:10]) + (" …" if len(dangling) > 10 else ""))

    # --- raster content -----------------------------------------------------
    if by_tag.get("image"):
        errors.append(f"{len(by_tag['image'])} raster <image> element(s); the spec "
                      "requires pure vector — remove or revectorise them")

    # --- subpathway machinery ----------------------------------------------
    overlays = {el.get("id"): el for el in els
                if (el.get("id") or "").startswith("OVERLAY-")}
    regions = {el.get("id"): el for el in els
               if (el.get("id") or "").startswith("REGION-")}

    if len(overlays) < 2:
        errors.append(f"found {len(overlays)} OVERLAY- group(s); an EHLD is defined as "
                      "a high-level pathway with TWO OR MORE subpathways as active regions")

    for oid in sorted(overlays):
        st = oid[len("OVERLAY-"):]
        if not REGION_ST_ID_RE.match(st):
            errors.append(f"{oid}: {st!r} is not a valid pathway ST_ID "
                          "(expected R-XXX-####### or R-HSA-PLACEHOLDER-<n>)")
    for rid in sorted(regions):
        st = rid[len("REGION-"):]
        if not REGION_ST_ID_RE.match(st):
            errors.append(f"{rid}: {st!r} is not a valid pathway ST_ID")
        # If both forms exist for a subpathway, REGION- must contain OVERLAY-.
        oid = "OVERLAY-" + st
        if oid in overlays and regions[rid] not in list(ancestors(overlays[oid])):
            errors.append(f"{rid} does not contain {oid}; when both exist the REGION- "
                          "group must wrap the OVERLAY- group")
    for oid in sorted(overlays):
        st = oid[len("OVERLAY-"):]
        if "REGION-" + st not in regions:
            warnings.append(f"{oid} has no matching REGION-{st} "
                            "(optional, but every corpus subpathway has one)")

    # --- arrows must never live inside an OVERLAY- group --------------------
    for oid, ov in sorted(overlays.items()):
        bad = [el for el in ov.iter()
               if (el.get("id") or "").upper().startswith("ARROW")
               or "arrow" in (el.get("class") or "").split()]
        if bad:
            errors.append(f"{oid} contains {len(bad)} arrow element(s); an OVERLAY- "
                          "group is analysis-overlayable and must hold the label box "
                          "only — move arrows to the ARROWS layer or the REGION- group")

    # --- ANALINFO -----------------------------------------------------------
    analinfos = [el for el in els if (el.get("id") or "").startswith("ANALINFO")]
    if not analinfos:
        errors.append("no ANALINFO group; one analysis-information label per pathway "
                      "label is MANDATORY")
    elif len(analinfos) < len(overlays):
        errors.append(f"{len(analinfos)} ANALINFO group(s) for {len(overlays)} "
                      "subpathway label(s); one per label is MANDATORY")
    for el in analinfos:
        op = el.get("opacity")
        if op is None:
            op = (re.search(r"opacity\s*:\s*([\d.]+)", el.get("style") or "") or [None, None])[1]
        val = _num(op)
        # Spec says 0%. Production files use 0.01 — a fully transparent group is
        # dropped from hit-testing by some renderers — so accept anything <=0.01.
        if val is None or val > 0.01:
            errors.append(f"{el.get('id')}: group opacity is {op!r}; must be 0 "
                          "(production EHLDs use 0.01) with inner shapes left at 100%")

    # --- text ---------------------------------------------------------------
    texts = by_tag.get("text", [])
    if not texts:
        warnings.append("no <text> elements — labels appear to be outlined <path>s. "
                        "Distributed EHLDs are exported that way, but an authored "
                        "EHLD must keep real editable <text> (spec)")
    for el in texts:
        content = "".join(el.itertext())
        exotic = sorted({c for c in content if ord(c) > 127})
        if exotic:
            warnings.append(f"<text> contains non-ASCII {exotic}; spell Greek letters "
                            "out in lowercase (alpha, not the symbol)")

    # --- background ---------------------------------------------------------
    for el in by_tag.get("rect", []):
        rw, rh = _num(el.get("width")), _num(el.get("height"))
        if rw and rh and rw >= 1366 and rh >= 768:
            warnings.append("a full-canvas background rect is present; the spec says "
                            "do not author one (Reactome renders EHLDs in blank "
                            "zoomable space). Illustrator adds it on export")
            break

    # --- placeholders, logo, analysis legend --------------------------------
    placeholders = sorted({m for m in re.findall(r"R-HSA-PLACEHOLDER-\d+", raw)})
    if placeholders:
        warnings.append(f"placeholder ST_ID(s) present ({', '.join(placeholders)}); "
                        "replace with real ST_IDs before Pathway Browser ingestion")

    logos = [el for el in els if (el.get("id") or "").upper().startswith("LOGO")]
    if not logos:
        warnings.append("no LOGO group; production EHLDs carry the Reactome logo at 50% opacity")
    else:
        for el in logos:
            val = _num(el.get("opacity"))
            if val is not None and abs(val - 0.5) > 0.01:
                warnings.append(f"{el.get('id')}: opacity {val}; the Reactome logo is always 50%")

    if not any((el.get("id") or "") == "ICON" for el in els):
        warnings.append("no ICON group (the analysis-overlay legend with 50/75/100 "
                        "children); every corpus EHLD has one")

    # --- label box geometry -------------------------------------------------
    label_rects = [el for el in by_tag.get("rect", [])
                   if (el.get("fill") or "").upper() == LABEL_FILL]
    for el in label_rects:
        rw, rh = _num(el.get("width")), _num(el.get("height"))
        if rw is not None and rw < 170:
            warnings.append(f"a {LABEL_FILL} label box is {rw:g}px wide; minimum is 170px")
        if rh is not None and rh not in (30.0, 42.0, 43.0):
            warnings.append(f"a {LABEL_FILL} label box is {rh:g}px high; expected 30 "
                            "(single line) or 43 (two lines)")
        if _num(el.get("rx")) not in (8.0,):
            warnings.append(f"a {LABEL_FILL} label box has rx={el.get('rx')!r}; "
                            "the spec corner radius is 8px")
    if overlays and not label_rects:
        warnings.append(f"no rect filled {LABEL_FILL} found; subpathway label boxes "
                        "should use that fill")

    # Search rather than match: a placed icon's id carries the per-placement
    # prefix from `place` (p01-R-ICO-013570) and may carry a repeat suffix
    # (R-ICO-013570_2), so anchoring at the start of the id undercounts to zero.
    ico_ids = sorted({m.group(0) for i in seen
                      for m in [re.search(r"R-ICO-\d+", i)] if m})
    report = {
        "file": os.path.abspath(args.svg),
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "info": {
            "canvas": f"{canvas[0]:g}x{canvas[1]:g}" if canvas else None,
            "regions": len(regions),
            "overlays": len(overlays),
            "analinfo": len(analinfos),
            "textElements": len(texts),
            "paths": len(by_tag.get("path", [])),
            "rasterImages": len(by_tag.get("image", [])),
            "distinctIcons": len(ico_ids),
            "iconIds": ico_ids,
            "topLevelLayers": [el.get("id") for el in root if el.get("id")],
            "subpathwayStIds": sorted(o[len("OVERLAY-"):] for o in overlays),
        },
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if errors else 0


# ---------------------------------------------------------------------------
# check-plan — verify a Figma-plugin placement plan before it is built
# ---------------------------------------------------------------------------

def cmd_check_plan(args):
    """Validate the placement plan handed to the Figma plugin (figma-plugin/).

    The plugin can only draw icons the plan names, so the plan is where a
    fabricated R-ICO id would enter the figure. `--online` closes that hole
    completely by confirming every id resolves to a real icon."""
    try:
        with open(args.plan, encoding="utf-8") as fh:
            plan = json.load(fh)
    except OSError as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}), file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(json.dumps({"ok": False, "file": args.plan,
                          "errors": [f"not valid JSON: {exc}"]}, indent=2))
        return 1

    errors, warnings = [], []
    if not isinstance(plan, dict):
        print(json.dumps({"ok": False, "errors": ["plan is not a JSON object"]}, indent=2))
        return 1

    pathway = plan.get("pathway") or {}
    if not pathway.get("stId"):
        errors.append("pathway.stId is required")
    elif not REGION_ST_ID_RE.match(pathway["stId"]):
        errors.append(f"pathway.stId {pathway['stId']!r} is not a valid ST_ID")

    canvas = plan.get("canvas") or {}
    cw = canvas.get("width", 1366)
    ch = canvas.get("height", 768)
    if (float(cw), float(ch)) not in VALID_CANVASES:
        errors.append(f"canvas {cw}x{ch}; expected 1366x768 or 1396x798")

    subs = plan.get("subpathways") or []
    if len(subs) < 2:
        errors.append(f"{len(subs)} subpathway(s); an EHLD needs two or more active regions")

    # Every icon reference in the plan, tagged with where it came from, so an
    # error names the entity the curator recognises rather than a bare id.
    placements = [("compartment", c) for c in (plan.get("compartments") or [])]
    seen_st = set()
    for sub in subs:
        st = sub.get("stId")
        if not st or not REGION_ST_ID_RE.match(st):
            errors.append(f"subpathway stId {st!r} is not a valid ST_ID")
        elif st in seen_st:
            errors.append(f"duplicate subpathway stId {st}")
        else:
            seen_st.add(st)
        if not sub.get("label"):
            warnings.append(f"{st}: no label; the box will fall back to the ST_ID")
        for ent in sub.get("entities") or []:
            placements.append((st or "?", ent))

    for where, item in placements:
        ico = item.get("icon")
        # Report every problem with a placement in one pass. Short-circuiting on
        # a bad id would hide the others and cost the curator a fix-rerun cycle.
        if item.get("category") and item["category"] not in CATEGORIES:
            errors.append(f"{where}/{ico}: category {item['category']!r} is not "
                          f"one of {', '.join(CATEGORIES)}")
        if not ico or not ICO_ID_RE.match(str(ico)):
            errors.append(f"{where}: {ico!r} is not an R-ICO id "
                          "(resolve it with `map`/`search` — never write one by hand)")
            continue
        x, y = item.get("x", 0), item.get("y", 0)
        w = item.get("width") or 0
        h = item.get("height") or 0
        if not (0 <= x <= cw and 0 <= y <= ch):
            warnings.append(f"{where}/{ico}: origin ({x},{y}) is outside the "
                            f"{cw:g}x{ch:g} canvas")
        elif x + w > cw or y + h > ch:
            warnings.append(f"{where}/{ico}: extends past the canvas edge; the spec "
                            "says portray elements in full or fade them with a gradient")

    ids = sorted({str(i.get("icon")) for _, i in placements
                  if ICO_ID_RE.match(str(i.get("icon") or ""))})

    # The anti-fabrication check: confirm each id is a real icon.
    unresolved = []
    if args.online:
        for ico in ids:
            try:
                req = urllib.request.Request(_svg_url(ico), method="HEAD",
                                             headers={"User-Agent": UA})
                urllib.request.urlopen(req, timeout=TIMEOUT).close()
            except Exception as exc:  # noqa: BLE001
                unresolved.append(f"{ico} ({exc})")
        for u in unresolved:
            errors.append(f"icon does not exist in the library: {u}")

    report = {
        "file": os.path.abspath(args.plan),
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "info": {
            "pathway": pathway.get("stId"),
            "canvas": f"{cw:g}x{ch:g}",
            "subpathways": len(subs),
            "placements": len(placements),
            "distinctIcons": len(ids),
            "iconIds": ids,
            "verifiedOnline": bool(args.online) and not unresolved,
        },
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if errors else 0


def cmd_info(args):
    args.max = 1
    args.category = getattr(args, "category", None)
    args.species = getattr(args, "species", None)
    return cmd_search(args)


def main():
    p = argparse.ArgumentParser(description="Reactome Icon Library access for /curation-build-illustration")
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("map", help="deterministic accession -> icon lookup (bundled tables)")
    m.add_argument("accession", help="external id, e.g. CHEBI:16020, GO:0005884, Q99638, CPX-503")
    m.add_argument("--db", help="force a database table (e.g. UNIPROT, CHEBI, GO, CL, UBERON, COMPLEXPORTAL)")
    m.set_defaults(func=cmd_map)

    s = sub.add_parser("search", help="search the icon library")
    s.add_argument("term")
    s.add_argument("--category", choices=CATEGORIES, metavar="CAT",
                   help="filter to one category: " + ", ".join(CATEGORIES))
    s.add_argument("--species", help="species filter, e.g. 'Homo sapiens'")
    s.add_argument("--max", type=int, default=10)
    s.set_defaults(func=cmd_search)

    f = sub.add_parser("fetch", help="download an icon SVG/PNG by R-ICO id")
    f.add_argument("ico_id")
    f.add_argument("--outdir", default="./icons")
    f.add_argument("--png", action="store_true", help="also download the PNG")
    f.set_defaults(func=cmd_fetch)

    fe = sub.add_parser("fetch-ehld", help="download an existing EHLD SVG by pathway ST_ID (Mode A base diagram)")
    fe.add_argument("st_id", help="pathway stable id, e.g. R-HSA-109581")
    fe.add_argument("--outdir", default=".", help="directory to write <ST_ID>.svg into (default: cwd)")
    fe.set_defaults(func=cmd_fetch_ehld)

    pl = sub.add_parser("place", help="emit a positioned, id-namespaced <g> for an icon SVG")
    pl.add_argument("icon", help="path to a downloaded icon SVG (from `fetch`)")
    pl.add_argument("--x", type=float, required=True, help="canvas x of the icon's top-left")
    pl.add_argument("--y", type=float, required=True, help="canvas y of the icon's top-left")
    pl.add_argument("--prefix", required=True,
                    help="unique per-placement id prefix, e.g. p03- or add01-")
    size = pl.add_mutually_exclusive_group()
    size.add_argument("--scale", type=float, help="uniform scale factor (default 1)")
    size.add_argument("--width", type=float, help="scale so the icon is this many px wide")
    size.add_argument("--height", type=float, help="scale so the icon is this many px high")
    pl.add_argument("--class", dest="klass", choices=CATEGORIES, metavar="CAT",
                    help="category class to tag the placed group with, as production "
                         "EHLDs do (class=\"cell_type\", class=\"protein\", …)")
    pl.add_argument("--into", metavar="SVG",
                    help="check the prefix against the ids already in this SVG "
                         "(use the base EHLD in Mode A); exit 1 on collision")
    pl.add_argument("--indent", type=int, default=0, help="indent the snippet by N spaces")
    pl.set_defaults(func=cmd_place)

    v = sub.add_parser("validate", help="check a composed EHLD against the spec")
    v.add_argument("svg", help="path to the composed EHLD SVG")
    v.set_defaults(func=cmd_validate)

    cp = sub.add_parser("check-plan", help="verify a Figma-plugin placement plan")
    cp.add_argument("plan", help="path to the placement plan JSON")
    cp.add_argument("--online", action="store_true",
                    help="confirm every R-ICO id resolves to a real icon (network)")
    cp.set_defaults(func=cmd_check_plan)

    i = sub.add_parser("info", help="single best match + attribution")
    i.add_argument("term")
    i.add_argument("--category", choices=CATEGORIES, metavar="CAT")
    i.add_argument("--species")
    i.set_defaults(func=cmd_info)

    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
