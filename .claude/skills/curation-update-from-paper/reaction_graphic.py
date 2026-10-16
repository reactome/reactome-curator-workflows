#!/usr/bin/env python3
"""Render a compact reaction anatomy diagram for one proposed event.

One PNG per ReactionLikeEvent, laid out the way a curator reads a reaction:

      [ preceding event ]
               |
          [ catalyst ]
               v
    inputs -> (REACTION) -> outputs
               ^
         [ regulators ]
               |
      [ following event ]

Entities are colour-coded by role, and an entity with no ST_ID is drawn with a
dashed border and a NEW tag, so what the paper adds is visible at a glance
against what is being reused. The compartment of each participant is printed
under its name, which is what "where does this reaction sit" usually means in
practice.

Used by build_update_doc.py. Importable (`render_event_graphic`) or runnable as
a CLI for a single spec, which is handy when tuning the layout:

    python3 reaction_graphic.py spec.json --out-dir /tmp/figs

Requires matplotlib (pinned in the repo's requirements.txt).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import textwrap
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    import matplotlib
    matplotlib.use("Agg")  # no display on a curator's laptop, and none needed
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
except ImportError:  # pragma: no cover - import guard
    sys.stderr.write(
        "error: matplotlib is not installed. Install it with:\n"
        "    pip3 install --user matplotlib\n"
    )
    raise SystemExit(2)


# ──────────────────────────────────────────────────────────────────────────────
# Palette - deliberately the same hues as build_update_doc.py's table shading
# ──────────────────────────────────────────────────────────────────────────────

ROLE_STYLE: Dict[str, Dict[str, str]] = {
    "input":     {"fill": "#D9E2F3", "edge": "#2F5496"},
    "output":    {"fill": "#E2EFD9", "edge": "#538135"},
    "catalyst":  {"fill": "#FFF2CC", "edge": "#BF8F00"},
    "regulator": {"fill": "#FBE4D5", "edge": "#C55A11"},
    "event":     {"fill": "#F2F2F2", "edge": "#808080"},
}
REACTION_FILL = "#FFFFFF"
REACTION_EDGE = "#1F3864"   # navy, matching the review-internal H1 colour
NEW_TAG_COLOR = "#C00000"
ARROW_COLOR = "#404040"
COMPARTMENT_COLOR = "#595959"

# A value like "(none)" or "(none - conformational change)" means "no
# participant", not "a participant named none". Treat it as empty.
_PLACEHOLDER = re.compile(
    r"^\s*\(?\s*(none|n/?a|not applicable|not noted|unknown)\b", re.IGNORECASE
)

_ST_ID = re.compile(r"\b(R-[A-Z]{3}-\d+)\b")
_COMPARTMENT = re.compile(r"\[([^\]]+)\]")

# Spec entity strings often carry a trailing rationale after an em dash, e.g.
# "ARP2/3 complex - positive regulator, inferred from ...". The diagram shows
# the participant; the rationale stays in the table underneath it.
_RATIONALE = re.compile(r"\s+[—–-]{1,2}\s+(?=\S)")
_POSITIVE = re.compile(r"\bpositive(ly)?\s+regulat", re.IGNORECASE)
_NEGATIVE = re.compile(r"\bnegative(ly)?\s+regulat|\binhibit", re.IGNORECASE)


# ──────────────────────────────────────────────────────────────────────────────
# Parsing
# ──────────────────────────────────────────────────────────────────────────────


def is_placeholder(text: Any) -> bool:
    """True for blank values and for curator shorthand meaning 'nothing here'."""
    if text is None:
        return True
    s = str(text).strip()
    return not s or bool(_PLACEHOLDER.match(s))


def parse_entity(text: Any) -> Optional[Dict[str, str]]:
    """Split "Name [compartment] (R-HSA-123)" into its parts.

    Returns None for placeholders. `st_id` is "" when the entity is new, which
    is what drives the dashed NEW styling.
    """
    if is_placeholder(text):
        return None
    s = str(text).strip()

    st_match = _ST_ID.search(s)
    st_id = st_match.group(1) if st_match else ""
    if st_match:
        # Drop the "(R-HSA-123)" wrapper, not just the bare id.
        s = re.sub(r"\(\s*" + re.escape(st_id) + r"\s*\)", "", s)
        s = s.replace(st_id, "")

    comp_match = _COMPARTMENT.search(s)
    compartment = comp_match.group(1).strip() if comp_match else ""
    if comp_match:
        s = s[: comp_match.start()] + s[comp_match.end():]

    # Split "<entity> - <rationale>" so only the entity is drawn. The sign is
    # read from the rationale before discarding it.
    sign = ""
    parts = _RATIONALE.split(s, maxsplit=1)
    tail = parts[1] if len(parts) > 1 else ""
    if _NEGATIVE.search(tail) or _NEGATIVE.search(s):
        sign = "−"
    elif _POSITIVE.search(tail) or _POSITIVE.search(s):
        sign = "+"
    if len(parts) > 1 and len(parts[0].strip()) >= 3:
        s = parts[0]

    name = re.sub(r"\s{2,}", " ", s).strip(" ,;")
    return {
        "name": name,
        "compartment": compartment,
        "st_id": st_id,
        "sign": sign,
        "note": re.sub(r"\s{2,}", " ", tail).strip(" ,;"),
    }


def parse_entities(values: Any) -> List[Dict[str, str]]:
    if values is None:
        return []
    if isinstance(values, (list, tuple)):
        items = list(values)
    else:
        items = [values]
    out = []
    for v in items:
        parsed = parse_entity(v)
        if parsed:
            out.append(parsed)
    return out


def event_ref_label(text: Any) -> str:
    """Short display form for a preceding/following event reference."""
    if is_placeholder(text):
        return ""
    return re.sub(r"\s{2,}", " ", str(text).strip())


def derive_following(events: Sequence[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Invert `preceding_event` into a label -> [following labels] map.

    Only matches references that name another event's label (e.g. "E4"), which
    is how a within-proposal chain is written. References to existing database
    events are left alone - they are upstream of the proposal, not inside it.
    """
    by_label = {}
    for e in events:
        label = str(e.get("label") or "").strip()
        if label:
            by_label.setdefault(label, [])

    for e in events:
        label = str(e.get("label") or "").strip()
        prec = e.get("preceding_event")
        if is_placeholder(prec) or not label:
            continue
        prec_s = str(prec).strip()
        for other in by_label:
            # Exact label, or the label leading the string ("E4 - some name").
            if prec_s == other or re.match(
                r"^" + re.escape(other) + r"\b", prec_s
            ):
                by_label[other].append(label)
                break
    return by_label


