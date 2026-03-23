"""
test_grade.py — Tests for grade.py module.

TDD: run first to verify failures, then implement grade.py, then verify passes.

Run from repo root:
    python tests/test_grade.py
"""

import math
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "meta-analyst"))

from pipeline.grade import (
    assess_risk_of_bias,
    assess_inconsistency,
    assess_imprecision,
    assess_publication_bias,
    compute_grade,
    grade_summary_row,
)

PASS = 0
FAIL = 0


def check(name, got, expected, tol=0.001):
    global PASS, FAIL
    if isinstance(expected, float) and math.isinf(expected):
        ok = math.isinf(got) and (got > 0) == (expected > 0)
    elif isinstance(expected, float):
        ok = abs(got - expected) <= tol
    elif isinstance(expected, bool):
        ok = bool(got) == expected
    elif expected is None:
        ok = got is None
    else:
        ok = got == expected
    status = "PASS" if ok else "FAIL"
    if not ok:
        FAIL += 1
    else:
        PASS += 1
    print(f"  [{status}] {name}: got={got}, expected={expected}")


# ===========================================================================
# assess_risk_of_bias
# ===========================================================================
print("\n--- assess_risk_of_bias ---")

# All low: 0 high → 0
check("All low", assess_risk_of_bias(["low", "low", "low", "low", "low"]), 0)

# 1/5 high = 20% < 50% → -1
check("1/5 high (20%)", assess_risk_of_bias(["low", "low", "high", "low", "low"]), -1)

# 2/5 high = 40% < 50% → -1
check("2/5 high (40%)", assess_risk_of_bias(["low", "low", "high", "low", "high"]), -1)

# 3/5 high = 60% >= 50% → -2
check("3/5 high (60%)", assess_risk_of_bias(["high", "high", "high", "low", "low"]), -2)

# All high: 5/5 = 100% >= 50% → -2
check("All high", assess_risk_of_bias(["high", "high", "high", "high", "high"]), -2)

# Some concerns only (no high): 0 high → 0
check("Some concerns only", assess_risk_of_bias(["some concerns", "low", "some concerns"]), 0)

# Empty list: 0 high → 0
check("Empty list", assess_risk_of_bias([]), 0)


# ===========================================================================
# assess_inconsistency
# ===========================================================================
print("\n--- assess_inconsistency ---")

check("I2=0", assess_inconsistency(0), 0)
check("I2=30", assess_inconsistency(30), 0)
check("I2=49.9", assess_inconsistency(49.9), 0)
check("I2=50", assess_inconsistency(50), -1)
check("I2=60", assess_inconsistency(60), -1)
check("I2=74.9", assess_inconsistency(74.9), -1)
check("I2=75", assess_inconsistency(75), -2)
check("I2=90", assess_inconsistency(90), -2)


# ===========================================================================
# assess_imprecision
# ===========================================================================
print("\n--- assess_imprecision ---")

# CI does not cross null, OIS met → 0
check(
    "CI no-cross, OIS met",
    assess_imprecision(0.5, 0.9, 1.0, ois=1000, total_n=2000),
    0,
)

# CI crosses null → -1
check(
    "CI crosses null",
    assess_imprecision(0.85, 1.20, 1.0),
    -1,
)

# OIS not met, CI does not cross null → -1
check(
    "OIS not met, CI no-cross",
    assess_imprecision(0.5, 0.9, 1.0, ois=5000, total_n=1000),
    -1,
)

# Both CI crosses null AND OIS not met → -2
check(
    "CI crosses null AND OIS not met",
    assess_imprecision(0.85, 1.20, 1.0, ois=5000, total_n=1000),
    -2,
)

# No OIS provided, CI crosses null → -1 (only crosses-null check)
check(
    "No OIS, CI crosses null",
    assess_imprecision(0.85, 1.20, 1.0),
    -1,
)

# No OIS provided, CI does not cross null → 0
check(
    "No OIS, CI no-cross",
    assess_imprecision(0.5, 0.9, 1.0),
    0,
)


# ===========================================================================
# assess_publication_bias
# ===========================================================================
print("\n--- assess_publication_bias ---")

# k=12, p=0.03 → -1
check("k=12 p=0.03", assess_publication_bias(0.03, 12), -1)

# k=12, p=0.50 → 0
check("k=12 p=0.50", assess_publication_bias(0.50, 12), 0)

# k=8, p=0.01 → 0 (k < 10, can't assess)
check("k=8 p=0.01 (k<10)", assess_publication_bias(0.01, 8), 0)

# k=10, p=0.09 → -1 (boundary: p < 0.10)
check("k=10 p=0.09 (boundary)", assess_publication_bias(0.09, 10), -1)

# k=10, p=0.10 → 0 (not < 0.10)
check("k=10 p=0.10", assess_publication_bias(0.10, 10), 0)


# ===========================================================================
# compute_grade
# ===========================================================================
print("\n--- compute_grade ---")

