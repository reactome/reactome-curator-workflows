"""arrow_fit.py — shorten a Reactome library arrow WITHOUT scaling it.

Companion to /curation-build-illustration; see the "Arrow weight must match its
neighbours" rule in SKILL.md.

Uniformly scaling an arrow (place --scale/--width) shrinks its stroke-width too,
so a short arrow ends up visually lighter than its neighbours. Production EHLDs
never do that: every arrow in R-HSA-109581 carries stroke-width 8 with no
transform, and length is varied by reshaping the shaft. This does the same —
an exact de Casteljau truncation of the shaft curve, leaving stroke-width and
the arrowhead polygon untouched.
"""
import re

def _split_cubic(p, t):
    """de Casteljau: return the sub-curve control points for [0, t]."""
    (x0,y0),(x1,y1),(x2,y2),(x3,y3) = p
    lerp = lambda a,b: (a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t)
    a,b,c = lerp(p[0],p[1]), lerp(p[1],p[2]), lerp(p[2],p[3])
    d,e = lerp(a,b), lerp(b,c)
    f = lerp(d,e)
    return [p[0], a, d, f]

def _x_at(p, t):
    mt = 1-t
    return (mt**3*p[0][0] + 3*mt*mt*t*p[1][0] + 3*mt*t*t*p[2][0] + t**3*p[3][0])

def _remap_gradient(svg_text, grad_id, new_tail_x):
    """Move the gradient's light end to the shaft's new tail.

    The library arrows stroke their shaft with a userSpaceOnUse linear gradient
    spanning the FULL native shaft (x1=0 light -> x2=61 dark). Shortening the
    shaft without moving x1 leaves the visible part sampling only the dark end,
    so the arrow renders as a flat dark line and loses the light-to-dark fade
    that every other arrow in the diagram has. The fade is also directional —
    light at the tail, solid at the tip — so losing it drops a visual cue, not
    just a decoration.
    """
    m = re.search(r'<linearGradient\b[^>]*\bid="' + re.escape(grad_id) + r'"[^>]*>', svg_text)
    if not m:
        return svg_text, None
    tag = m.group(0)
    if 'gradientUnits="userSpaceOnUse"' not in tag:
        # objectBoundingBox gradients rescale with the shape automatically.
        return svg_text, None
    old_x1 = re.search(r'\bx1="([-\d.eE]+)"', tag)
    if not old_x1:
        return svg_text, None
    new_tag = re.sub(r'\bx1="[-\d.eE]+"', f'x1="{new_tail_x:.4f}"', tag, count=1)
    return svg_text[:m.start()] + new_tag + svg_text[m.end():], float(old_x1.group(1))


def truncate_shaft(svg_text, tail_x):
    """Rewrite the shaft path so its tail sits at local x = tail_x, and move the
    stroke gradient's light end with it so the full fade spans the new length."""
    m = re.search(r'(<path[^>]*\bd=")(M[^"]*)("[^>]*stroke-width="8"[^>]*>)', svg_text)
    if not m:
        raise SystemExit('shaft path not found')
    shaft_tag = m.group(1) + m.group(2) + m.group(3)
    nums = [float(v) for v in re.findall(r'-?\d*\.?\d+(?:[eE][-+]?\d+)?', m.group(2))]
    p = [(nums[0],nums[1]), (nums[2],nums[3]), (nums[4],nums[5]), (nums[6],nums[7])]
    # x decreases along the curve; bisect for the t where x == tail_x
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = (lo+hi)/2
        if _x_at(p, mid) > tail_x: lo = mid
        else: hi = mid
    q = _split_cubic(p, (lo+hi)/2)
    d = (f"M{q[0][0]:.4f} {q[0][1]:.4f}"
         f"C{q[1][0]:.4f} {q[1][1]:.4f} {q[2][0]:.4f} {q[2][1]:.4f} {q[3][0]:.4f} {q[3][1]:.4f}")
    out = svg_text[:m.start(2)] + d + svg_text[m.end(2):]

    ref = re.search(r'stroke="url\(#([^)]+)\)"', shaft_tag)
    if ref:
        out, _ = _remap_gradient(out, ref.group(1), tail_x)
    return out


def fit(icon_svg_path, total_length, out_path, native_width=70.0):
    """Write a copy of the arrow icon shortened to `total_length` user units.

    The arrowhead (local x 60..70) is untouched; only the shaft tail moves, so
    the result keeps the icon's native stroke-width and head size. Place the
    result with `place --scale 1` and translate it into position: the content
    then spans local x (native_width - total_length) .. native_width.
    """
    if total_length <= 12:
        raise SystemExit(f'total_length {total_length} leaves no shaft; the '
                         'arrowhead alone is ~10 units. Give the arrow more room.')
    src = open(icon_svg_path, encoding='utf-8').read()
    out = truncate_shaft(src, native_width - total_length)
    open(out_path, 'w', encoding='utf-8').write(out)
    return {'tailX': native_width - total_length,
            'spansLocalX': [native_width - total_length, native_width]}


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 4:
        raise SystemExit('usage: arrow_fit.py <arrow-icon.svg> <total-length> <out.svg>')
    import json
    print(json.dumps(fit(sys.argv[1], float(sys.argv[2]), sys.argv[3]), indent=2))