# ──────────────────────────────────────────────────────────────────────────────
# Drawing primitives
# ──────────────────────────────────────────────────────────────────────────────


def _wrap(text: str, width: int) -> str:
    return "\n".join(textwrap.wrap(text, width=width)) or text


def _box(ax, x, y, w, h, *, fill, edge, dashed=False, lw=1.2, radius=0.6):
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0,rounding_size=%s" % radius,
        linewidth=lw,
        edgecolor=edge,
        facecolor=fill,
        linestyle=(0, (4, 2)) if dashed else "solid",
        mutation_aspect=1.0,
        zorder=2,
    )
    ax.add_patch(patch)
    return patch


def _entity_lines(entity, width: int) -> List[str]:
    """Wrapped name lines for one entity, with the regulator sign inline."""
    name = entity["name"]
    if entity.get("sign"):
        name = "%s %s" % (entity["sign"], name)
    lines = textwrap.wrap(name, width=width) or [name]
    # A diagram box is not the place for an essay; the table carries the rest.
    if len(lines) > MAX_NAME_LINES:
        lines = lines[:MAX_NAME_LINES]
        lines[-1] = lines[-1].rstrip(" ,;") + "…"
    return lines


def _entity_height(entity, width: int) -> float:
    lines = _entity_lines(entity, width)
    h = BOX_PAD * 2 + len(lines) * LINE_H
    if entity["compartment"]:
        h += COMP_H
    if entity["st_id"] or True:   # every box carries a corner tag
        h += TAG_H
    return h


