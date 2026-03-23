"""
test_visualizations.py — Tests for visualizations.py SVG generation module.

TDD: run first to verify failures, then implement visualizations.py, then verify passes.

Run from repo root:
    python tests/test_visualizations.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "meta-analyst"))

from pipeline.visualizations import (
    forest_plot_svg,
    funnel_plot_svg,
    prisma_flow_svg,
    rob_traffic_light_svg,
)

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}" + (f": {detail}" if detail else ""))


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------
studies = [
    {"label": "Smith 2020", "effect": -0.89, "ci_lower": -1.58, "ci_upper": -0.19, "weight_pct": 15.2},
    {"label": "Jones 2021", "effect": -0.51, "ci_lower": -1.10, "ci_upper": 0.08,  "weight_pct": 22.5},
    {"label": "Chen 2022",  "effect": -0.22, "ci_lower": -0.71, "ci_upper": 0.27,  "weight_pct": 30.1},
    {"label": "Lee 2023",   "effect": -0.69, "ci_lower": -1.50, "ci_upper": 0.11,  "weight_pct": 12.8},
    {"label": "Park 2024",  "effect": -0.36, "ci_lower": -0.91, "ci_upper": 0.20,  "weight_pct": 19.4},
]
pooled = {"pooled": -0.47, "ci_lower": -0.74, "ci_upper": -0.20}
fixed_pooled = {"pooled": -0.43, "ci_lower": -0.65, "ci_upper": -0.21}

effects = [-0.89, -0.51, -0.22, -0.69, -0.36]
ses     = [0.355,  0.302,  0.250,  0.412,  0.280]

prisma_counts = {
    "db_pubmed":             342,
    "db_central":            198,
    "db_ctgov":               47,
    "duplicates_removed":     89,
    "screened":              498,
    "excluded_screening":    423,
    "eligible":               75,
    "excluded_eligibility":   70,
    "included":                5,
}

rob_data = [
    {"study": "Smith 2020", "domains": [
        {"domain": "Randomisation", "judgment": "low"},
        {"domain": "Deviations",    "judgment": "some concerns"},
        {"domain": "Missing data",  "judgment": "low"},
        {"domain": "Measurement",   "judgment": "low"},
        {"domain": "Reporting",     "judgment": "high"},
    ]},
    {"study": "Jones 2021", "domains": [
        {"domain": "Randomisation", "judgment": "low"},
        {"domain": "Deviations",    "judgment": "low"},
        {"domain": "Missing data",  "judgment": "some concerns"},
        {"domain": "Measurement",   "judgment": "low"},
        {"domain": "Reporting",     "judgment": "low"},
    ]},
]


# ===========================================================================
# forest_plot_svg
# ===========================================================================
print("\n--- forest_plot_svg ---")

svg = forest_plot_svg(studies, pooled, fixed_pooled=fixed_pooled,
                      title="Test Forest Plot", null_value=0.0)

check("returns a string",          isinstance(svg, str))
check("starts with <svg",          svg.lstrip().startswith("<svg"))
check("closes with </svg>",        "</svg>" in svg)
check("contains Smith 2020",       "Smith 2020" in svg)
check("contains Jones 2021",       "Jones 2021" in svg)
check("contains Chen 2022",        "Chen 2022" in svg)
check("contains Lee 2023",         "Lee 2023" in svg)
check("contains Park 2024",        "Park 2024" in svg)
check("contains diamond (polygon or path)", "polygon" in svg or "<path" in svg)
check("contains null line",        "<line" in svg)
check("contains weight pct 15.2",  "15.2" in svg)
check("contains weight pct 30.1",  "30.1" in svg)
check("contains title text",       "Test Forest Plot" in svg)
check("width attr present",        'width=' in svg)
check("height attr present",       'height=' in svg)

# With no fixed_pooled
svg2 = forest_plot_svg(studies, pooled)
check("works without fixed_pooled", isinstance(svg2, str) and svg2.lstrip().startswith("<svg"))


# ===========================================================================
# funnel_plot_svg
# ===========================================================================
print("\n--- funnel_plot_svg ---")

fsvg = funnel_plot_svg(effects, ses, pooled["pooled"])

check("returns a string",          isinstance(fsvg, str))
check("starts with <svg",          fsvg.lstrip().startswith("<svg"))
check("closes with </svg>",        "</svg>" in fsvg)
check("contains circle elements",  "<circle" in fsvg)
check("has one circle per study",  fsvg.count("<circle") >= len(effects))
check("contains pooled line",      "<line" in fsvg)
check("contains CI triangle/polygon", "polygon" in fsvg or "<path" in fsvg or "<line" in fsvg)
check("width ~600px",              "600" in fsvg)
check("height ~400px",             "400" in fsvg)


# ===========================================================================
# prisma_flow_svg
# ===========================================================================
print("\n--- prisma_flow_svg ---")

psvg = prisma_flow_svg(prisma_counts)

check("returns a string",          isinstance(psvg, str))
check("starts with <svg",          psvg.lstrip().startswith("<svg"))
check("closes with </svg>",        "</svg>" in psvg)
check("contains 'Included' text",  "Included" in psvg)
check("contains PubMed",           "PubMed" in psvg)
check("contains CENTRAL",          "CENTRAL" in psvg)
check("contains ClinicalTrials",   "ClinicalTrials" in psvg)
check("contains count 342",        "342" in psvg)
check("contains count 198",        "198" in psvg)
check("contains count 5",          "5" in psvg)
check("contains count 89 (dupes)", "89" in psvg)
check("contains 'Screening'",      "Screening" in psvg or "screening" in psvg)
check("contains 'Identification'", "Identification" in psvg or "identification" in psvg)
check("has rect boxes",            "<rect" in psvg)
check("has arrows/lines",          "<line" in psvg or "<path" in psvg)
check("width ~700px",              "700" in psvg)


# ===========================================================================
# rob_traffic_light_svg
# ===========================================================================
print("\n--- rob_traffic_light_svg ---")

rsvg = rob_traffic_light_svg(rob_data)

check("returns a string",          isinstance(rsvg, str))
check("starts with <svg",          rsvg.lstrip().startswith("<svg"))
check("closes with </svg>",        "</svg>" in rsvg)
check("contains Smith 2020",       "Smith 2020" in rsvg)
check("contains Jones 2021",       "Jones 2021" in rsvg)
check("contains Randomisation",    "Randomisation" in rsvg)
check("contains Deviations",       "Deviations" in rsvg)
check("contains Missing data",     "Missing data" in rsvg)
check("contains green (#4caf50)",  "#4caf50" in rsvg)
check("contains yellow (#ff9800)", "#ff9800" in rsvg)
check("contains red (#f44336)",    "#f44336" in rsvg)
check("contains circle elements",  "<circle" in rsvg)


# ===========================================================================
# Summary
# ===========================================================================
print(f"\n{'='*50}")
print(f"Results: {PASS} passed, {FAIL} failed")
if FAIL == 0:
    print("All tests passed!")
else:
    print(f"{FAIL} test(s) FAILED.")
    sys.exit(1)
