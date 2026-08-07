// Reactome EHLD Builder — Figma plugin main thread.
//
// Companion to the /curation-build-illustration skill. This file NEVER touches
// the network: all fetching happens in ui.html (the plugin iframe), which posts
// already-downloaded icon SVG text over to us. That split is deliberate — it
// keeps every network call in one auditable place and matches Figma's sandbox,
// where the scene thread has no fetch.
//
// The contract with the skill: this plugin only ever PLACES icons that the
// curator already approved in the Phase 1 Icon Map. It cannot invent an icon,
// because it has no search of its own on this side — an R-ICO id arrives in the
// plan or it does not get drawn.

const CANVAS_W = 1366;
const CANVAS_H = 768;

// Spec colours (EHLD_Specs_and_Guidelines.pdf), as Figma 0..1 RGB.
const LABEL_FILL = { r: 15 / 255, g: 130 / 255, b: 188 / 255 };   // #0F82BC
const ANALINFO_FILL = { r: 198 / 255, g: 198 / 255, b: 198 / 255 }; // #C6C6C6
const WHITE = { r: 1, g: 1, b: 1 };

const LABEL_MIN_W = 170;
const LABEL_H_1LINE = 30;
const LABEL_H_2LINE = 43;
const ANALINFO_H = 20;
const CORNER_RADIUS = 8;

// Production EHLDs use 0.01, not 0: a fully transparent group can be dropped
// from hit-testing, which would disable the analysis overlay this box exists to
// receive. See SKILL.md and EHLD_layout_reference.md §7.
const ANALINFO_OPACITY = 0.01;

const ST_ID_RE = /^(R-[A-Z]{3}-\d+|R-HSA-PLACEHOLDER-\d+)$/;
const ICO_ID_RE = /^R-ICO-\d+$/;

figma.showUI(__html__, { width: 420, height: 620, themeColors: true });

// ---------------------------------------------------------------------------
// Fonts
// ---------------------------------------------------------------------------

// The spec calls for Arial Bold. Arial is a system font, so it is present in
// the Figma desktop app on macOS/Windows but usually NOT in the browser editor
// (which needs the Figma font helper). Fall back to Inter rather than failing
// the whole build, and tell the curator — the exported label text is still real
// editable <text>, only the family differs, and the family is trivially fixed
// later. Silently substituting would be worse: they would ship a non-spec font.
let FONT = { family: "Arial", style: "Bold" };
let fontFallbackUsed = false;

async function loadFonts() {
  const candidates = [
    { family: "Arial", style: "Bold" },
    { family: "Helvetica", style: "Bold" },
    { family: "Inter", style: "Bold" },
  ];
  for (const font of candidates) {
    try {
      await figma.loadFontAsync(font);
      FONT = font;
      fontFallbackUsed = font.family !== "Arial";
      return;
    } catch (e) {
      // try the next family
    }
  }
  throw new Error("could not load any bold font (tried Arial, Helvetica, Inter)");
}

// ---------------------------------------------------------------------------
// Small builders
// ---------------------------------------------------------------------------

function makeRect(name, x, y, w, h, fill) {
  const rect = figma.createRectangle();
  rect.name = name;
  rect.x = x;
  rect.y = y;
  rect.resize(w, h);
  rect.cornerRadius = CORNER_RADIUS;
  rect.fills = [{ type: "SOLID", color: fill }];
  rect.strokes = [];
  return rect;
}

function makeText(content, size, x, y, w) {
  const text = figma.createText();
  text.fontName = FONT;
  text.characters = content;
  text.fontSize = size;
  text.fills = [{ type: "SOLID", color: WHITE }];
  text.textAlignHorizontal = "CENTER";
  text.textAlignVertical = "CENTER";
  text.textAutoResize = "NONE";
  text.resize(w, size * 1.6);
  text.x = x;
  text.y = y;
  return text;
}

// Spell Greek/Unicode out — the spec forbids the symbols in EHLD text.
const GREEK = {
  "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta",
  "ε": "epsilon", "ζ": "zeta", "κ": "kappa", "λ": "lambda",
  "μ": "mu", "σ": "sigma", "ω": "omega",
};

function sanitizeLabel(raw) {
  let out = String(raw == null ? "" : raw);
  for (const ch of Object.keys(GREEK)) {
    out = out.split(ch).join(GREEK[ch]);
  }
  // Pathway/subpathway labels are UPPERCASE per spec.
  return out.toUpperCase();
}

// ---------------------------------------------------------------------------
// Icon placement
// ---------------------------------------------------------------------------

// Turn one downloaded icon SVG into a positioned, correctly-named Figma node.
// Naming matters: on export with svgIdAttribute the layer name becomes the SVG
// id, which is how R-ICO provenance survives the round trip.
function placeIcon(svgText, spec) {
  const node = figma.createNodeFromSvg(svgText);
  node.name = spec.icon;

  const targetW = spec.width || null;
  const targetH = spec.height || null;
  let scale = 1;
  if (targetW && node.width) scale = targetW / node.width;
  else if (targetH && node.height) scale = targetH / node.height;
  else if (spec.scale) scale = spec.scale;

  // rescale() scales the frame AND its children; resize() would stretch the
  // frame while leaving the vector art at its original size.
  if (scale > 0 && Math.abs(scale - 1) > 1e-6) node.rescale(scale);

  node.x = spec.x || 0;
  node.y = spec.y || 0;
  return node;
}