def _entity_box(ax, entity, x, y, w, h, role, *, name_width=26, fontsize=8.0):
    """Draw one participant: corner tag, name, optional compartment line."""
    style = ROLE_STYLE[role]
    is_new = not entity["st_id"]
    _box(ax, x, y, w, h, fill=style["fill"], edge=style["edge"], dashed=is_new)

    cx = x + w / 2.0
    lines = _entity_lines(entity, name_width)
    comp = entity["compartment"]

    # Lay the box out top-down: tag strip, name block, compartment strip.
    name_block_h = len(lines) * LINE_H
    name_top = y + h - BOX_PAD - TAG_H
    name_centre = name_top - name_block_h / 2.0

    ax.text(
        cx, name_centre, "\n".join(lines),
        ha="center", va="center", fontsize=fontsize, zorder=3,
        color="#1A1A1A", linespacing=1.25,
    )
    if comp:
        ax.text(
            cx, y + BOX_PAD + COMP_H / 2.0,
            "[%s]" % textwrap.shorten(comp, width=46, placeholder="…"),
            ha="center", va="center", fontsize=fontsize - 1.3,
            color=COMPARTMENT_COLOR, style="italic", zorder=3,
        )
    if is_new:
        ax.text(
            x + w - 0.5, y + h - 0.4, "NEW",
            ha="right", va="top", fontsize=fontsize - 2.0,
            color=NEW_TAG_COLOR, fontweight="bold", zorder=3,
        )
    else:
        ax.text(
            x + w - 0.5, y + h - 0.4, entity["st_id"],
            ha="right", va="top", fontsize=fontsize - 2.4,
            color=COMPARTMENT_COLOR, zorder=3,
        )


def _arrow(ax, start, end, *, style="-|>", color=ARROW_COLOR, lw=1.3,
           dashed=False, shrink=2.0):
    arrow = FancyArrowPatch(
        start, end,
        arrowstyle=style,
        mutation_scale=11,
        linewidth=lw,
        color=color,
        linestyle=(0, (3, 2)) if dashed else "solid",
        shrinkA=shrink, shrinkB=shrink,
        zorder=1,
    )
    ax.add_patch(arrow)
    return arrow


