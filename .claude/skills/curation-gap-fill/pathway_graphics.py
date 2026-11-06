#!/usr/bin/env python3
"""Overview graphics for a /curation-gap-fill pathway proposal (matplotlib).

Two figures, both drawn from the proposal spec so they cannot drift from it:

  render_hierarchy_map(spec, out_png)
      One page. The new top-level pathway, its subpathways as columns (plus any
      pathway linked directly under the top level), and their members as boxes.
      NEW reactions are green and dashed; linked existing pathways (▣) and
      reactions (●) are blue.

  render_chain(subpathway, out_png)
      The causal chain of one subpathway, from its `chain` field:
        {"lanes": [{"title": "...", "independent": false,
                    "steps": [{"id": "s1", "text": "...", "source": "R-HSA-…",
                               "kind": "shared|new|gap"}]}],
         "regulators": [{"at": "s5", "text": "G0S2 ⊣", "sign": "neg|pos"}],
         "questions":  [{"at": "s4", "q": "Q2", "text": "move E1/E2 into …"}],
         "context":    ["NR1H2 & NR1H3 … (R-HSA-9031528)", "…"]}
      Steps in a lane are joined by arrows unless the lane is `independent`
      (separate receptor events with no chain between them). A `gap` step is
      drawn red and dashed. Regulators hang below their step. Open questions are
      pinned above their step.

Returns the PNG path, or None when matplotlib is missing (the report then falls
back to text).
"""
import textwrap

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
except Exception:  # pragma: no cover - optional dependency
    plt = None

NAVY = "#1F3864"
NEW_FILL, NEW_EDGE = "#E2EFD9", "#38761D"
SH_FILL, SH_EDGE = "#DEEAF6", "#2E5F8A"
GAP_FILL, GAP_EDGE = "#FCE4E4", "#C00000"
Q_COLOR = "#B36B00"


def _box(ax, x, y, w, h, text, fill, edge, dashed=False, size=7.0, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=fill, ec=edge, lw=1.3, ls="--" if dashed else "-"))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size,
            fontweight="bold" if bold else "normal")


def render_hierarchy_map(spec, out_png):
    if plt is None:
        return None
    top = spec["hierarchy"][0]
    cols = top.get("children", [])
    if not cols:
        return None
    def _col_h(c):
        tot = 0.0
        for k in c.get("children", []):
            t = textwrap.fill(" ".join(k["name"].split()), 28)
            lines = t.count("\n") + (2 if k.get("st_id") else 1)
            tot += 0.3 + 0.15 * (lines - 1) + 0.07
        return tot
    height = max(5.0, 3.0 + max(_col_h(c) for c in cols))
    fig, ax = plt.subplots(figsize=(16, height))
    ax.axis("off")
    colw = 16 / len(cols)
    ax.set_xlim(0, 16)
    ax.set_ylim(-1.2, height)
    parent = ", ".join(p.get("name", "") for p in spec.get("proposed_pathway", {}).get("parents", []))
    _box(ax, 4.5, height - 1.0, 7, 0.8,
         f"{top['name']}\nNEW pathway" + (f", under {parent}" if parent else ""),
         "#C9D7EE", NAVY, size=10, bold=True)
    for i, col in enumerate(cols):
        x, w = i * colw + 0.12, colw - 0.24
        shared = (col.get("status") or "").upper() == "SHARED"
        label = textwrap.fill(col["name"], 24) + ("\nlinked pathway" if shared else "\nNEW subpathway")
        ytop = height - 2.55
        _box(ax, x, ytop, w, 1.1, label, SH_FILL if shared else "#E4ECF7",
             SH_EDGE if shared else NAVY, size=7.8, bold=True)
        ax.plot([x + w / 2, 8], [ytop + 1.1, height - 1.0], color="#999", lw=0.8)
        y = ytop - 0.1
        for k in col.get("children", []):
            new = (k.get("status") or "").upper() == "NEW"
            pw = k.get("kind") == "Pathway"
            t = ("▣ " if pw else "● ") + textwrap.fill(" ".join(k["name"].split()), 28)
            if k.get("st_id"):
                t += f"\n{k['st_id']}"
            h = 0.3 + 0.15 * t.count("\n")
            y -= h + 0.07
            _box(ax, x + 0.08, y, w - 0.16, h, t,
                 NEW_FILL if new else (SH_FILL if pw else "#FFFFFF"),
                 NEW_EDGE if new else SH_EDGE, dashed=new, size=6.0)
    ax.text(0.1, -1.1, "Green dashed = NEW reaction proposed here   ▣ linked existing pathway   "
            "● linked existing reaction", fontsize=8, color="#444")
    plt.savefig(out_png, dpi=170, bbox_inches="tight")
    plt.close(fig)
    return out_png


