"""
test_sensitivity.py — Tests for sensitivity.py sensitivity analysis module.

TDD: run first to verify failures, then implement sensitivity.py, then verify passes.

Run from repo root:
    python tests/test_sensitivity.py
"""

import math
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "meta-analyst"))

from pipeline.sensitivity import (
    leave_one_out,
    exclude_high_rob,
    fixed_vs_random_comparison,
)
from pipeline.pooling import pool_random_effects_dl

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


# ---------------------------------------------------------------------------
# Dataset: 5 studies
# ---------------------------------------------------------------------------
effects = [-0.8873, -0.5108, -0.2231, -0.6931, -0.3567]
ses     = [0.3550,  0.3020,  0.2500,  0.4120,  0.2800]
labels  = ["Study A", "Study B", "Study C", "Study D", "Study E"]

# Full pooling for reference
full_re = pool_random_effects_dl(effects, ses)
full_pooled = full_re["pooled"]
full_p = full_re["p_value"]


# ===========================================================================
# leave_one_out
# ===========================================================================
print("\n--- leave_one_out ---")

loo = leave_one_out(effects, ses, study_labels=labels)

# Returns exactly 5 results
check("LOO returns 5 results", len(loo), 5)

# Each result has required keys
required_keys = {"excluded_study", "pooled", "ci_lower", "ci_upper", "p_value",
                 "direction_changed", "significance_changed"}
for i, result in enumerate(loo):
    for key in required_keys:
        check(f"LOO result[{i}] has key '{key}'", key in result, True)

# With labels, excluded_study shows label names
check("LOO result[0] excluded_study = 'Study A'", loo[0]["excluded_study"], "Study A")
check("LOO result[1] excluded_study = 'Study B'", loo[1]["excluded_study"], "Study B")
check("LOO result[4] excluded_study = 'Study E'", loo[4]["excluded_study"], "Study E")

# All pooled estimates should be negative (removing any one study won't change direction)
for i, result in enumerate(loo):
    check(f"LOO result[{i}] pooled < 0", result["pooled"] < 0, True)

# No single removal changes direction (all effects negative)
for i, result in enumerate(loo):
    check(f"LOO result[{i}] direction_changed = False", result["direction_changed"], False)

# Removing Study A (most extreme, most negative) shifts pooled toward null (less negative)
# loo[0] excludes Study A; its pooled should be less negative than full_pooled
check("LOO removing Study A shifts toward null", loo[0]["pooled"] > full_pooled, True)

# Leave-one-out without labels: excluded_study uses index
loo_no_labels = leave_one_out(effects, ses)
check("LOO no labels result[0] excluded_study = 0", loo_no_labels[0]["excluded_study"], 0)
check("LOO no labels result[3] excluded_study = 3", loo_no_labels[3]["excluded_study"], 3)

# Each LOO pool uses k-1=4 studies (verified implicitly by checking CI width wider than k=5)
# With fewer studies, SE should generally be larger
# Check that LOO results have valid CI (lower < pooled < upper)
for i, result in enumerate(loo):
    check(f"LOO result[{i}] ci_lower < pooled", result["ci_lower"] < result["pooled"], True)
    check(f"LOO result[{i}] ci_upper > pooled", result["ci_upper"] > result["pooled"], True)

# significance_changed: full pooling is significant (p < 0.05); check type is bool
for i, result in enumerate(loo):
    check(f"LOO result[{i}] significance_changed is bool", isinstance(result["significance_changed"], bool), True)


# ===========================================================================
# exclude_high_rob
# ===========================================================================
print("\n--- exclude_high_rob ---")

rob_mixed = ["low", "low", "high", "low", "high"]  # Studies C and E are high
rob_all_low = ["low", "low", "low", "low", "low"]
rob_all_high = ["high", "high", "high", "high", "high"]

