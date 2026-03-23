"""
test_pooling.py — Tests for pooling.py meta-analytic pooling module.

TDD: run first to verify failures, then implement pooling.py, then verify passes.

Run from repo root:
    python tests/test_pooling.py
"""

import math
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "meta-analyst"))

from pipeline.pooling import (
    pool_fixed_effect_iv,
    pool_random_effects_dl,
    pool_mantel_haenszel,
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
# Dataset A — 5 studies, moderate heterogeneity
# ---------------------------------------------------------------------------
# Log OR values and SEs (pre-computed from 2x2 tables)
effects = [-0.8873, -0.5108, -0.2231, -0.6931, -0.3567]
ses     = [ 0.3550,  0.3020,  0.2500,  0.4120,  0.2800]

# Pre-compute expected fixed-effect values for reference
import math as _math
_w = [1 / s**2 for s in ses]
_sum_w = sum(_w)
_theta_fe = sum(wi * ei for wi, ei in zip(_w, effects)) / _sum_w
_se_fe = _math.sqrt(1 / _sum_w)


# ===========================================================================
# pool_fixed_effect_iv
# ===========================================================================
print("\n--- pool_fixed_effect_iv ---")

fe = pool_fixed_effect_iv(effects, ses)

# Pooled effect should be negative (all studies favor intervention)
check("FE pooled < 0", fe["pooled"] < 0, True)

# SE should be less than the smallest individual SE (pooling reduces uncertainty)
check("FE se < min(ses)", fe["se"] < min(ses), True)

# 95% CI should not cross 0 (significant result, both bounds negative)
check("FE ci_lower < 0", fe["ci_lower"] < 0, True)
check("FE ci_upper < 0", fe["ci_upper"] < 0, True)

# p-value should be < 0.05
check("FE p_value < 0.05", fe["p_value"] < 0.05, True)

# Weights should sum to sum(1/SE_i^2)
check("FE weights sum", sum(fe["weights"]), _sum_w, tol=0.001)

# Pooled estimate matches formula
check("FE pooled value", fe["pooled"], _theta_fe, tol=0.0001)

# SE matches formula
check("FE se value", fe["se"], _se_fe, tol=0.0001)

# CI bounds: theta +/- 1.96 * se
check("FE ci_lower value", fe["ci_lower"], _theta_fe - 1.96 * _se_fe, tol=0.0001)
check("FE ci_upper value", fe["ci_upper"], _theta_fe + 1.96 * _se_fe, tol=0.0001)

# Required keys present
check("FE has weights key", "weights" in fe, True)
check("FE weights length", len(fe["weights"]), 5)

# Individual weight values
for i, (wi_got, wi_exp) in enumerate(zip(fe["weights"], _w)):
    check(f"FE weight[{i}]", wi_got, wi_exp, tol=0.0001)


# ===========================================================================
# pool_random_effects_dl (DerSimonian-Laird)
# ===========================================================================
print("\n--- pool_random_effects_dl ---")

re = pool_random_effects_dl(effects, ses)

# tau^2 >= 0 (non-negative heterogeneity)
check("RE tau_sq >= 0", re["tau_sq"] >= 0, True)

# Q statistic > 0
check("RE q_stat > 0", re["q_stat"] > 0, True)

# RE pooled should be between min and max individual effects
check("RE pooled >= min(effects)", re["pooled"] >= min(effects), True)
check("RE pooled <= max(effects)", re["pooled"] <= max(effects), True)

# RE CI should be wider than or equal to FE CI
fe_width = fe["ci_upper"] - fe["ci_lower"]
re_width = re["ci_upper"] - re["ci_lower"]
check("RE CI >= FE CI width", re_width >= fe_width - 1e-9, True)

# Prediction interval should be wider than CI
pi = re["prediction_interval"]
ci_w = re["ci_upper"] - re["ci_lower"]
pi_w = pi["upper"] - pi["lower"]
check("PI wider than CI", pi_w >= ci_w - 1e-9, True)

# p_value < 0.05
check("RE p_value < 0.05", re["p_value"] < 0.05, True)

# Weights should sum to sum(1/(SE_i^2 + tau^2))
tau_sq = re["tau_sq"]
_w_re = [1 / (s**2 + tau_sq) for s in ses]
_sum_w_re = sum(_w_re)
check("RE weights sum", sum(re["weights"]), _sum_w_re, tol=0.001)

# Required keys
check("RE has tau_sq", "tau_sq" in re, True)
check("RE has q_stat", "q_stat" in re, True)
check("RE has prediction_interval", "prediction_interval" in re, True)
check("RE has weights", "weights" in re, True)
check("RE weights length", len(re["weights"]), 5)


# ===========================================================================
# pool_mantel_haenszel
# ===========================================================================
print("\n--- pool_mantel_haenszel (OR) ---")

tables = [
    (15, 85, 30, 70),   # Study 1: OR ≈ 0.41
    (20, 80, 30, 70),   # Study 2: OR ≈ 0.58
    (10, 90, 12, 88),   # Study 3: OR ≈ 0.81
    (25, 75, 40, 60),   # Study 4: OR ≈ 0.50
    (18, 82, 24, 76),   # Study 5: OR ≈ 0.69
]

mh = pool_mantel_haenszel(tables, measure="OR")

# MH OR should be < 1 (favors intervention)
check("MH OR < 1", mh["pooled"] < 1.0, True)

# MH OR should be positive
check("MH OR > 0", mh["pooled"] > 0, True)

# p_value < 0.05 (should be significant)
check("MH p_value < 0.05", mh["p_value"] < 0.05, True)

# log_pooled should be ln(pooled)
check("MH log_pooled = log(pooled)", mh["log_pooled"], _math.log(mh["pooled"]), tol=0.0001)

# CI should be < 1 (both bounds, significant)
check("MH ci_lower < 1", mh["ci_lower"] < 1.0, True)

# CI lower should be > 0
check("MH ci_lower > 0", mh["ci_lower"] > 0, True)

# Required keys
check("MH has pooled", "pooled" in mh, True)
check("MH has se", "se" in mh, True)
check("MH has ci_lower", "ci_lower" in mh, True)
check("MH has ci_upper", "ci_upper" in mh, True)
check("MH has p_value", "p_value" in mh, True)
check("MH has log_pooled", "log_pooled" in mh, True)

# MH OR should be close to IV pooled OR (exp of fixed-effect log OR)
fe_or = _math.exp(fe["pooled"])
check("MH OR close to IV OR", abs(mh["pooled"] - fe_or) < 0.15, True)

print("\n--- pool_mantel_haenszel (RR) ---")
mh_rr = pool_mantel_haenszel(tables, measure="RR")

# MH RR should be < 1
check("MH RR < 1", mh_rr["pooled"] < 1.0, True)
check("MH RR > 0", mh_rr["pooled"] > 0, True)
check("MH RR p_value < 0.05", mh_rr["p_value"] < 0.05, True)
check("MH RR log_pooled = log(pooled)", mh_rr["log_pooled"], _math.log(mh_rr["pooled"]), tol=0.0001)


# ===========================================================================
# Edge cases
# ===========================================================================
print("\n--- edge cases ---")

# Single study: pooled = effect, SE = its SE
fe1 = pool_fixed_effect_iv([-0.5], [0.3])
check("k=1 FE pooled", fe1["pooled"], -0.5, tol=0.0001)
check("k=1 FE se", fe1["se"], 0.3, tol=0.0001)

re1 = pool_random_effects_dl([-0.5], [0.3])
check("k=1 RE pooled", re1["pooled"], -0.5, tol=0.0001)
check("k=1 RE se", re1["se"], 0.3, tol=0.0001)
check("k=1 RE tau_sq = 0", re1["tau_sq"], 0.0, tol=0.0001)

# Two identical studies: pooled = same effect, SE = original_se / sqrt(2)
fe2 = pool_fixed_effect_iv([-0.5, -0.5], [0.3, 0.3])
check("k=2 identical FE pooled", fe2["pooled"], -0.5, tol=0.0001)
check("k=2 identical FE se", fe2["se"], 0.3 / _math.sqrt(2), tol=0.0001)

# Homogeneous studies (all same effect): tau^2 should be 0, RE = FE
same_effects = [-0.5, -0.5, -0.5, -0.5]
same_ses     = [0.2,   0.3,  0.25,  0.35]
re_homo = pool_random_effects_dl(same_effects, same_ses)
fe_homo = pool_fixed_effect_iv(same_effects, same_ses)
check("homogeneous tau_sq = 0", re_homo["tau_sq"], 0.0, tol=0.0001)
check("homogeneous RE pooled = FE pooled", re_homo["pooled"], fe_homo["pooled"], tol=0.0001)

# k=2 for DL: prediction interval should be skipped (k-2 = 0 df)
re2 = pool_random_effects_dl([-0.5, -0.6], [0.3, 0.25])
check("k=2 prediction_interval is None", re2["prediction_interval"] is None, True)

# k=1 for DL: prediction interval should also be skipped
check("k=1 prediction_interval is None", re1["prediction_interval"] is None, True)


# ===========================================================================
# Consistency: FE == RE when tau^2 = 0
# ===========================================================================
print("\n--- consistency: FE == RE when tau^2=0 ---")

# Use homogeneous dataset where tau^2 is forced to 0
re_c = pool_random_effects_dl(same_effects, same_ses)
fe_c = pool_fixed_effect_iv(same_effects, same_ses)

check("consistency tau_sq=0", re_c["tau_sq"], 0.0, tol=0.0001)
check("consistency FE=RE pooled", re_c["pooled"], fe_c["pooled"], tol=0.0001)
check("consistency FE=RE se", re_c["se"], fe_c["se"], tol=0.0001)
check("consistency FE=RE ci_lower", re_c["ci_lower"], fe_c["ci_lower"], tol=0.0001)
check("consistency FE=RE ci_upper", re_c["ci_upper"], fe_c["ci_upper"], tol=0.0001)


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