no_downgrades = {
    "rob": 0,
    "inconsistency": 0,
    "indirectness": 0,
    "imprecision": 0,
    "publication_bias": 0,
}

# High + all zeros → "High"
check(
    "High all zeros",
    compute_grade("High", no_downgrades),
    "High",
)

# High + rob=-1 → "Moderate"
check(
    "High rob=-1",
    compute_grade("High", {**no_downgrades, "rob": -1}),
    "Moderate",
)

# High + rob=-1, inconsistency=-1 → "Low"
check(
    "High rob=-1 inconsistency=-1",
    compute_grade("High", {**no_downgrades, "rob": -1, "inconsistency": -1}),
    "Low",
)

# High + rob=-1, inconsistency=-1, imprecision=-1 → "Very Low"
check(
    "High rob=-1 inconsistency=-1 imprecision=-1",
    compute_grade("High", {**no_downgrades, "rob": -1, "inconsistency": -1, "imprecision": -1}),
    "Very Low",
)

# High + rob=-2, inconsistency=-2 → "Very Low" (can't go below Very Low)
check(
    "High rob=-2 inconsistency=-2 (clamped to Very Low)",
    compute_grade("High", {**no_downgrades, "rob": -2, "inconsistency": -2}),
    "Very Low",
)

# High + all -2 → "Very Low"
check(
    "High all -2",
    compute_grade("High", {
        "rob": -2,
        "inconsistency": -2,
        "indirectness": -2,
        "imprecision": -2,
        "publication_bias": -2,
    }),
    "Very Low",
)


# ===========================================================================
# grade_summary_row
# ===========================================================================
print("\n--- grade_summary_row ---")

row_high = grade_summary_row(
    outcome_name="All-cause mortality",
    n_studies=10,
    total_n=5000,
    pooled_effect=0.75,
    ci_lower=0.65,
    ci_upper=0.87,
    certainty="High",
    downgrade_reasons=[],
)

check("Row has 'outcome'", "outcome" in row_high, True)
check("Row outcome value", row_high["outcome"], "All-cause mortality")
check("Row has 'n_studies'", "n_studies" in row_high, True)
check("Row n_studies value", row_high["n_studies"], 10)
check("Row has 'total_n'", "total_n" in row_high, True)
check("Row total_n value", row_high["total_n"], 5000)
check("Row has 'effect_with_ci'", "effect_with_ci" in row_high, True)
check("Row effect_with_ci formatted", row_high["effect_with_ci"], "0.75 (0.65 to 0.87)")
check("Row has 'certainty'", "certainty" in row_high, True)
check("Row certainty value", row_high["certainty"], "High")
check("Row has 'certainty_symbols'", "certainty_symbols" in row_high, True)
check("Row High symbols", row_high["certainty_symbols"], "⊕⊕⊕⊕")
check("Row has 'downgrade_reasons'", "downgrade_reasons" in row_high, True)
check("Row downgrade_reasons empty list", row_high["downgrade_reasons"], [])

# Moderate
row_mod = grade_summary_row(
    outcome_name="CV death",
    n_studies=5,
    total_n=2000,
    pooled_effect=0.82,
    ci_lower=0.71,
    ci_upper=0.95,
    certainty="Moderate",
    downgrade_reasons=["serious risk of bias"],
)
check("Moderate symbols", row_mod["certainty_symbols"], "⊕⊕⊕◯")
check("Moderate effect_with_ci", row_mod["effect_with_ci"], "0.82 (0.71 to 0.95)")
check("Moderate downgrade_reasons", row_mod["downgrade_reasons"], ["serious risk of bias"])

# Low
row_low = grade_summary_row(
    outcome_name="Hospitalization",
    n_studies=3,
    total_n=800,
    pooled_effect=0.90,
    ci_lower=0.78,
    ci_upper=1.04,
    certainty="Low",
    downgrade_reasons=["serious inconsistency", "serious imprecision"],
)
check("Low symbols", row_low["certainty_symbols"], "⊕⊕◯◯")

# Very Low
row_vl = grade_summary_row(
    outcome_name="Quality of life",
    n_studies=2,
    total_n=300,
    pooled_effect=1.10,
    ci_lower=0.85,
    ci_upper=1.42,
    certainty="Very Low",
    downgrade_reasons=["very serious risk of bias"],
)
check("Very Low symbols", row_vl["certainty_symbols"], "⊕◯◯◯")
check("Very Low effect_with_ci", row_vl["effect_with_ci"], "1.10 (0.85 to 1.42)")


# ===========================================================================
# Summary
# ===========================================================================
print(f"\n{'='*50}")
print(f"TOTAL: {PASS + FAIL} | PASS: {PASS} | FAIL: {FAIL}")
if FAIL == 0:
    print("All tests passed.")
else:
    print(f"{FAIL} test(s) FAILED.")
    sys.exit(1)
