"""
test_publication_bias.py — Tests for publication_bias.py module.

TDD: run first to verify failures, then implement publication_bias.py, then verify passes.

Run from repo root:
    python tests/test_publication_bias.py
"""

import math
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "meta-analyst"))

from pipeline.publication_bias import (
    eggers_test,
    funnel_plot_data,
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


# ---------------------------------------------------------------------------
# Symmetric dataset (no publication bias) — 12 studies
# Effects drawn as constant true effect (-0.5) plus small noise independent of SE,
# so effect magnitude does not correlate with study size (Egger-symmetric by construction).
# ---------------------------------------------------------------------------
symmetric_effects = [-0.4851, -0.5041, -0.4806, -0.4543, -0.5070, -0.5070,
                     -0.4526, -0.4770, -0.5141, -0.4837, -0.5139, -0.5140]
symmetric_ses     = [0.10,  0.15,  0.12,  0.20,  0.11,  0.14,  0.18,  0.13,  0.16,  0.12,  0.19,  0.11]

# ---------------------------------------------------------------------------
# Asymmetric / biased dataset — 12 studies
# ---------------------------------------------------------------------------
biased_effects = [-1.2, -1.0, -0.9, -0.8, -0.5, -0.45, -0.4, -0.35, -0.3, -0.3, -0.25, -0.2]
biased_ses     = [0.40, 0.35, 0.30, 0.28, 0.15, 0.14,  0.12, 0.11,  0.10, 0.10, 0.09,  0.08]


# ===========================================================================
# eggers_test — symmetric data (k=12, no bias)
# ===========================================================================
print("\n--- eggers_test: symmetric data ---")

sym_result = eggers_test(symmetric_effects, symmetric_ses)

# Not skipped (k=12 >= 10)
check("Sym skipped=False", sym_result["skipped"], False)

# reason should be None when not skipped
check("Sym reason=None", sym_result["reason"], None)

# Has required keys
check("Sym has intercept", "intercept" in sym_result, True)
check("Sym has se", "se" in sym_result, True)
check("Sym has p_value", "p_value" in sym_result, True)

# p_value > 0.10 (no significant asymmetry)
check("Sym p_value > 0.10 (not significant)", sym_result["p_value"] > 0.10, True)


# ===========================================================================
# eggers_test — biased data (k=12, asymmetry)
# ===========================================================================
print("\n--- eggers_test: biased data ---")

biased_result = eggers_test(biased_effects, biased_ses)

# Not skipped (k=12 >= 10)
check("Biased skipped=False", biased_result["skipped"], False)

# reason should be None when not skipped
check("Biased reason=None", biased_result["reason"], None)

# Has required keys
check("Biased has intercept", "intercept" in biased_result, True)
check("Biased has se", "se" in biased_result, True)
check("Biased has p_value", "p_value" in biased_result, True)

# p_value < 0.10 (significant asymmetry detected)
check("Biased p_value < 0.10 (significant asymmetry)", biased_result["p_value"] < 0.10, True)


# ===========================================================================
# eggers_test — k < 10 (skipped)
# ===========================================================================
print("\n--- eggers_test: k < 10 ---")

# Use first 8 studies from symmetric dataset
few_effects = symmetric_effects[:8]
few_ses = symmetric_ses[:8]

few_result = eggers_test(few_effects, few_ses)

# Should be skipped
check("Few skipped=True", few_result["skipped"], True)

# reason should contain "Fewer than 10"
check("Few reason contains 'Fewer than 10'", "Fewer than 10" in few_result["reason"], True)

# skipped result should not have intercept/se/p_value (or have them as None)
# According to spec: return {skipped: True, reason: "..."} — other keys absent or None
# We check that skipped is True and reason is present
check("Few has reason key", "reason" in few_result, True)

# Also test with biased first 8
few_biased_result = eggers_test(biased_effects[:8], biased_ses[:8])
check("Few biased skipped=True", few_biased_result["skipped"], True)
check("Few biased reason contains 'Fewer than 10'", "Fewer than 10" in few_biased_result["reason"], True)

# k=9 should also be skipped
nine_result = eggers_test(symmetric_effects[:9], symmetric_ses[:9])
check("k=9 skipped=True", nine_result["skipped"], True)

# k=10 should NOT be skipped
ten_result = eggers_test(symmetric_effects[:10], symmetric_ses[:10])
check("k=10 skipped=False", ten_result["skipped"], False)


# ===========================================================================
# funnel_plot_data
# ===========================================================================
print("\n--- funnel_plot_data ---")

# Use full pooling for pooled estimate
from pipeline.pooling import pool_random_effects_dl
pooled_sym = pool_random_effects_dl(symmetric_effects, symmetric_ses)["pooled"]
pooled_biased = pool_random_effects_dl(biased_effects, biased_ses)["pooled"]

funnnel_sym = funnel_plot_data(symmetric_effects, symmetric_ses, pooled_sym)

# Number of points equals number of studies
check("Funnel sym points count=12", len(funnnel_sym["points"]), 12)

# Pooled value returned
check("Funnel sym pooled", funnnel_sym["pooled"], pooled_sym, tol=0.0001)

# Each point has effect and se keys
for i, pt in enumerate(funnnel_sym["points"]):
    check(f"Funnel sym point[{i}] has 'effect'", "effect" in pt, True)
    check(f"Funnel sym point[{i}] has 'se'", "se" in pt, True)

# Points match input data
check("Funnel sym point[0] effect", funnnel_sym["points"][0]["effect"], symmetric_effects[0], tol=0.0001)
check("Funnel sym point[0] se", funnnel_sym["points"][0]["se"], symmetric_ses[0], tol=0.0001)
check("Funnel sym point[5] effect", funnnel_sym["points"][5]["effect"], symmetric_effects[5], tol=0.0001)

# pseudo_ci_lines structure
pci = funnnel_sym["pseudo_ci_lines"]
check("Funnel sym has pseudo_ci_lines", "pseudo_ci_lines" in funnnel_sym, True)
check("Funnel pci has se_range", "se_range" in pci, True)
check("Funnel pci has lower_bound", "lower_bound" in pci, True)
check("Funnel pci has upper_bound", "upper_bound" in pci, True)

# se_range is [min, max]
check("Funnel pci se_range[0] = min(ses)", pci["se_range"][0], min(symmetric_ses), tol=0.0001)
check("Funnel pci se_range[1] = max(ses)", pci["se_range"][1], max(symmetric_ses), tol=0.0001)

# lower_bound and upper_bound should have same length
check("Funnel pci lower/upper same length", len(pci["lower_bound"]) == len(pci["upper_bound"]), True)

# Check pseudo CI is symmetric around pooled:
# At each SE, lower_bound[i] = pooled - 1.96 * se_val, upper_bound[i] = pooled + 1.96 * se_val
# We verify the sum of lower + upper = 2 * pooled at each position
for i, (lb, ub) in enumerate(zip(pci["lower_bound"], pci["upper_bound"])):
    midpoint = (lb + ub) / 2.0
    check(f"Funnel pci midpoint[{i}] = pooled", midpoint, pooled_sym, tol=0.0001)

# Funnel plot for biased data
funnel_biased = funnel_plot_data(biased_effects, biased_ses, pooled_biased)
check("Funnel biased points count=12", len(funnel_biased["points"]), 12)
check("Funnel biased pooled", funnel_biased["pooled"], pooled_biased, tol=0.0001)


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