def render_chain(sub, out_png):
    if plt is None:
        return None
    chain = sub.get("chain") or {}
    lanes = chain.get("lanes") or []
    if not lanes:
        return None
    maxsteps = max(len(l["steps"]) for l in lanes)
    w, gap = 2.15, 0.25
    width = max(10.0, 0.4 + maxsteps * (w + gap))
    has_regs = {r["at"] for r in chain.get("regulators", [])}
    lane_hs = [3.3 if any(st["id"] in has_regs for st in l["steps"]) else 2.45 for l in lanes]
    height = 0.9 + sum(lane_hs) + (0.5 if chain.get("context") else 0)
    fig, ax = plt.subplots(figsize=(width, height))
    ax.axis("off")
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    pos = {}
    regs = {}
    for r in chain.get("regulators", []):
        regs.setdefault(r["at"], []).append(r)
    qs = {}
    for q in chain.get("questions", []):
        qs.setdefault(q["at"], []).append(q)
    acc = 0.0
    for li, lane in enumerate(lanes):
        lane_h = lane_hs[li]
        acc += lane_h
        base = height - 0.6 - acc
        ybox, hbox = base + (1.05 if lane_h > 3 else 0.2), 1.55
        ax.text(0.1, base + lane_h - 0.25, lane.get("title", ""), fontsize=8.5, fontweight="bold", color=NAVY)
        for si, st in enumerate(lane["steps"]):
            x = 0.2 + si * (w + gap)
            kind = st.get("kind", "shared")
            fill, edge, dashed = {"new": (NEW_FILL, NEW_EDGE, True), "gap": (GAP_FILL, GAP_EDGE, True)}.get(
                kind, (SH_FILL, SH_EDGE, False))
            body = "\n".join(textwrap.fill(line, 24) for line in st["text"].split("\n"))
            if st.get("source"):
                body += "\n\n" + textwrap.fill(st["source"], 26)
            _box(ax, x, ybox, w, hbox, body, fill, edge, dashed=dashed, size=6.4)
            pos[st["id"]] = (x, ybox, hbox)
            if si and not lane.get("independent"):
                ax.annotate("", xy=(x, ybox + hbox / 2), xytext=(x - gap, ybox + hbox / 2),
                            arrowprops=dict(arrowstyle="-|>", color="#333", lw=1.1))
            for k, r in enumerate(regs.get(st["id"], [])):
                neg = r.get("sign", "neg") == "neg"
                rx = x + 0.12 + k * 0.1
                _box(ax, rx, base + 0.1, w - 0.24, 0.6, textwrap.fill(r["text"], 26),
                     "#FCE4E4" if neg else "#E2EFD9", "#C00000" if neg else NEW_EDGE, size=6.0)
                ax.annotate("", xy=(x + w / 2, ybox), xytext=(x + w / 2, base + 0.7),
                            arrowprops=dict(arrowstyle="-[" if neg else "-|>",
                                            color="#C00000" if neg else NEW_EDGE, lw=1.1))
            for k, q in enumerate(qs.get(st["id"], [])):
                ax.text(x + 0.03, ybox + hbox + 0.08 + 0.33 * k,
                        textwrap.fill(f"◆ {q['q']}: {q['text']}", 34), fontsize=6.0, color=Q_COLOR, va="bottom")
    if chain.get("context"):
        ax.text(0.1, 0.12, "Also linked here: " + "; ".join(chain["context"]), fontsize=7, color="#444")
    ax.text(width - 0.1, height - 0.25,
            "green dashed = NEW   blue = existing (linked)   red dashed = gap   ◆ open decision",
            fontsize=6.8, color="#444", ha="right")
    plt.savefig(out_png, dpi=170, bbox_inches="tight")
    plt.close(fig)
    return out_png