def _event_chip(ax, text, x, y, w, h, *, fontsize=7.6, label=""):
    """A single-line strip naming an adjacent event in the chain."""
    style = ROLE_STYLE["event"]
    _box(ax, x, y, w, h, fill=style["fill"], edge=style["edge"], lw=1.0,
         radius=0.4)
    if label:
        ax.text(
            x + 1.2, y + h / 2.0, label,
            ha="left", va="center", fontsize=fontsize - 1.4,
            color="#808080", fontweight="bold", zorder=3,
        )
    ax.text(
        x + w / 2.0, y + h / 2.0,
        textwrap.shorten(text, width=96, placeholder="…"),
        ha="center", va="center", fontsize=fontsize, color="#333333", zorder=3,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Main layout
# ──────────────────────────────────────────────────────────────────────────────

W = 100.0          # drawing units across
GAP = 2.0
COL_W = 32.0       # participant column width

# The reaction is a small node, as in a Reactome diagram - not a box, which
# reads as just another entity. Its name is already in the header, so the node
# only carries the short label.
RXN_MIN_W = 3.5
RXN_H = 3.75
RXN_FONT = 5.2

LINE_H = 3.3       # one wrapped line of entity name
COMP_H = 3.2       # the "[compartment]" strip
TAG_H = 2.6        # the NEW / ST_ID corner strip
BOX_PAD = 1.3
MAX_NAME_LINES = 3
NAME_CHARS = 30    # wrap width inside a participant box


def render_event_graphic(
    event: Dict[str, Any],
    out_path: str,
    following: Optional[Sequence[str]] = None,
    dpi: int = 220,
    preceding: Optional[str] = None,
) -> Optional[str]:
    """Render one event to `out_path`. Returns the path, or None if there is
    nothing worth drawing (no inputs and no outputs)."""
    inputs = parse_entities(event.get("inputs"))
    outputs = parse_entities(event.get("outputs"))
    catalysts = parse_entities(event.get("catalyst"))
    regulators = parse_entities(event.get("regulators"))

    if not inputs and not outputs:
        return None

    preceding = (preceding if preceding is not None
                 else event_ref_label(event.get("preceding_event")))
    following_label = ", ".join([f for f in (following or []) if f])

    label = str(event.get("label") or "").strip()
    name = str(event.get("name") or "").strip()
    etype = str(event.get("type") or "").strip()
    compartment = str(event.get("compartment") or "").strip()

    # ── vertical budget, driven by how much text each box actually holds ─────
    row_gap = 1.8
    chip_h = 5.2
    band = 4.2          # gap between stacked bands

    def column_height(entities):
        if not entities:
            return 0.0
        heights = [_entity_height(e, NAME_CHARS) for e in entities]
        return sum(heights) + row_gap * (len(heights) - 1)

    in_h = column_height(inputs)
    out_h = column_height(outputs)
    core_h = max(in_h, out_h, 12.0)

    def row_height(entities, each_w):
        if not entities:
            return 0.0
        chars = max(16, int(each_w * 1.05))
        return max(_entity_height(e, chars) for e in entities)

    cat_each = (min(W, len(catalysts) * COL_W + (len(catalysts) - 1) * GAP)
                - (len(catalysts) - 1) * GAP) / len(catalysts) if catalysts else 0
    reg_each = (min(W, len(regulators) * COL_W + (len(regulators) - 1) * GAP)
                - (len(regulators) - 1) * GAP) / len(regulators) if regulators else 0
    cat_h = row_height(catalysts, cat_each)
    reg_h = row_height(regulators, reg_each)

    y = 1.5
    y_following = None
    if following_label:
        y_following = y
        y += chip_h + band
    y_regulators = None
    if regulators:
        y_regulators = y
        y += reg_h + band
    y_core = y
    y += core_h + band
    y_catalyst = None
    if catalysts:
        y_catalyst = y
        y += cat_h + band
    y_preceding = None
    if preceding:
        y_preceding = y
        y += chip_h
    total_h = y + 8.0   # header band

    fig_w = 9.1
    fig_h = max(2.5, fig_w * (total_h / W))
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, total_h)
    ax.axis("off")

    # ── header ───────────────────────────────────────────────────────────────
    head_bits = [b for b in (label, name) if b]
    ax.text(
        0, total_h - 1.8, "  ".join(head_bits),
        ha="left", va="top", fontsize=9.2, fontweight="bold", color=REACTION_EDGE,
    )
    sub = " | ".join([b for b in (etype, compartment and "compartment: " + compartment) if b])
    if sub:
        ax.text(
            0, total_h - 5.6, sub,
            ha="left", va="top", fontsize=7.4, color=COMPARTMENT_COLOR,
        )

    x_in = 0.0
    node_label = label or "●"
    rxn_w = max(RXN_MIN_W, min(7.0, 1.5 + len(node_label) * 1.0))
    x_out = W - COL_W
    x_rxn = W / 2.0 - rxn_w / 2.0

    # ── reaction node ────────────────────────────────────────────────────────
    rxn_h = RXN_H
    rxn_y = y_core + (core_h - rxn_h) / 2.0
    _box(ax, x_rxn, rxn_y, rxn_w, rxn_h,
         fill=REACTION_FILL, edge=REACTION_EDGE, lw=1.3, radius=0.25)
    ax.text(
        x_rxn + rxn_w / 2.0, rxn_y + rxn_h / 2.0,
        node_label,
        ha="center", va="center", fontsize=RXN_FONT, fontweight="bold",
        color=REACTION_EDGE, zorder=3,
    )

    # ── inputs / outputs ─────────────────────────────────────────────────────
    def stack(entities, x, role):
        n = len(entities)
        if not n:
            return []
        heights = [_entity_height(e, NAME_CHARS) for e in entities]
        block_h = sum(heights) + row_gap * (n - 1)
        y0 = y_core + (core_h - block_h) / 2.0
        centres = []
        cursor = y0 + block_h
        for ent, h in zip(entities, heights):
            cursor -= h
            _entity_box(ax, ent, x, cursor, COL_W, h, role,
                        name_width=NAME_CHARS)
            centres.append(cursor + h / 2.0)
            cursor -= row_gap
        return centres

    in_centres = stack(inputs, x_in, "input")
    out_centres = stack(outputs, x_out, "output")

    for cy in in_centres:
        _arrow(ax, (x_in + COL_W, cy), (x_rxn, rxn_y + rxn_h / 2.0))
    for cy in out_centres:
        _arrow(ax, (x_rxn + rxn_w, rxn_y + rxn_h / 2.0), (x_out, cy))

    # ── catalyst above, regulators below ─────────────────────────────────────
    cx_rxn = x_rxn + rxn_w / 2.0

    def centred_row(entities, y0, role, h):
        """Centre a row on the node."""
        n = len(entities)
        if not n:
            return
        total_w = min(W, n * COL_W + (n - 1) * GAP)
        x0 = max(0.0, min(cx_rxn - total_w / 2.0, W - total_w))
        each = (total_w - (n - 1) * GAP) / n
        for i, ent in enumerate(entities):
            bx = x0 + i * (each + GAP)
            _entity_box(ax, ent, bx, y0, each, h, role,
                        name_width=max(16, int(each * 1.05)))

    effector_x = cx_rxn

    if catalysts:
        centred_row(catalysts, y_catalyst, "catalyst", cat_h)
        _arrow(ax, (effector_x, y_catalyst), (effector_x, rxn_y + rxn_h),
               dashed=True)
        ax.text(
            effector_x + 0.9, y_catalyst - band / 2.0, "catalyses",
            ha="left", va="center", fontsize=6.6, color=COMPARTMENT_COLOR,
            style="italic",
        )

    if regulators:
        centred_row(regulators, y_regulators, "regulator", reg_h)
        _arrow(ax, (effector_x, y_regulators + reg_h), (effector_x, rxn_y),
               dashed=True)
        ax.text(
            effector_x + 0.9, y_regulators + reg_h + band / 2.0, "regulates",
            ha="left", va="center", fontsize=6.6, color=COMPARTMENT_COLOR,
            style="italic",
        )

    # ── preceding / following chips ──────────────────────────────────────────
    # No connectors: the chips are captioned PRECEDED BY / FOLLOWED BY, which
    # says what they are. Arrows in this diagram belong to the reaction being
    # detailed and nothing else.
    if preceding:
        _event_chip(ax, preceding, 0, y_preceding, W, chip_h,
                    label="PRECEDED BY")

    if following_label:
        _event_chip(ax, following_label, 0, y_following, W, chip_h,
                    label="FOLLOWED BY")

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    fig.savefig(out_path, dpi=dpi, facecolor="white", bbox_inches="tight",
                pad_inches=0.04)
    plt.close(fig)
    return out_path