// ---------------------------------------------------------------------------
// Subpathway machinery: REGION- ⊃ (icons, ANALINFO, OVERLAY- ⊃ label box)
// ---------------------------------------------------------------------------

function buildSubpathway(sub, icons, warnings) {
  const members = [];

  for (const ent of sub.entities || []) {
    const svg = icons[ent.icon];
    if (!svg) {
      warnings.push(
        `${sub.stId}: no downloaded SVG for ${ent.icon} (${ent.name || "?"}) — skipped, not substituted`
      );
      continue;
    }
    try {
      members.push(placeIcon(svg, ent));
    } catch (e) {
      warnings.push(`${sub.stId}: could not place ${ent.icon}: ${e.message}`);
    }
  }

  const label = sanitizeLabel(sub.label || sub.stId);
  const pos = sub.labelPos || { x: 40, y: CANVAS_H - 80 };
  // Two-line labels get the taller box, per spec.
  const twoLine = label.indexOf("\n") >= 0 || label.length > 34;
  const labelH = twoLine ? LABEL_H_2LINE : LABEL_H_1LINE;
  const labelW = Math.max(LABEL_MIN_W, Math.ceil(label.length * 7.2) + 24);

  // OVERLAY- holds the label box ONLY: it is the analysis-overlayable group and
  // must never contain arrows or entity art.
  const labelRect = makeRect("PATHWAY_LABEL", pos.x, pos.y, labelW, labelH, LABEL_FILL);
  const labelText = makeText(label, 12, pos.x, pos.y + (labelH - 12 * 1.6) / 2, labelW);
  const overlay = figma.group([labelRect, labelText], figma.currentPage);
  overlay.name = `OVERLAY-${sub.stId}`;

  // ANALINFO sits beside its label on the side opposite the content. Content is
  // above the label in the common bottom-label layout, so put it below.
  const analRect = makeRect("ANALINFO_BOX", pos.x, pos.y + labelH + 4, labelW, ANALINFO_H, ANALINFO_FILL);
  const analText = makeText("XXX/YYY", 9, pos.x, pos.y + labelH + 4 + (ANALINFO_H - 9 * 1.6) / 2, labelW);
  const analinfo = figma.group([analRect, analText], figma.currentPage);
  analinfo.name = "ANALINFO";
  analinfo.opacity = ANALINFO_OPACITY;

  const region = figma.group([...members, analinfo, overlay], figma.currentPage);
  region.name = `REGION-${sub.stId}`;
  return region;
}

// ---------------------------------------------------------------------------
// Plan validation (mirrors reactome_icons.py check-plan)
// ---------------------------------------------------------------------------

function validatePlan(plan) {
  const errors = [];
  if (!plan || typeof plan !== "object") return ["plan is not a JSON object"];
  if (!plan.pathway || !plan.pathway.stId) {
    errors.push("plan.pathway.stId is required");
  } else if (!ST_ID_RE.test(plan.pathway.stId)) {
    errors.push(`plan.pathway.stId ${plan.pathway.stId} is not a valid ST_ID`);
  }

  const subs = plan.subpathways || [];
  if (subs.length < 2) {
    errors.push(
      `plan has ${subs.length} subpathway(s); an EHLD needs two or more active regions`
    );
  }
  const seen = new Set();
  for (const sub of subs) {
    if (!sub.stId || !ST_ID_RE.test(sub.stId)) {
      errors.push(`subpathway stId ${sub.stId} is not a valid ST_ID`);
    } else if (seen.has(sub.stId)) {
      errors.push(`duplicate subpathway stId ${sub.stId}`);
    } else {
      seen.add(sub.stId);
    }
    for (const ent of sub.entities || []) {
      if (!ICO_ID_RE.test(ent.icon || "")) {
        errors.push(`${sub.stId}: ${JSON.stringify(ent.icon)} is not an R-ICO id`);
      }
    }
  }
  for (const c of plan.compartments || []) {
    if (!ICO_ID_RE.test(c.icon || "")) {
      errors.push(`compartment ${JSON.stringify(c.icon)} is not an R-ICO id`);
    }
  }
  return errors;
}

// ---------------------------------------------------------------------------
// Build
// ---------------------------------------------------------------------------