# Mixed: n_remaining=3, n_excluded=2
result_mixed = exclude_high_rob(effects, ses, rob_mixed, study_labels=labels)
check("RoB mixed n_remaining=3", result_mixed["n_remaining"], 3)
check("RoB mixed n_excluded=2", result_mixed["n_excluded"], 2)
check("RoB mixed pooled is float", isinstance(result_mixed["pooled"], float), True)
check("RoB mixed pooled < 0 (remaining studies all negative)", result_mixed["pooled"] < 0, True)
check("RoB mixed has ci_lower", "ci_lower" in result_mixed, True)
check("RoB mixed has ci_upper", "ci_upper" in result_mixed, True)
check("RoB mixed has p_value", "p_value" in result_mixed, True)
check("RoB mixed has changed_significance", "changed_significance" in result_mixed, True)
check("RoB mixed changed_significance is bool", isinstance(result_mixed["changed_significance"], bool), True)

# All low: n_remaining=5, n_excluded=0, matches full pooling
result_all_low = exclude_high_rob(effects, ses, rob_all_low)
check("RoB all low n_remaining=5", result_all_low["n_remaining"], 5)
check("RoB all low n_excluded=0", result_all_low["n_excluded"], 0)
check("RoB all low pooled matches full RE", result_all_low["pooled"], full_pooled, tol=0.0001)
check("RoB all low p_value matches full RE", result_all_low["p_value"], full_p, tol=0.0001)

# All high: n_remaining=0, pooled=None
result_all_high = exclude_high_rob(effects, ses, rob_all_high)
check("RoB all high n_remaining=0", result_all_high["n_remaining"], 0)
check("RoB all high pooled=None", result_all_high["pooled"], None)

# All high result should still have the structural keys
check("RoB all high has n_excluded", "n_excluded" in result_all_high, True)
check("RoB all high n_excluded=5", result_all_high["n_excluded"], 5)


# ===========================================================================
# fixed_vs_random_comparison
# ===========================================================================
print("\n--- fixed_vs_random_comparison ---")

fvr = fixed_vs_random_comparison(effects, ses)

# Both should be negative
check("FvR fixed_pooled < 0", fvr["fixed_pooled"] < 0, True)
check("FvR random_pooled < 0", fvr["random_pooled"] < 0, True)

# divergence is abs difference between fixed and random pooled
expected_divergence = abs(fvr["fixed_pooled"] - fvr["random_pooled"])
check("FvR divergence = abs(fixed-random)", fvr["divergence"], expected_divergence, tol=0.0001)

# fixed_ci has lower and upper keys
check("FvR fixed_ci has lower", "lower" in fvr["fixed_ci"], True)
check("FvR fixed_ci has upper", "upper" in fvr["fixed_ci"], True)

# random_ci has lower and upper keys
check("FvR random_ci has lower", "lower" in fvr["random_ci"], True)
check("FvR random_ci has upper", "upper" in fvr["random_ci"], True)

# small_study_flag is bool
check("FvR small_study_flag is bool", isinstance(fvr["small_study_flag"], bool), True)

# For this dataset with moderate heterogeneity, divergence should be small
check("FvR divergence >= 0", fvr["divergence"] >= 0, True)

# fixed CI should be narrower than or equal to random CI (fixed-effect CI is typically tighter)
fixed_width = fvr["fixed_ci"]["upper"] - fvr["fixed_ci"]["lower"]
random_width = fvr["random_ci"]["upper"] - fvr["random_ci"]["lower"]
check("FvR fixed CI <= random CI width", fixed_width <= random_width + 1e-9, True)

# Verify fixed_pooled matches pool_fixed_effect_iv output
from pipeline.pooling import pool_fixed_effect_iv
fe_ref = pool_fixed_effect_iv(effects, ses)
check("FvR fixed_pooled matches FE pooled", fvr["fixed_pooled"], fe_ref["pooled"], tol=0.0001)

# Verify random_pooled matches pool_random_effects_dl output
check("FvR random_pooled matches RE pooled", fvr["random_pooled"], full_pooled, tol=0.0001)


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