def render_all(spec: Dict[str, Any], out_dir: str, dpi: int = 220
               ) -> Dict[str, str]:
    """Render every event in a spec. Returns label -> png path."""
    events = [e for e in (spec.get("new_events") or []) if isinstance(e, dict)]
    following_map = derive_following(events)
    # "E7" alone tells a reader nothing; show "E7 - <name>" on the chip.
    names = {
        str(e.get("label") or "").strip(): str(e.get("name") or "").strip()
        for e in events
    }

    def describe(label: str) -> str:
        name = names.get(label, "")
        return "%s — %s" % (label, name) if name else label

    def describe_preceding(value: Any) -> str:
        """Expand a bare label reference ("E5") to "E5 - <name>".

        A preceding_event naming an existing database event is already written
        out in full, so it is passed through untouched.
        """
        text = event_ref_label(value)
        if not text:
            return ""
        for other, name in names.items():
            if other and name and (
                text == other or re.match(r"^" + re.escape(other) + r"\b", text)
            ):
                rest = text[len(other):].lstrip(" —-:")
                return describe(other) if not rest else text
        return text

    made: Dict[str, str] = {}
    for idx, event in enumerate(events, start=1):
        label = str(event.get("label") or "event%d" % idx).strip()
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", label) or "event%d" % idx
        path = os.path.join(out_dir, "reaction_%s.png" % safe)
        result = render_event_graphic(
            event, path,
            following=[describe(f) for f in following_map.get(label, [])],
            preceding=describe_preceding(event.get("preceding_event")),
            dpi=dpi,
        )
        if result:
            made[label] = result
    return made