async function build(plan, icons) {
  const errors = validatePlan(plan);
  if (errors.length) return { ok: false, errors };

  await loadFonts();
  const warnings = [];
  if (fontFallbackUsed) {
    warnings.push(
      `Arial Bold is unavailable here, so labels use ${FONT.family} ${FONT.style}. ` +
      `The spec requires Arial Bold — switch the font before final export ` +
      `(Figma desktop on macOS/Windows has Arial; the browser editor needs the font helper).`
    );
  }

  const frame = figma.createFrame();
  frame.name = plan.pathway.stId;
  frame.resize(plan.canvas && plan.canvas.width || CANVAS_W,
               plan.canvas && plan.canvas.height || CANVAS_H);
  // No full-canvas background: the spec says Reactome renders EHLDs in blank
  // zoomable space. A transparent frame is the closest Figma equivalent.
  frame.fills = [];
  frame.clipsContent = false;
  frame.x = 0;
  frame.y = 0;

  // Back-to-front. appendChild puts a node on TOP, so emit in stacking order:
  // compartments first, then the subpathway regions that sit over them.
  const compartments = [];
  for (const c of plan.compartments || []) {
    const svg = icons[c.icon];
    if (!svg) {
      warnings.push(`compartment ${c.icon} (${c.name || "?"}) not downloaded — skipped`);
      continue;
    }
    try {
      compartments.push(placeIcon(svg, c));
    } catch (e) {
      warnings.push(`could not place compartment ${c.icon}: ${e.message}`);
    }
  }
  if (compartments.length) {
    const layer = figma.group(compartments, figma.currentPage);
    layer.name = "CELL";
    frame.appendChild(layer);
  }

  const regions = [];
  for (const sub of plan.subpathways || []) {
    const region = buildSubpathway(sub, icons, warnings);
    frame.appendChild(region);
    regions.push(region.name);
  }

  // Standard furniture the spec/corpus expects. Created empty for the curator
  // to fill — an empty named group is honest; a fabricated logo would not be.
  for (const name of ["ARROWS", "TEXT"]) {
    const marker = figma.createFrame();
    marker.name = name;
    marker.resize(1, 1);
    marker.fills = [];
    marker.x = 0;
    marker.y = 0;
    frame.appendChild(marker);
  }
  warnings.push(
    "Empty ARROWS and TEXT layers were created for you to draw into. The LOGO " +
    "(50% opacity) and the ICON analysis legend are not generated — add them from " +
    "the Reactome template before ingestion."
  );

  figma.currentPage.appendChild(frame);
  figma.viewport.scrollAndZoomIntoView([frame]);

  return {
    ok: true,
    errors: [],
    warnings,
    summary: {
      frame: frame.name,
      compartments: compartments.length,
      regions: regions.length,
      subpathwayStIds: regions.map((r) => r.replace("REGION-", "")),
      font: `${FONT.family} ${FONT.style}`,
    },
  };
}

// ---------------------------------------------------------------------------
// Export
// ---------------------------------------------------------------------------

async function exportSelection() {
  // Prefer an explicitly selected frame; otherwise the single top-level frame.
  let target = figma.currentPage.selection.find((n) => n.type === "FRAME");
  if (!target) {
    const frames = figma.currentPage.children.filter((n) => n.type === "FRAME");
    if (frames.length === 1) target = frames[0];
  }
  if (!target) {
    return { ok: false, errors: ["select the EHLD frame you want to export"] };
  }

  // These four settings are the Figma equivalent of the Illustrator export
  // settings in SKILL.md, and two of them are load-bearing:
  //   svgIdAttribute:  layer names become SVG ids — this is what preserves
  //                    REGION-/OVERLAY-/ANALINFO, without which the EHLD is
  //                    not interactive in the Pathway Browser.
  //   svgOutlineText:  MUST be false. Figma outlines text by default, and the
  //                    spec explicitly forbids converting text to shapes.
  const bytes = await target.exportAsync({
    format: "SVG",
    svgIdAttribute: true,
    svgOutlineText: false,
    svgSimplifyStroke: false,
  });

  return {
    ok: true,
    errors: [],
    filename: `${target.name}_figma.svg`,
    bytes: Array.from(bytes),
    note:
      "Run `python3 reactome_icons.py validate <file>` on this export before " +
      "handing it to a curator.",
  };
}

// ---------------------------------------------------------------------------
// Message routing
// ---------------------------------------------------------------------------

figma.ui.onmessage = async (msg) => {
  try {
    if (msg.type === "build") {
      const result = await build(msg.plan, msg.icons || {});
      figma.ui.postMessage({ type: "build-result", result });
      if (result.ok) figma.notify(`Built ${result.summary.regions} subpathway region(s)`);
    } else if (msg.type === "validate-plan") {
      figma.ui.postMessage({ type: "plan-errors", errors: validatePlan(msg.plan) });
    } else if (msg.type === "insert-icon") {
      // Single-icon insert from the browse panel.
      await loadFonts();
      const node = placeIcon(msg.svg, msg.spec);
      figma.currentPage.appendChild(node);
      figma.currentPage.selection = [node];
      figma.viewport.scrollAndZoomIntoView([node]);
      figma.notify(`Inserted ${msg.spec.icon}`);
      figma.ui.postMessage({ type: "inserted", icon: msg.spec.icon });
    } else if (msg.type === "export") {
      const result = await exportSelection();
      figma.ui.postMessage({ type: "export-result", result });
    } else if (msg.type === "close") {
      figma.closePlugin();
    }
  } catch (e) {
    figma.ui.postMessage({
      type: "build-result",
      result: { ok: false, errors: [String(e && e.message ? e.message : e)] },
    });
    figma.notify(`Error: ${e && e.message ? e.message : e}`, { error: true });
  }
};
