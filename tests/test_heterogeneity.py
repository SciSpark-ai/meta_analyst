"""
test_heterogeneity.py — Tests for heterogeneity.py module.

TDD: run first to verify failures, then implement heterogeneity.py, then verify passes.

Run from repo root:
    python tests/test_heterogeneity.py
"""

import math
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "meta-analyst"))

from pipeline.heterogeneity import (
    cochrans_q, i_squared, tau_squared_dl, h_squared, prediction_interval,
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
    else:
        ok = got == expected
    status = "✅" if ok else "❌"
    if not ok:
        FAIL += 1
    else:
        PASS += 1
    print(f"  {status} {name}: got={got}, expected={expected}")


# ---------------------------------------------------------------------------
# Dataset A — 5 studies, moderate heterogeneity (same as pooling tests)
# ---------------------------------------------------------------------------
effects = [-0.8873, -0.5108, -0.2231, -0.6931, -0.3567]
ses     = [ 0.3550,  0.3020,  0.2500,  0.4120,  0.2800]

# Pre-compute expected fixed-effect weights for reference
_w = [1.0 / s**2 for s in ses]
_sum_w = sum(_w)
_theta_fe = sum(wi * ei for wi, ei in zip(_w, effects)) / _sum_w
_q_expected = sum(wi * (ei - _theta_fe) ** 2 for wi, ei in zip(_w, effects))
_df_expected = len(effects) - 1  # k - 1 = 4


# ===========================================================================
# cochrans_q
# ===========================================================================
print("\n--- cochrans_q ---")

q_result = cochrans_q(effects, ses)

# Q > 0 (studies differ)
check("Q > 0", q_result["q"] > 0, True)

# df = k - 1 = 4
check("df = 4", q_result["df"], 4)

# p_value is a valid probability
check("p_value >= 0", q_result["p_value"] >= 0, True)
check("p_value <= 1", q_result["p_value"] <= 1.0, True)

# Q matches formula exactly
check("Q value", q_result["q"], _q_expected, tol=0.001)

# p_value < 1 and > 0 (meaningful result)
check("p_value > 0", q_result["p_value"] > 0, True)
check("p_value < 1", q_result["p_value"] < 1, True)

# Required keys present
check("has key q", "q" in q_result, True)
check("has key df", "df" in q_result, True)
check("has key p_value", "p_value" in q_result, True)


# ===========================================================================
# i_squared
# ===========================================================================
print("\n--- i_squared ---")

isq_result = i_squared(q_result["q"], q_result["df"])

# I² in [0, 100]
check("I² >= 0", isq_result["i_squared"] >= 0, True)
check("I² <= 100", isq_result["i_squared"] <= 100.0, True)

# Required keys
check("has key i_squared", "i_squared" in isq_result, True)
check("has key interpretation", "interpretation" in isq_result, True)

# Interpretation is one of valid categories
valid_interps = {"low", "moderate", "substantial", "considerable"}
check("interpretation is valid", isq_result["interpretation"] in valid_interps, True)

# Edge case: Q = 0 → I² = 0, interpretation = "low"
isq_zero = i_squared(0.0, 4)
check("I² = 0 when Q=0", isq_zero["i_squared"], 0.0, tol=0.0001)
check("interpretation low when Q=0", isq_zero["interpretation"], "low")

# Edge case: Q = df → I² = 0 (boundary, no excess heterogeneity)
isq_boundary = i_squared(4.0, 4)
check("I² = 0 when Q=df", isq_boundary["i_squared"], 0.0, tol=0.0001)
check("interpretation low when Q=df", isq_boundary["interpretation"], "low")

# Edge case: Q = 2*df → I² = 50%
isq_half = i_squared(8.0, 4)
check("I² = 50 when Q=2*df", isq_half["i_squared"], 50.0, tol=0.001)
check("interpretation moderate when I²=50", isq_half["interpretation"], "moderate")

# Interpretation boundaries per Cochrane Handbook 10.10.2
# I² < 40 → "low"
isq_low = i_squared(5.0, 4)  # Q=5, df=4 → I²=(5-4)/5*100=20 → "low"
check("I² < 40 is low", isq_low["interpretation"], "low")

# 40 <= I² < 60 → "moderate"
# I² = 50 → Q = 2*df = 8, df = 4
check("I² = 50 is moderate", isq_half["interpretation"], "moderate")

# 60 <= I² < 75 → "substantial"
# I² = 66.67 → (Q-df)/Q = 2/3 → Q = 3*df = 12, df=4
isq_substantial = i_squared(12.0, 4)
check("I² = 66.67 is substantial", isq_substantial["interpretation"], "substantial")

# I² >= 75 → "considerable"
# I² = 75 → (Q-df)/Q = 0.75 → Q = 4*df = 16, df=4
isq_considerable = i_squared(16.0, 4)
check("I² >= 75 is considerable", isq_considerable["i_squared"] >= 75.0 - 0.001, True)
check("I² = 75 is considerable", isq_considerable["interpretation"], "considerable")


# ===========================================================================
# tau_squared_dl
# ===========================================================================
print("\n--- tau_squared_dl ---")

weights = [1.0 / s**2 for s in ses]
tau_sq = tau_squared_dl(q_result["q"], q_result["df"], weights)

# tau² >= 0
check("tau² >= 0", tau_sq >= 0, True)

# tau² = 0 when Q <= df (no excess heterogeneity)
tau_sq_zero = tau_squared_dl(3.0, 4, weights)  # Q < df
check("tau² = 0 when Q < df", tau_sq_zero, 0.0, tol=0.0001)

tau_sq_boundary = tau_squared_dl(4.0, 4, weights)  # Q = df
check("tau² = 0 when Q = df", tau_sq_boundary, 0.0, tol=0.0001)

# Consistency: tau² matches the value from pool_random_effects_dl
from pipeline.pooling import pool_random_effects_dl
re_result = pool_random_effects_dl(effects, ses)
check("tau² consistent with pooling module", tau_sq, re_result["tau_sq"], tol=0.001)

# tau² is a float
check("tau² is float", isinstance(tau_sq, float), True)


# ===========================================================================
# h_squared
# ===========================================================================
print("\n--- h_squared ---")

h_sq = h_squared(q_result["q"], q_result["df"])

# H² = Q/df (no minimum constraint; H² < 1 is possible when Q < df)
check("H² > 0", h_sq > 0, True)

# H² = 1 when Q = df (no heterogeneity)
h_sq_one = h_squared(4.0, 4)
check("H² = 1 when Q=df", h_sq_one, 1.0, tol=0.0001)

# H² = Q/df when df > 0
check("H² = Q/df", h_sq, q_result["q"] / q_result["df"], tol=0.0001)

# Edge case: df = 0 → H² = 1.0
h_sq_zero_df = h_squared(0.0, 0)
check("H² = 1.0 when df=0", h_sq_zero_df, 1.0, tol=0.0001)

# H² is a float
check("H² is float", isinstance(h_sq, float), True)


# ===========================================================================
# prediction_interval
# ===========================================================================
print("\n--- prediction_interval ---")

# Use RE result from pooling module for reference values
pooled = re_result["pooled"]
se_pooled = re_result["se"]
tau_sq_val = re_result["tau_sq"]
k = len(effects)

pi = prediction_interval(pooled, se_pooled, tau_sq_val, k)

# PI should be returned (k=5 >= 3)
check("PI is not None for k=5", pi is not None, True)

# PI should be wider than CI (includes between-study variance)
ci_width = (pooled + 1.96 * se_pooled) - (pooled - 1.96 * se_pooled)
pi_width = pi["upper"] - pi["lower"]
check("PI wider than CI", pi_width >= ci_width - 1e-9, True)

# PI contains pooled estimate
check("PI lower < pooled", pi["lower"] < pooled, True)
check("PI upper > pooled", pi["upper"] > pooled, True)

# Required keys
check("PI has key lower", "lower" in pi, True)
check("PI has key upper", "upper" in pi, True)

# k < 3: return None
pi_k2 = prediction_interval(pooled, se_pooled, tau_sq_val, 2)
check("PI is None for k=2", pi_k2 is None, True)

pi_k1 = prediction_interval(pooled, se_pooled, tau_sq_val, 1)
check("PI is None for k=1", pi_k1 is None, True)

# When tau²=0, PI collapses toward CI (but still uses t instead of z)
pi_no_tau = prediction_interval(pooled, se_pooled, 0.0, k)
check("PI no_tau is not None", pi_no_tau is not None, True)
# PI with tau²=0 should have width >= CI width (t > 1.96 for small df)
pi_no_tau_width = pi_no_tau["upper"] - pi_no_tau["lower"]
check("PI tau²=0 width >= CI width", pi_no_tau_width >= ci_width - 1e-9, True)

# PI matches pooling module's prediction interval
pi_pooling = re_result["prediction_interval"]
check("PI lower matches pooling module", pi["lower"], pi_pooling["lower"], tol=0.001)
check("PI upper matches pooling module", pi["upper"], pi_pooling["upper"], tol=0.001)


# ===========================================================================
# Edge cases
# ===========================================================================
print("\n--- edge cases ---")

# Single study (k=1): Q=0, df=0, I²=0
q_single = cochrans_q([-0.5], [0.3])
check("k=1 Q=0", q_single["q"], 0.0, tol=0.0001)
check("k=1 df=0", q_single["df"], 0)
check("k=1 I²=0", i_squared(q_single["q"], q_single["df"])["i_squared"], 0.0, tol=0.0001)

# Two identical studies: Q≈0, I²=0, tau²=0
q_ident = cochrans_q([-0.5, -0.5], [0.3, 0.3])
check("k=2 identical Q≈0", q_ident["q"] < 1e-9, True)
check("k=2 identical df=1", q_ident["df"], 1)
isq_ident = i_squared(q_ident["q"], q_ident["df"])
check("k=2 identical I²=0", isq_ident["i_squared"], 0.0, tol=0.0001)
w_ident = [1.0 / s**2 for s in [0.3, 0.3]]
tau_ident = tau_squared_dl(q_ident["q"], q_ident["df"], w_ident)
check("k=2 identical tau²=0", tau_ident, 0.0, tol=0.0001)

# Extreme heterogeneity: effects widely spread → I² > 75, "considerable"
extreme_effects = [-2.0, -1.0, 0.0, 1.0, 2.0]
extreme_ses     = [0.2, 0.2, 0.2, 0.2, 0.2]
q_extreme = cochrans_q(extreme_effects, extreme_ses)
isq_extreme = i_squared(q_extreme["q"], q_extreme["df"])
check("extreme I² > 75", isq_extreme["i_squared"] > 75.0, True)
check("extreme interpretation=considerable", isq_extreme["interpretation"], "considerable")

# Homogeneous: all effects identical → Q≈0, I²=0, tau²=0
homo_effects = [-0.5, -0.5, -0.5, -0.5]
homo_ses     = [0.2, 0.3, 0.25, 0.35]
q_homo = cochrans_q(homo_effects, homo_ses)
check("homogeneous Q≈0", q_homo["q"] < 1e-9, True)
check("homogeneous I²=0", i_squared(q_homo["q"], q_homo["df"])["i_squared"], 0.0, tol=0.0001)
w_homo = [1.0 / s**2 for s in homo_ses]
tau_homo = tau_squared_dl(q_homo["q"], q_homo["df"], w_homo)
check("homogeneous tau²=0", tau_homo, 0.0, tol=0.0001)


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