# ──────────────────────────────────────────────────────────────────────────────
# Decision flowchart for the open-questions section
# ──────────────────────────────────────────────────────────────────────────────

DECISION_FILL = "#EAF1FB"
TERMINAL_FILL = "#E2EFD9"


def render_decision_flow(flow: Sequence[Dict[str, Any]], out_path: str,
                         dpi: int = 220) -> Optional[str]:
    """Draw a left-to-right decision chart from a declared flow.

    Node shape:
        {"id": "Q1", "text": "Structural decision",
         "answers": [{"label": "parallel", "to": "Q3"}]}
        {"id": "BUILD", "text": "Create instances", "terminal": true}

    Nothing is inferred - if the spec declares no flow, no chart is drawn. An
    invented decision order would be worse than none.
    """
    nodes = [n for n in (flow or []) if isinstance(n, dict) and n.get("id")]
    if len(nodes) < 2:
        return None

    by_id = {str(n["id"]): n for n in nodes}
    targets = {
        str(a.get("to"))
        for n in nodes for a in (n.get("answers") or []) if a.get("to")
    }
    roots = [str(n["id"]) for n in nodes if str(n["id"]) not in targets]
    if not roots:
        roots = [str(nodes[0]["id"])]

    # Layer by longest path from a root so an arrow always points rightwards.
    depth: Dict[str, int] = {r: 0 for r in roots}
    for _ in range(len(nodes)):
        for node in nodes:
            nid = str(node["id"])
            if nid not in depth:
                continue
            for answer in node.get("answers") or []:
                to = str(answer.get("to") or "")
                if to in by_id:
                    depth[to] = max(depth.get(to, 0), depth[nid] + 1)
    for node in nodes:
        depth.setdefault(str(node["id"]), 0)

    layers: Dict[int, List[str]] = {}
    for nid, d in sorted(depth.items(), key=lambda kv: (kv[1], kv[0])):
        layers.setdefault(d, []).append(nid)

    n_layers = max(layers) + 1
    max_rows = max(len(v) for v in layers.values())

    # Fit the columns to the page rather than letting them overlap: reserve a
    # real gap for the arrows first, then divide what is left.
    x_gap = 6.0
    box_w = (W - x_gap * (n_layers - 1)) / n_layers if n_layers > 1 else W
    box_w = max(box_w, 12.0)
    chars = max(12, int(box_w * 1.25))

    # Height follows the most-wrapped label, so no text escapes its box.
    worst = 1
    for node in nodes:
        worst = max(worst, len(textwrap.wrap(str(node.get("text") or ""), chars)))
    box_h = 6.5 + worst * 3.0
    y_gap = 5.0
    total_h = max_rows * box_h + (max_rows - 1) * y_gap + 4.0

    fig_w = 9.1
    fig = plt.figure(figsize=(fig_w, max(1.6, fig_w * (total_h / W))), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, total_h)
    ax.axis("off")

    centres: Dict[str, Tuple[float, float, float, float]] = {}
    for layer_idx in sorted(layers):
        column = layers[layer_idx]
        block_h = len(column) * box_h + (len(column) - 1) * y_gap
        y0 = (total_h - 3.0 - block_h) / 2.0 + 1.0
        x = layer_idx * (box_w + x_gap)
        for row_idx, nid in enumerate(column):
            y = y0 + (len(column) - 1 - row_idx) * (box_h + y_gap)
            node = by_id[nid]
            terminal = bool(node.get("terminal"))
            _box(ax, x, y, box_w, box_h,
                 fill=TERMINAL_FILL if terminal else DECISION_FILL,
                 edge="#538135" if terminal else REACTION_EDGE,
                 lw=1.5, radius=0.7)
            ax.text(
                x + box_w / 2.0, y + box_h - 2.2, nid,
                ha="center", va="center", fontsize=8.2, fontweight="bold",
                color="#538135" if terminal else REACTION_EDGE, zorder=3,
            )
            ax.text(
                x + box_w / 2.0, y + (box_h - 4.4) / 2.0,
                _wrap(str(node.get("text") or ""), chars),
                ha="center", va="center", fontsize=6.9, color="#1A1A1A",
                zorder=3, linespacing=1.3,
            )
            centres[nid] = (x, y, box_w, box_h)

    # Several answers can lead to the same node ("parallel" and "supersede"
    # both reach Q2). Draw one arrow and join the labels, or they overprint.
    merged: Dict[Tuple[str, str], List[str]] = {}
    for node in nodes:
        nid = str(node["id"])
        if nid not in centres:
            continue
        for answer in node.get("answers") or []:
            to = str(answer.get("to") or "")
            if to in centres:
                merged.setdefault((nid, to), []).append(
                    str(answer.get("label") or "")
                )

    for (src, dst), labels in merged.items():
        x, y, w, h = centres[src]
        tx, ty, tw, th = centres[dst]
        start = (x + w, y + h / 2.0)
        end = (tx, ty + th / 2.0)
        _arrow(ax, start, end, lw=1.1)

        text = " / ".join([l for l in labels if l])
        if not text:
            continue
        # Sit the label nearer the source so it clears the target box's text.
        t = 0.34
        mx = start[0] + (end[0] - start[0]) * t
        my = start[1] + (end[1] - start[1]) * t
        ax.text(
            mx, my + 0.9, textwrap.shorten(text, 30, placeholder="…"),
            ha="center", va="bottom", fontsize=6.3,
            color=COMPARTMENT_COLOR, style="italic", zorder=4,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white",
                      edgecolor="none", alpha=0.92),
        )

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    fig.savefig(out_path, dpi=dpi, facecolor="white", bbox_inches="tight",
                pad_inches=0.04)
    plt.close(fig)
    return out_path


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", help="curation update spec JSON")
    parser.add_argument("--out-dir", default="figs", help="where to write PNGs")
    parser.add_argument("--dpi", type=int, default=220)
    args = parser.parse_args(argv)

    with open(args.spec, "r", encoding="utf-8") as fh:
        spec = json.load(fh)
    made = render_all(spec, args.out_dir, dpi=args.dpi)
    for label, path in made.items():
        print("%-6s %s" % (label, path))
    if not made:
        print("no events with inputs/outputs to draw", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
