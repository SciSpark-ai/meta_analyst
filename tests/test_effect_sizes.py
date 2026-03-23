import math
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "meta-analyst"))

from pipeline.effect_sizes import (
    compute_log_or, compute_log_rr, compute_rd,
    compute_md, compute_smd, zero_cell_correction,
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
# Zero-cell correction
# ---------------------------------------------------------------------------
print("\n--- zero_cell_correction ---")

a, b, c, d = zero_cell_correction(0, 100, 10, 90)
check("zero-cell a", a, 0.5)
check("zero-cell b", b, 100.5)
check("zero-cell c", c, 10.5)
check("zero-cell d", d, 90.5)

a2, b2, c2, d2 = zero_cell_correction(10, 90, 20, 80)
check("no-correction a", a2, 10.0)
check("no-correction b", b2, 90.0)
check("no-correction c", c2, 20.0)
check("no-correction d", d2, 80.0)

# custom correction value
a3, b3, c3, d3 = zero_cell_correction(0, 10, 5, 5, correction=0.1)
check("custom correction a", a3, 0.1)
check("custom correction b", b3, 10.1)
check("custom correction c", c3, 5.1)
check("custom correction d", d3, 5.1)


# ---------------------------------------------------------------------------
# compute_log_or
# ---------------------------------------------------------------------------
print("\n--- compute_log_or ---")

# Basic case: a=15, b=85, c=30, d=70
# OR = (15*70)/(85*30) = 1050/2550 = 0.41176
# log(OR) = -0.8873, SE = sqrt(1/15 + 1/85 + 1/30 + 1/70) = 0.3953
res = compute_log_or(15, 85, 30, 70)
check("basic log_or", res["log_or"], -0.8873)
# SE = sqrt(1/15 + 1/85 + 1/30 + 1/70) = 0.3550 (task spec had a typo of 0.3953)
expected_se_or = math.sqrt(1/15 + 1/85 + 1/30 + 1/70)
check("basic se", res["se"], expected_se_or)
check("basic or_value", res["or_value"], 0.4118)
check("basic ci_lower < 1", res["ci_lower"] < 1.0, True)
check("basic ci_upper < 1", res["ci_upper"] < 1.0, True)

# Balanced: OR = 1, log(OR) = 0
res2 = compute_log_or(50, 50, 50, 50)
check("balanced log_or", res2["log_or"], 0.0)
check("balanced or_value", res2["or_value"], 1.0)

# Very large effect: a=95, b=5, c=5, d=95
# OR = (95*95)/(5*5) = 361
res3 = compute_log_or(95, 5, 5, 95)
check("large effect or_value", res3["or_value"], 361.0)
check("large effect log_or", res3["log_or"], math.log(361.0))


# ---------------------------------------------------------------------------
# compute_log_rr
# ---------------------------------------------------------------------------
print("\n--- compute_log_rr ---")

# Basic case: a=15, b=85, c=30, d=70
# RR = (15/100) / (30/100) = 0.5, log(RR) = -0.6931
res = compute_log_rr(15, 85, 30, 70)
check("basic log_rr", res["log_rr"], -0.6931)
check("basic rr", res["rr"], 0.5)
check("basic rr ci_lower < 1", res["ci_lower"] < 1.0, True)
check("basic rr ci_upper < 1", res["ci_upper"] < 1.0, True)

# Balanced: RR = 1, log(RR) = 0
res2 = compute_log_rr(50, 50, 50, 50)
check("balanced log_rr", res2["log_rr"], 0.0)
check("balanced rr", res2["rr"], 1.0)

# SE check for basic case:
# SE = sqrt(1/15 - 1/100 + 1/30 - 1/100)
# = sqrt(0.06667 - 0.01 + 0.03333 - 0.01) = sqrt(0.09) = 0.3
expected_se_rr = math.sqrt(1/15 - 1/100 + 1/30 - 1/100)
check("basic rr se", res["se"], expected_se_rr)


# ---------------------------------------------------------------------------
# compute_rd
# ---------------------------------------------------------------------------
print("\n--- compute_rd ---")

# Basic case: a=15, b=85, c=30, d=70
# RD = 15/100 - 30/100 = -0.15
res = compute_rd(15, 85, 30, 70)
check("basic rd", res["rd"], -0.15)
check("basic rd ci_lower < 0", res["ci_lower"] < 0.0, True)
check("basic rd ci_upper < 0", res["ci_upper"] < 0.0, True)

# SE = sqrt(0.15*0.85/100 + 0.30*0.70/100)
#     = sqrt(0.001275 + 0.0021) = sqrt(0.003375) = 0.05811
expected_se_rd = math.sqrt(0.15 * 0.85 / 100 + 0.30 * 0.70 / 100)
check("basic rd se", res["se"], expected_se_rd)

# Balanced: RD = 0
res2 = compute_rd(50, 50, 50, 50)
check("balanced rd", res2["rd"], 0.0)


# ---------------------------------------------------------------------------
# compute_md
# ---------------------------------------------------------------------------
print("\n--- compute_md ---")

# mean_i=5.2, sd_i=1.1, n_i=50, mean_c=4.8, sd_c=1.2, n_c=50
# MD = 0.4
# SE = sqrt(1.21/50 + 1.44/50) = sqrt(0.0242 + 0.0288) = sqrt(0.053) = 0.2302
res = compute_md(5.2, 1.1, 50, 4.8, 1.2, 50)
check("basic md", res["md"], 0.4)
expected_se_md = math.sqrt(1.21/50 + 1.44/50)
check("basic md se", res["se"], expected_se_md)
check("basic md se numeric", res["se"], 0.2302)
# CI lower = 0.4 - 1.96*0.2302 ≈ -0.051 (crosses zero, so lower < 0)
check("basic md ci_lower < 0", res["ci_lower"] < 0.0, True)
check("basic md ci_upper > 0", res["ci_upper"] > 0.0, True)

# No difference
res2 = compute_md(5.0, 1.0, 30, 5.0, 1.0, 30)
check("no-diff md", res2["md"], 0.0)


# ---------------------------------------------------------------------------
# compute_smd (Hedges' g)
# ---------------------------------------------------------------------------
print("\n--- compute_smd ---")

# mean_i=5.2, sd_i=1.1, n_i=50, mean_c=4.8, sd_c=1.2, n_c=50
# s_pooled = sqrt(((49*1.21)+(49*1.44))/98) = sqrt((59.29+70.56)/98)
#           = sqrt(129.85/98) = sqrt(1.3250) = 1.1511
# Cohen's d = (5.2-4.8) / 1.1511 = 0.3475
# J = 1 - 3/(4*98 - 1) = 1 - 3/391 = 0.9923
# g = 0.3475 * 0.9923 ≈ 0.3447
s_pooled = math.sqrt(((49 * 1.21) + (49 * 1.44)) / 98)
J = 1 - 3 / (4 * 98 - 1)
expected_g = (5.2 - 4.8) / s_pooled * J

res = compute_smd(5.2, 1.1, 50, 4.8, 1.2, 50)
check("basic smd (Hedges g)", res["smd"], expected_g)
check("basic smd approx 0.3447", res["smd"], 0.3447)
# CI lower = g - 1.96*SE ≈ 0.345 - 0.392 ≈ -0.047 (crosses zero, so lower < 0)
check("basic smd ci_lower < 0", res["ci_lower"] < 0.0, True)
check("basic smd ci_upper > 0", res["ci_upper"] > 0.0, True)

# SE formula: sqrt((n_i+n_c)/(n_i*n_c) + g²/(2*(n_i+n_c-2))) * J
g = expected_g
expected_se_smd = math.sqrt((50+50)/(50*50) + g**2/(2*(50+50-2))) * J
check("basic smd se", res["se"], expected_se_smd)

# No difference
res2 = compute_smd(5.0, 1.0, 30, 5.0, 1.0, 30)
check("no-diff smd", res2["smd"], 0.0)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------
print("\n--- edge cases ---")

# Very large OR should not crash
res = compute_log_or(95, 5, 5, 95)
check("large or finite log_or", math.isfinite(res["log_or"]), True)
check("large or finite se", math.isfinite(res["se"]), True)

# Equal groups, all metrics at null
res_or = compute_log_or(50, 50, 50, 50)
res_rr = compute_log_rr(50, 50, 50, 50)
res_rd = compute_rd(50, 50, 50, 50)
check("equal groups OR=1", res_or["or_value"], 1.0)
check("equal groups RR=1", res_rr["rr"], 1.0)
check("equal groups RD=0", res_rd["rd"], 0.0)

# Continuous no difference
res_md = compute_md(3.0, 2.0, 40, 3.0, 2.0, 40)
res_smd = compute_smd(3.0, 2.0, 40, 3.0, 2.0, 40)
check("equal continuous MD=0", res_md["md"], 0.0)
check("equal continuous SMD=0", res_smd["smd"], 0.0)

# Zero-cell all four cells
a, b, c, d = zero_cell_correction(0, 0, 0, 0)
check("all-zero correction a", a, 0.5)
check("all-zero correction b", b, 0.5)
check("all-zero correction c", c, 0.5)
check("all-zero correction d", d, 0.5)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n{'='*60}")
print(f"TOTAL: {PASS} passed, {FAIL} failed out of {PASS+FAIL}")
if FAIL > 0:
    sys.exit(1)
