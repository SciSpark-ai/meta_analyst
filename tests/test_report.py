"""
test_report.py — Tests for report.py report assembly module.

TDD: run first to verify failures, then implement report.py, then verify passes.

Run from repo root:
    python tests/test_report.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "meta-analyst"))

from pipeline.report import (
    format_characteristics_table,
    format_grade_sof_table,
    assemble_report,
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

char_studies = [
    {
        "first_author": "Smith",
        "year": 2020,
        "n_intervention": 150,
        "n_control": 150,
        "intervention_description": "Drug A 10mg",
        "comparator_description": "Placebo",
        "followup_duration": "12 months",
        "rob_overall": "low",
    },
    {
        "first_author": "Jones",
        "year": 2021,
        "n_intervention": 200,
        "n_control": 200,
        "intervention_description": "Drug A 10mg",
        "comparator_description": "Placebo",
        "followup_duration": "24 months",
        "rob_overall": "some concerns",
    },
]

grade_outcomes = [
    {
        "name": "Primary Outcome",
        "n_studies": 5,
        "total_n": 1200,
        "pooled_effect": -0.47,
        "ci_lower": -0.74,
        "ci_upper": -0.20,
        "certainty": "moderate",
        "certainty_symbols": "⊕⊕⊕⊖",
        "downgrade_reasons": "Some concerns about blinding",
    },
    {
        "name": "Secondary Outcome",
        "n_studies": 3,
        "total_n": 650,
        "pooled_effect": -0.21,
        "ci_lower": -0.55,
        "ci_upper": 0.13,
        "certainty": "low",
        "certainty_symbols": "⊕⊕⊖⊖",
        "downgrade_reasons": "High risk of bias; imprecision",
    },
]

pico = {
    "population": "Adults with hypertension",
    "intervention": "Drug A 10mg",
    "comparator": "Placebo",
    "outcome": "Blood pressure reduction",
    "question": "Does Drug A reduce blood pressure in hypertensive adults?",
}

search = {
    "query": '("Drug A" OR "medication A") AND ("hypertension" OR "blood pressure")',
    "date_range": "2000-2024",
    "databases": ["PubMed", "Cochrane CENTRAL", "ClinicalTrials.gov"],
}

prisma_counts = {
    "db_pubmed": 342,
    "db_central": 198,
    "db_ctgov": 47,
    "duplicates_removed": 89,
    "screened": 498,
    "excluded_screening": 423,
    "eligible": 75,
    "excluded_eligibility": 70,
    "included": 5,
}

rob_summary = "2 of 5 studies rated low RoB; 2 some concerns; 1 high RoB."

outcomes_for_report = [
    {
        "name": "Primary Outcome",
        "pooling": {
            "pooled": -0.47,
            "ci_lower": -0.74,
            "ci_upper": -0.20,
            "p_value": 0.001,
        },
        "heterogeneity": {
            "i2": 42.3,
            "q": 6.93,
            "q_p_value": 0.139,
            "prediction_lower": -1.10,
            "prediction_upper": 0.16,
        },
        "studies": [
            {"label": "Smith 2020", "effect": -0.89, "ci_lower": -1.58,
             "ci_upper": -0.19, "weight_pct": 15.2},
            {"label": "Jones 2021", "effect": -0.51, "ci_lower": -1.10,
             "ci_upper": 0.08,  "weight_pct": 22.5},
            {"label": "Chen 2022",  "effect": -0.22, "ci_lower": -0.71,
             "ci_upper": 0.27,  "weight_pct": 30.1},
            {"label": "Lee 2023",   "effect": -0.69, "ci_lower": -1.50,
             "ci_upper": 0.11,  "weight_pct": 12.8},
            {"label": "Park 2024",  "effect": -0.36, "ci_lower": -0.91,
             "ci_upper": 0.20,  "weight_pct": 19.4},
        ],
        "effects_for_funnel": [-0.89, -0.51, -0.22, -0.69, -0.36],
        "ses_for_funnel": [0.355, 0.302, 0.250, 0.412, 0.280],
        "grade": {
            "certainty": "moderate",
            "certainty_symbols": "⊕⊕⊕⊖",
            "downgrade_reasons": "Some concerns about blinding",
        },
        "sensitivity": {
            "leave_one_out": [
                {"removed": "Smith 2020", "pooled": -0.43, "ci_lower": -0.72,
                 "ci_upper": -0.14},
                {"removed": "Jones 2021", "pooled": -0.45, "ci_lower": -0.75,
                 "ci_upper": -0.15},
            ],
            "high_rob_excluded": {"pooled": -0.40, "ci_lower": -0.70,
                                  "ci_upper": -0.10, "n_removed": 1},
        },
        "publication_bias": {
            "egger_p": 0.32,
            "egger_note": "No significant asymmetry detected",
        },
    },
]

sensitivity = {
    "Primary Outcome": {
        "leave_one_out": [
            {"removed": "Smith 2020", "pooled": -0.43},
            {"removed": "Jones 2021", "pooled": -0.45},
        ],
        "fixed_vs_random": {"fixed": -0.43, "random": -0.47},
        "high_rob_excluded": {"pooled": -0.40, "n_removed": 1},
    }
}

publication_bias = {
    "Primary Outcome": {
        "egger_p": 0.32,
        "note": "No significant asymmetry detected",
    }
}


# ===========================================================================
# format_characteristics_table
# ===========================================================================
print("\n--- format_characteristics_table ---")

ct = format_characteristics_table(char_studies)

check("returns a string",              isinstance(ct, str))
check("contains pipe (Markdown table)", "|" in ct)
check("contains Smith",                "Smith" in ct)
check("contains Jones",                "Jones" in ct)
check("contains 2020",                 "2020" in ct)
check("contains 2021",                 "2021" in ct)
check("contains n_intervention 150",   "150" in ct)
check("contains n_intervention 200",   "200" in ct)
check("contains Drug A",               "Drug A" in ct)
check("contains 12 months",            "12 months" in ct)
check("contains rob_overall 'low'",    "low" in ct)
check("contains 'some concerns'",      "some concerns" in ct)
check("has header separator row",      "|---" in ct or "| ---" in ct or "|:---" in ct)


# ===========================================================================
# format_grade_sof_table
# ===========================================================================
print("\n--- format_grade_sof_table ---")

sof = format_grade_sof_table(grade_outcomes)

check("returns a string",              isinstance(sof, str))
check("contains pipe (Markdown table)", "|" in sof)
check("contains certainty symbol ⊕",  "⊕" in sof)
check("contains Primary Outcome",      "Primary Outcome" in sof)
check("contains Secondary Outcome",    "Secondary Outcome" in sof)
check("contains 'moderate'",           "moderate" in sof)
check("contains 'low'",                "low" in sof)
check("contains n_studies 5",          "5" in sof)
check("contains total_n 1200",         "1200" in sof)
check("contains pooled -0.47",         "-0.47" in sof)
check("has header separator row",      "|---" in sof or "| ---" in sof or "|:---" in sof)


# ===========================================================================
# assemble_report
# ===========================================================================
print("\n--- assemble_report ---")

result = assemble_report(
    pico=pico,
    search=search,
    prisma_counts=prisma_counts,
    characteristics_table=format_characteristics_table(char_studies),
    rob_summary=rob_summary,
    outcomes=outcomes_for_report,
    sensitivity=sensitivity,
    publication_bias=publication_bias,
    prisma_svg=None,
    rob_svg=None,
)

check("returns a dict",                isinstance(result, dict))
check("has 'markdown' key",            "markdown" in result)
check("has 'json' key",                "json" in result)

md = result["markdown"]
check("markdown is a string",          isinstance(md, str))
check("markdown contains report title", "# Meta-Analysis Report" in md)
check("markdown contains PRISMA",      "PRISMA" in md)
check("markdown contains Disclaimer",  "Disclaimer" in md)
check("markdown contains GRADE Summary", "GRADE Summary" in md)
check("markdown contains Search Strategy", "Search Strategy" in md)
check("markdown contains Characteristics", "Characteristics" in md)
check("markdown contains Risk of Bias", "Risk of Bias" in md or "risk of bias" in md.lower())
check("markdown contains Results",     "## Results" in md)
check("markdown contains Sensitivity", "Sensitivity" in md)
check("markdown contains Publication Bias", "Publication Bias" in md)
check("markdown contains pico question", pico["question"] in md)
check("markdown contains search query",
      '("Drug A"' in md or "Drug A" in md)
check("markdown contains 'Narrative summary'", "Narrative summary" in md)
check("markdown contains Primary Outcome", "Primary Outcome" in md)
check("markdown contains pooled -0.47", "-0.47" in md)
check("markdown contains I²",          "I²" in md or "I2" in md)
check("markdown contains Prediction interval", "Prediction interval" in md or "prediction interval" in md.lower())

j = result["json"]
check("json is a dict",                isinstance(j, dict))
check("json has 'pico' key",           "pico" in j)
check("json has 'search' key",         "search" in j)
check("json has 'prisma' key",         "prisma" in j)
check("json has 'studies' key",        "studies" in j)
check("json has 'outcomes' key",       "outcomes" in j)
check("json has 'grade_summary' key",  "grade_summary" in j)
check("json has 'publication_bias' key", "publication_bias" in j)

j_outcomes = j["outcomes"]
check("json outcomes is a list",       isinstance(j_outcomes, list))
check("json outcomes non-empty",       len(j_outcomes) > 0)

o0 = j_outcomes[0]
check("outcome has 'name' key",        "name" in o0)
check("outcome has 'pooling' key",     "pooling" in o0)
check("outcome has 'heterogeneity' key", "heterogeneity" in o0)
check("outcome has 'grade' key",       "grade" in o0)

# Test with prisma_svg provided
result2 = assemble_report(
    pico=pico,
    search=search,
    prisma_counts=prisma_counts,
    characteristics_table=format_characteristics_table(char_studies),
    rob_summary=rob_summary,
    outcomes=outcomes_for_report,
    sensitivity=sensitivity,
    publication_bias=publication_bias,
    prisma_svg="<svg>mock</svg>",
    rob_svg="<svg>mock_rob</svg>",
)
check("works with prisma_svg provided", "markdown" in result2 and "json" in result2)
check("SVG content included in markdown when provided",
      "<svg>mock</svg>" in result2["markdown"] or "PRISMA" in result2["markdown"])


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
