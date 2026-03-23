"""
visualizations.py — SVG generation module for meta-analysis outputs.

All functions return SVG strings built via plain string construction (no
external rendering libraries). SVG dimensions are fixed or dynamically scaled
based on data size.

Functions
---------
forest_plot_svg    — Forest plot with per-study CI whiskers and pooled diamond
funnel_plot_svg    — Funnel plot with pseudo-95% CI triangle
prisma_flow_svg    — PRISMA 2020 flow diagram
rob_traffic_light_svg — Risk-of-bias traffic-light table
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _esc(text):
    """Escape special XML characters for embedding in SVG text nodes."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _svg_wrap(content, width, height, extra_attrs=""):
    """Wrap content in an <svg> root element."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'{extra_attrs}>\n'
        f'{content}\n'
        f'</svg>'
    )


def _line(x1, y1, x2, y2, stroke="#333", stroke_width=1, **kwargs):
    attrs = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in kwargs.items())
    return (
        f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
        f'stroke="{stroke}" stroke-width="{stroke_width}" {attrs}/>'
    )


def _rect(x, y, w, h, fill="#eee", stroke="#333", stroke_width=1, rx=0):
    return (
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" rx="{rx}"/>'
    )


def _text(x, y, content, font_size=12, anchor="start", fill="#000",
          font_weight="normal", font_family="Arial, sans-serif"):
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" font-size="{font_size}" '
        f'text-anchor="{anchor}" fill="{fill}" font-weight="{font_weight}" '
        f'font-family="{font_family}">{_esc(content)}</text>'
    )


def _circle(cx, cy, r, fill="#333", stroke="none", stroke_width=1):
    return (
        f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
    )


def _polygon(points, fill="#333", stroke="#333", stroke_width=1, opacity=1.0):
    pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return (
        f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" '
        f'stroke-width="{stroke_width}" opacity="{opacity}"/>'
    )


# ---------------------------------------------------------------------------
# 1. Forest Plot
# ---------------------------------------------------------------------------

def forest_plot_svg(studies, pooled, fixed_pooled=None, title="",
                    null_value=0.0, measure_label="Effect"):
    """
    Generate a forest-plot SVG.

    Parameters
    ----------
    studies      : list of {label, effect, ci_lower, ci_upper, weight_pct}
    pooled       : {pooled, ci_lower, ci_upper}  — random-effects summary
    fixed_pooled : {pooled, ci_lower, ci_upper}  — optional fixed-effect summary
    title        : plot title string
    null_value   : value of the null line (default 0.0)
    measure_label: x-axis label

    Returns
    -------
    str — SVG markup
    """
    # --- Layout constants ---
    W = 800
    MARGIN_LEFT  = 220   # space for study labels
    MARGIN_RIGHT =  80   # space for CI text
    PLOT_W = W - MARGIN_LEFT - MARGIN_RIGHT   # pixel width of the plot area
    ROW_H = 28
    HEADER_H = 60        # title + column header
    FOOTER_H = 80        # diamond rows + x-axis label

    n_studies = len(studies)
    H = HEADER_H + n_studies * ROW_H + FOOTER_H
    if fixed_pooled is not None:
        H += ROW_H        # extra row for fixed-effect diamond

    # --- Axis range: span all CIs plus null ---
    all_vals = (
        [s["ci_lower"] for s in studies]
        + [s["ci_upper"] for s in studies]
        + [pooled["ci_lower"], pooled["ci_upper"], null_value]
    )
    if fixed_pooled:
        all_vals += [fixed_pooled["ci_lower"], fixed_pooled["ci_upper"]]
    x_min = min(all_vals)
    x_max = max(all_vals)
    pad = (x_max - x_min) * 0.12
    x_min -= pad
    x_max += pad

    def to_px(val):
        """Convert a data value to x pixel position."""
        frac = (val - x_min) / (x_max - x_min)
        return MARGIN_LEFT + frac * PLOT_W

    # --- Start building SVG elements ---
    elems = []

    # Background
    elems.append(_rect(0, 0, W, H, fill="#ffffff", stroke="none"))

    # Title
    if title:
        elems.append(_text(W / 2, 22, title, font_size=15,
                           anchor="middle", font_weight="bold"))

    # Column headers
    header_y = 45
    elems.append(_text(5, header_y, "Study", font_size=11, font_weight="bold"))
    elems.append(_text(MARGIN_LEFT + PLOT_W / 2, header_y,
                       f"{measure_label} (95% CI)", font_size=11,
                       anchor="middle", font_weight="bold"))
    elems.append(_text(W - MARGIN_RIGHT + 5, header_y, "Weight (%)",
                       font_size=11, font_weight="bold"))

    # Null line (drawn behind study points)
    null_px = to_px(null_value)
    plot_top = HEADER_H
    plot_bottom = HEADER_H + n_studies * ROW_H
    elems.append(_line(null_px, plot_top - 5, null_px,
                       plot_bottom + 5, stroke="#999", stroke_width=1,
                       stroke_dasharray="4 3"))

    # Per-study rows
    max_weight = max(s["weight_pct"] for s in studies)
    for i, s in enumerate(studies):
        row_y = HEADER_H + i * ROW_H + ROW_H / 2

        # Label
        elems.append(_text(5, row_y + 4, s["label"], font_size=11))

        # Square (size proportional to weight)
        sq_half = 4 + 6 * (s["weight_pct"] / max_weight)
        eff_px  = to_px(s["effect"])
        lo_px   = to_px(s["ci_lower"])
        hi_px   = to_px(s["ci_upper"])

        # Whisker line
        elems.append(_line(lo_px, row_y, hi_px, row_y,
                           stroke="#333", stroke_width=1.5))
        # Left tick
        elems.append(_line(lo_px, row_y - 4, lo_px, row_y + 4,
                           stroke="#333", stroke_width=1.5))
        # Right tick
        elems.append(_line(hi_px, row_y - 4, hi_px, row_y + 4,
                           stroke="#333", stroke_width=1.5))
        # Square
        elems.append(_rect(
            eff_px - sq_half, row_y - sq_half,
            sq_half * 2, sq_half * 2,
            fill="#1565c0", stroke="#0d47a1",
        ))

        # CI text
        ci_txt = f"{s['effect']:.2f} [{s['ci_lower']:.2f}, {s['ci_upper']:.2f}]"
        elems.append(_text(W - MARGIN_RIGHT + 5, row_y + 4,
                           f"{s['weight_pct']:.1f}", font_size=10))
        # effect + CI in right text column (abbreviated)
        elems.append(_text(
            MARGIN_LEFT - 5, row_y + 4,
            ci_txt, font_size=9, anchor="end", fill="#555",
        ))

    # Separator line
    elems.append(_line(0, plot_bottom + 4, W, plot_bottom + 4,
                       stroke="#aaa", stroke_width=1))

    # --- Pooled estimates (diamonds) ---
    def draw_diamond(result, y_center, label, color):
        lo_px  = to_px(result["ci_lower"])
        hi_px  = to_px(result["ci_upper"])
        mid_px = to_px(result["pooled"])
        dh = 8  # half-height of diamond
        pts = [
            (mid_px, y_center - dh),
            (hi_px,  y_center),
            (mid_px, y_center + dh),
            (lo_px,  y_center),
        ]
        elems.append(_polygon(pts, fill=color, stroke=color))
        elems.append(_text(5, y_center + 4, label, font_size=11,
                           font_weight="bold"))
        ci_txt = (f"{result['pooled']:.2f} "
                  f"[{result['ci_lower']:.2f}, {result['ci_upper']:.2f}]")
        elems.append(_text(MARGIN_LEFT - 5, y_center + 4, ci_txt,
                           font_size=9, anchor="end", fill="#555"))

    diamond_y = plot_bottom + 30
    draw_diamond(pooled, diamond_y, "Random effects", "#d32f2f")

    if fixed_pooled is not None:
        draw_diamond(fixed_pooled, diamond_y + ROW_H,
                     "Fixed effect", "#7b1fa2")

    # X-axis label
    axis_y = H - 12
    elems.append(_text(MARGIN_LEFT + PLOT_W / 2, axis_y,
                       measure_label, font_size=11, anchor="middle"))

    # Null value label on axis
    elems.append(_text(null_px, axis_y, str(null_value),
                       font_size=9, anchor="middle", fill="#666"))

    return _svg_wrap("\n".join(elems), W, H)


# ---------------------------------------------------------------------------
# 2. Funnel Plot
# ---------------------------------------------------------------------------

def funnel_plot_svg(effects, ses, pooled):
    """
    Generate a funnel-plot SVG.

    Parameters
    ----------
    effects : list of float — per-study effect estimates
    ses     : list of float — per-study standard errors
    pooled  : float         — pooled effect estimate (vertical reference line)

    Returns
    -------
    str — SVG markup
    """
    W = 600
    H = 400
    ML = 70   # left margin
    MR = 30
    MT = 40
    MB = 50

    PLOT_W = W - ML - MR
    PLOT_H = H - MT - MB

    # Axis ranges
    all_e = list(effects) + [pooled]
    e_min = min(all_e)
    e_max = max(all_e)
    e_pad = (e_max - e_min) * 0.15 or 0.1
    e_min -= e_pad
    e_max += e_pad

    se_max = max(ses)
    se_min = 0.0
    se_pad = se_max * 0.05

    # Note: y-axis is inverted (SE=0 at top)
    def to_x(e):
        return ML + (e - e_min) / (e_max - e_min) * PLOT_W

    def to_y(se):
        # SE=0 maps to top (MT), se_max maps to bottom (MT+PLOT_H)
        return MT + se / (se_max + se_pad) * PLOT_H

    elems = []
    elems.append(_rect(0, 0, W, H, fill="#ffffff", stroke="none"))

    # Title
    elems.append(_text(W / 2, 20, "Funnel Plot", font_size=14,
                       anchor="middle", font_weight="bold"))

    # Plot border
    elems.append(_rect(ML, MT, PLOT_W, PLOT_H, fill="#f9f9f9",
                       stroke="#ccc", stroke_width=1))

    # Pseudo-95% CI triangle
    # At SE level s, x = pooled ± 1.96 * s
    # Triangle: apex at (pooled, SE=0), base at (pooled ± 1.96*se_max, se_max)
    apex_x = to_x(pooled)
    apex_y = to_y(0)
    base_y = to_y(se_max)
    base_lo = to_x(pooled - 1.96 * se_max)
    base_hi = to_x(pooled + 1.96 * se_max)

    elems.append(_polygon(
        [(apex_x, apex_y), (base_hi, base_y), (base_lo, base_y)],
        fill="#e3f2fd", stroke="#90caf9", stroke_width=1, opacity=0.7,
    ))

    # Pooled vertical line
    elems.append(_line(apex_x, MT, apex_x, MT + PLOT_H,
                       stroke="#d32f2f", stroke_width=1.5,
                       stroke_dasharray="5 3"))

    # Study scatter points
    for e, se in zip(effects, ses):
        cx = to_x(e)
        cy = to_y(se)
        elems.append(_circle(cx, cy, 5, fill="#1565c0", stroke="#ffffff",
                             stroke_width=1))

    # Y-axis labels (SE, inverted — 0 at top)
    elems.append(_text(ML - 5, MT + 4, "0", font_size=9,
                       anchor="end", fill="#555"))
    elems.append(_text(ML - 5, MT + PLOT_H,
                       f"{se_max:.2f}", font_size=9, anchor="end", fill="#555"))
    mid_se = se_max / 2
    elems.append(_text(ML - 5, to_y(mid_se),
                       f"{mid_se:.2f}", font_size=9, anchor="end", fill="#555"))

    # Y-axis title (rotated)
    elems.append(
        f'<text x="{12}" y="{MT + PLOT_H / 2:.2f}" '
        f'font-size="11" text-anchor="middle" fill="#333" '
        f'font-family="Arial, sans-serif" '
        f'transform="rotate(-90, 12, {MT + PLOT_H / 2:.2f})">'
        f'SE (inverted)</text>'
    )

    # X-axis labels
    elems.append(_text(ML, MT + PLOT_H + 15, f"{e_min:.2f}",
                       font_size=9, anchor="middle", fill="#555"))
    elems.append(_text(ML + PLOT_W, MT + PLOT_H + 15, f"{e_max:.2f}",
                       font_size=9, anchor="middle", fill="#555"))
    elems.append(_text(W / 2, H - 8, "Effect Estimate",
                       font_size=11, anchor="middle"))

    return _svg_wrap("\n".join(elems), W, H)


# ---------------------------------------------------------------------------
# 3. PRISMA Flow Diagram
# ---------------------------------------------------------------------------

def prisma_flow_svg(counts):
    """
    Generate a PRISMA 2020 flow diagram SVG.

    Parameters
    ----------
    counts : dict with keys:
        db_pubmed, db_central, db_ctgov,
        duplicates_removed,
        screened, excluded_screening,
        eligible, excluded_eligibility,
        included

    Returns
    -------
    str — SVG markup
    """
    W = 700
    # Box dimensions
    BOX_W = 190
    BOX_H = 52
    # Column x-positions (center)
    COL_LEFT   = 155
    COL_CENTER = 380
    COL_RIGHT  = 590
    # Row y-positions (top of box)
    R0 = 30    # Identification row (databases)
    R1 = 140   # Duplicates removed
    R2 = 230   # Screening
    R3 = 330   # Eligibility
    R4 = 430   # Included

    db_total = (counts["db_pubmed"] + counts["db_central"]
                + counts["db_ctgov"] - counts["duplicates_removed"])

    # Dynamic height
    H = R4 + BOX_H + 60

    elems = []
    elems.append(_rect(0, 0, W, H, fill="#ffffff", stroke="none"))

    # ---- Phase labels ----
    phase_style = dict(font_size=11, font_weight="bold", fill="#555")
    elems.append(_text(8, R0 + BOX_H // 2 + 4, "Identification", **phase_style))
    elems.append(_text(8, R2 + BOX_H // 2 + 4, "Screening", **phase_style))
    elems.append(_text(8, R3 + BOX_H // 2 + 4, "Eligibility", **phase_style))
    elems.append(_text(8, R4 + BOX_H // 2 + 4, "Included", **phase_style))

    def box(cx, ry, lines, fill="#e3f2fd", stroke="#1565c0"):
        bx = cx - BOX_W / 2
        elems.append(_rect(bx, ry, BOX_W, BOX_H, fill=fill,
                           stroke=stroke, stroke_width=1.5, rx=4))
        line_h = BOX_H / (len(lines) + 1)
        for j, ln in enumerate(lines, 1):
            elems.append(_text(cx, ry + j * line_h + 2,
                               ln, font_size=10, anchor="middle"))

    def arrow_down(cx, y1, y2, stroke="#555"):
        # Vertical arrow from y1 to y2 at x=cx
        elems.append(_line(cx, y1, cx, y2 - 8, stroke=stroke, stroke_width=1.5))
        # Arrowhead
        ax, ay = cx, y2
        elems.append(_polygon(
            [(ax - 6, ay - 8), (ax + 6, ay - 8), (ax, ay)],
            fill=stroke, stroke=stroke,
        ))

    def arrow_right(y_center, x1, x2, stroke="#555"):
        elems.append(_line(x1, y_center, x2 - 8, y_center,
                           stroke=stroke, stroke_width=1.5))
        elems.append(_polygon(
            [(x2 - 8, y_center - 5), (x2, y_center), (x2 - 8, y_center + 5)],
            fill=stroke, stroke=stroke,
        ))

    # ---- Row 0: Database boxes ----
    box(COL_LEFT - 120, R0,
        ["PubMed", f"n = {counts['db_pubmed']}"],
        fill="#fff8e1", stroke="#f9a825")
    box(COL_LEFT, R0,
        ["Cochrane CENTRAL", f"n = {counts['db_central']}"],
        fill="#fff8e1", stroke="#f9a825")
    box(COL_LEFT + 120, R0,
        ["ClinicalTrials.gov", f"n = {counts['db_ctgov']}"],
        fill="#fff8e1", stroke="#f9a825")

    # ---- Merge line from databases to center column ----
    # Horizontal connector across 3 boxes at their bottoms
    merge_y = R0 + BOX_H + 10
    left_cx  = COL_LEFT - 120
    right_cx = COL_LEFT + 120

    elems.append(_line(left_cx, R0 + BOX_H, left_cx, merge_y,
                       stroke="#555", stroke_width=1.5))
    elems.append(_line(COL_LEFT, R0 + BOX_H, COL_LEFT, merge_y,
                       stroke="#555", stroke_width=1.5))
    elems.append(_line(right_cx, R0 + BOX_H, right_cx, merge_y,
                       stroke="#555", stroke_width=1.5))
    elems.append(_line(left_cx, merge_y, right_cx, merge_y,
                       stroke="#555", stroke_width=1.5))
    # Arrow from midpoint down to duplicates box
    merge_cx = COL_LEFT
    arrow_down(merge_cx, merge_y, R1)

    # ---- Row 1: Duplicates removed ----
    box(COL_CENTER, R1,
        ["Duplicates removed", f"n = {counts['duplicates_removed']}"],
        fill="#fce4ec", stroke="#c62828")

    # Arrow from duplicates row to screening
    arrow_down(merge_cx, R1 + BOX_H, R2)

    # Right arrow to duplicates box
    arrow_right(R1 + BOX_H // 2, merge_cx + BOX_W // 2,
                COL_CENTER - BOX_W // 2)

    # ---- Row 2: Screened ----
    box(COL_LEFT, R2,
        ["Records screened", f"n = {counts['screened']}"])

    # Right side: excluded at screening
    box(COL_CENTER, R2,
        ["Excluded (screening)", f"n = {counts['excluded_screening']}"],
        fill="#fce4ec", stroke="#c62828")
    arrow_right(R2 + BOX_H // 2, COL_LEFT + BOX_W // 2,
                COL_CENTER - BOX_W // 2)

    arrow_down(COL_LEFT, R2 + BOX_H, R3)

    # ---- Row 3: Eligibility ----
    box(COL_LEFT, R3,
        ["Full-text assessed", f"n = {counts['eligible']}"])
    box(COL_CENTER, R3,
        ["Excluded (eligibility)", f"n = {counts['excluded_eligibility']}"],
        fill="#fce4ec", stroke="#c62828")
    arrow_right(R3 + BOX_H // 2, COL_LEFT + BOX_W // 2,
                COL_CENTER - BOX_W // 2)

    arrow_down(COL_LEFT, R3 + BOX_H, R4)

    # ---- Row 4: Included ----
    box(COL_LEFT, R4,
        ["Studies included", f"n = {counts['included']}"],
        fill="#e8f5e9", stroke="#2e7d32")

    return _svg_wrap("\n".join(elems), W, H)


# ---------------------------------------------------------------------------
# 4. Risk-of-Bias Traffic Light
# ---------------------------------------------------------------------------

def rob_traffic_light_svg(rob_data):
    """
    Generate a risk-of-bias traffic-light table SVG.

    Parameters
    ----------
    rob_data : list of {study, domains: [{domain, judgment}]}
        judgment must be one of: 'low', 'some concerns', 'high'

    Returns
    -------
    str — SVG markup
    """
    JUDGMENT_COLOR = {
        "low":           "#4caf50",
        "some concerns": "#ff9800",
        "high":          "#f44336",
    }
    CIRCLE_R = 12
    COL_W    = 110   # width per domain column
    ROW_H    = 36
    LABEL_W  = 140   # study label column

    if not rob_data:
        return _svg_wrap("", 200, 50)

    # Collect domain names (preserve insertion order, deduplicate)
    seen = {}
    for entry in rob_data:
        for d in entry["domains"]:
            seen[d["domain"]] = True
    domains = list(seen.keys())

    n_studies = len(rob_data)
    n_domains = len(domains)

    W = LABEL_W + n_domains * COL_W + 20
    H = ROW_H * (n_studies + 1) + 20  # +1 for header

    elems = []
    elems.append(_rect(0, 0, W, H, fill="#ffffff", stroke="none"))

    # Header row background
    elems.append(_rect(0, 0, W, ROW_H, fill="#eceff1", stroke="none"))

    # Header: "Study" label
    elems.append(_text(8, ROW_H / 2 + 5, "Study", font_size=11,
                       font_weight="bold"))

    # Domain column headers (rotated or truncated)
    for col_i, dom in enumerate(domains):
        cx = LABEL_W + col_i * COL_W + COL_W / 2
        # Use short label if needed (truncate at 14 chars)
        short = dom if len(dom) <= 14 else dom[:13] + "…"
        elems.append(_text(cx, ROW_H / 2 + 5, short, font_size=9,
                           anchor="middle", font_weight="bold"))

    # Alternating row backgrounds + circles
    for row_i, entry in enumerate(rob_data):
        ry = ROW_H * (row_i + 1)
        bg = "#f5f5f5" if row_i % 2 == 0 else "#ffffff"
        elems.append(_rect(0, ry, W, ROW_H, fill=bg, stroke="none"))

        # Separator line
        elems.append(_line(0, ry, W, ry, stroke="#e0e0e0", stroke_width=1))

        # Study label
        label = entry["study"]
        short_label = label if len(label) <= 18 else label[:17] + "…"
        elems.append(_text(8, ry + ROW_H / 2 + 5, short_label, font_size=10))

        # Domain circles
        domain_map = {d["domain"]: d["judgment"] for d in entry["domains"]}
        for col_i, dom in enumerate(domains):
            judgment = domain_map.get(dom, "")
            color = JUDGMENT_COLOR.get(judgment.lower(), "#bdbdbd")
            cx = LABEL_W + col_i * COL_W + COL_W / 2
            cy = ry + ROW_H / 2
            elems.append(_circle(cx, cy, CIRCLE_R, fill=color,
                                 stroke="#fff", stroke_width=2))

    # Outer border
    elems.append(_rect(0, 0, W, H, fill="none", stroke="#ccc", stroke_width=1))

    # Legend
    legend_y = H - 2
    elems.append(_text(8, legend_y, "Low", font_size=8, fill="#4caf50"))
    elems.append(_text(60, legend_y, "Some concerns", font_size=8,
                       fill="#ff9800"))
    elems.append(_text(170, legend_y, "High", font_size=8, fill="#f44336"))

    return _svg_wrap("\n".join(elems), W, H)
