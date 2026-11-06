#!/usr/bin/env python3
"""Compare a proposal's genes with WikiPathways, KEGG and GO, to find topology gaps.

/curation-gap-fill's optional comparison step (on by default). This script does the mechanical
part: it fetches each resource's genes for the topic and reports which of them the
proposal (including the existing Reactome pathways it links) does not contain. A
comparison agent then judges the candidates: does Reactome already have them, do
they close a chain gap, and is there human evidence?

Sources, all reachable without an account:
  WikiPathways  CC0. The JSON index of every pathway (one download, cached), then the GPML of each
                selected human pathway: GeneProduct/Protein data nodes and the
                number of interactions.
  KEGG          REST API (rest.kegg.jp), gene list per pathway. Academic use only;
                KEGG content is used as a COMPARISON and must never be copied into
                Reactome or the staging file. The output carries this notice.
  GO            Gene annotations per biological process (api.geneontology.org),
                human only. CC BY 4.0.

Input: a JSON file mapping each subpathway (or any grouping) to the gene symbols
the proposal contains there, e.g. from a gk_central query over all participants
of each subpathway's members:
    {"pw-lipolysis": ["ADRB1", "PNPLA2", ...], "pw-fed": [...]}

Usage:
    python3 compare_resources.py genes.json \\
        --wp-query adipo,lipolysis,thermogen,"brown fat","white fat" \\
        --kegg hsa04923,hsa04714 --go GO:0019433,GO:0019915,GO:1990845 \\
        -o agents/comparison_resources.json
    python3 compare_resources.py genes.json --wp WP4321,WP3634 --kegg hsa04923 ...

Output JSON: per resource and pathway or term, its genes, which are in the proposal and which
are absent; plus a candidate list of absent genes ranked by how many sources show
them. Stdlib only; downloads are cached in ~/.cache/reactome-curator-workflows/compare/.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

CACHE = os.path.expanduser("~/.cache/reactome-curator-workflows/compare")
UA = {"User-Agent": "reactome-curator-workflows/compare_resources"}
KEGG_NOTICE = ("KEGG content is used for comparison only (academic REST access) and must not be "
               "copied into Reactome or the staging file.")


def fetch(url, cache_name=None, timeout=60):
    if cache_name:
        path = os.path.join(CACHE, cache_name)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                return fh.read()
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        text = r.read().decode("utf-8", errors="replace")
    if cache_name:
        os.makedirs(os.path.dirname(os.path.join(CACHE, cache_name)), exist_ok=True)
        with open(os.path.join(CACHE, cache_name), "w", encoding="utf-8") as fh:
            fh.write(text)
    time.sleep(0.3)
    return text


# ── WikiPathways ────────────────────────────────────────────────────────────
def wp_index():
    d = json.loads(fetch("https://www.wikipathways.org/json/findPathwaysByText.json", "wp_index.json"))
    return d.get("pathwayInfo", d)


def wp_select(queries, ids):
    idx = wp_index()
    out = []
    for p in idx:
        if "Homo sapiens" not in str(p.get("species")):
            continue
        text = (str(p.get("name", "")) + " " + str(p.get("description", ""))).lower()
        if p.get("id") in ids or any(q.lower() in text for q in queries):
            out.append({"id": p["id"], "name": p.get("name"), "revision": p.get("revision")})
    return out


def wp_genes(wpid):
    gpml = fetch(f"https://www.wikipathways.org/wikipathways-assets/pathways/{wpid}/{wpid}.gpml",
                 f"wp/{wpid}.gpml")
    root = ET.fromstring(gpml.encode("utf-8"))
    ns = {"g": root.tag.split("}")[0].strip("{")} if root.tag.startswith("{") else {}
    q = (lambda t: f"g:{t}") if ns else (lambda t: t)
    genes = set()
    for dn in root.iter(f"{{{ns['g']}}}DataNode" if ns else "DataNode"):
        if dn.get("Type") in ("GeneProduct", "Protein", "Rna"):
            lab = (dn.get("TextLabel") or "").strip()
            if lab and re.fullmatch(r"[A-Za-z0-9\-]{2,15}", lab):
                genes.add(lab.upper())
    n_int = sum(1 for _ in root.iter(f"{{{ns['g']}}}Interaction" if ns else "Interaction"))
    return sorted(genes), n_int


# ── KEGG ────────────────────────────────────────────────────────────────────
def kegg_genes(pid):
    txt = fetch(f"https://rest.kegg.jp/get/{pid}", f"kegg/{pid}.txt")
    name = re.search(r"^NAME\s+(.+)$", txt, re.M)
    genes, inblock = [], False
    for line in txt.splitlines():
        if line.startswith("GENE"):
            inblock = True
            line = line[4:]
        elif inblock and line[:1] != " ":
            break
        if inblock:
            m = re.match(r"\s*\d+\s+([A-Za-z0-9\-]+);", line)
            if m:
                genes.append(m.group(1).upper())
    return (name.group(1).split(" - ")[0] if name else pid), sorted(set(genes))


# ── GO ──────────────────────────────────────────────────────────────────────
def go_genes(goid):
    url = ("https://api.geneontology.org/api/bioentity/function/"
           + urllib.parse.quote(goid) + "/genes?taxon=NCBITaxon%3A9606&rows=1000")
    d = json.loads(fetch(url, f"go/{goid.replace(':', '_')}.json"))
    genes = {a["subject"]["label"].upper() for a in d.get("associations", [])
             if re.fullmatch(r"[A-Za-z0-9\-]{2,15}", a["subject"].get("label", ""))}
    label = d.get("associations", [{}])[0].get("object", {}).get("label") if d.get("associations") else None
    return label, sorted(genes)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Compare proposal genes with WikiPathways, KEGG and GO.")
    ap.add_argument("genes_json")
    ap.add_argument("--wp-query", default="", help="comma-separated keywords to select human WikiPathways")
    ap.add_argument("--wp", default="", help="comma-separated WikiPathways IDs to include")
    ap.add_argument("--kegg", default="", help="comma-separated KEGG pathway IDs (e.g. hsa04923)")
    ap.add_argument("--go", default="", help="comma-separated GO BP IDs")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args(argv)

    with open(a.genes_json) as fh:
        groups = json.load(fh)
    proposal = {g.upper() for v in groups.values() for g in v}
    split = lambda s: [x.strip() for x in s.split(",") if x.strip()]
    res = {"proposal_gene_count": len(proposal), "kegg_notice": KEGG_NOTICE,
           "wikipathways": [], "kegg": [], "go": [], "errors": []}

    for p in wp_select(split(a.wp_query), set(split(a.wp))):
        try:
            genes, n_int = wp_genes(p["id"])
        except Exception as e:  # one bad file should not stop the comparison
            res["errors"].append(f"WikiPathways {p['id']}: {e}")
            continue
        res["wikipathways"].append({**p, "interactions": n_int, "genes": genes,
                                    "in_proposal": [g for g in genes if g in proposal],
                                    "absent": [g for g in genes if g not in proposal]})
    for pid in split(a.kegg):
        try:
            name, genes = kegg_genes(pid)
        except Exception as e:
            res["errors"].append(f"KEGG {pid}: {e}")
            continue
        res["kegg"].append({"id": pid, "name": name, "genes": genes,
                            "in_proposal": [g for g in genes if g in proposal],
                            "absent": [g for g in genes if g not in proposal]})
    for goid in split(a.go):
        try:
            label, genes = go_genes(goid)
        except Exception as e:
            res["errors"].append(f"GO {goid}: {e}")
            continue
        res["go"].append({"id": goid, "name": label, "genes": genes,
                          "in_proposal": [g for g in genes if g in proposal],
                          "absent": [g for g in genes if g not in proposal]})

    seen = {}
    for kind in ("wikipathways", "kegg", "go"):
        for entry in res[kind]:
            for g in entry["absent"]:
                seen.setdefault(g, set()).add(f"{kind}:{entry['id']}")
    res["candidates"] = sorted(
        ({"gene": g, "sources": sorted(s), "n_sources": len(s),
          "resource_types": sorted({x.split(':')[0] for x in s})} for g, s in seen.items()),
        key=lambda c: (-len(c["resource_types"]), -c["n_sources"], c["gene"]))
    with open(a.out, "w") as fh:
        json.dump(res, fh, indent=1)
    print(f"proposal genes {len(proposal)} | WikiPathways {len(res['wikipathways'])} | "
          f"KEGG {len(res['kegg'])} | GO {len(res['go'])} | candidates {len(res['candidates'])}"
          + (f" | errors {len(res['errors'])}" if res["errors"] else ""))
    multi = [c for c in res["candidates"] if len(c["resource_types"]) >= 2]
    print("absent from the proposal and shown by 2+ resource types:",
          ", ".join(c["gene"] for c in multi[:40]) or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
