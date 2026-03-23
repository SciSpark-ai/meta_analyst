"""
effect_sizes.py — Deterministic effect-size computation for meta-analysis.

All functions use only the Python standard library (math module).
No scipy / numpy dependency.

Binary outcome functions accept a 2×2 table:
  a = events in intervention arm
  b = non-events in intervention arm
  c = events in control arm
  d = non-events in control arm

Call zero_cell_correction() before any binary function when any cell may be 0.
"""

import math


# ---------------------------------------------------------------------------
# Zero-cell handling
# ---------------------------------------------------------------------------

def zero_cell_correction(a, b, c, d, correction=0.5):
    """
    If any cell in the 2×2 table is zero, add `correction` to ALL four cells.
    Returns (a, b, c, d) as floats.
    """
    a, b, c, d = float(a), float(b), float(c), float(d)
    if a == 0 or b == 0 or c == 0 or d == 0:
        a += correction
        b += correction
        c += correction
        d += correction
    return a, b, c, d


# ---------------------------------------------------------------------------
# Binary outcomes
# ---------------------------------------------------------------------------

def compute_log_or(a, b, c, d):
    """
    Compute log odds ratio and 95% CI from a 2×2 table.

    Returns dict:
        log_or    — natural log of OR
        se        — standard error of log_or
        or_value  — odds ratio on original scale
        ci_lower  — lower bound of 95% CI (OR scale)
        ci_upper  — upper bound of 95% CI (OR scale)
    """
    a, b, c, d = float(a), float(b), float(c), float(d)
    log_or = math.log(a * d / (b * c))
    se = math.sqrt(1/a + 1/b + 1/c + 1/d)
    or_value = math.exp(log_or)
    ci_lower = math.exp(log_or - 1.96 * se)
    ci_upper = math.exp(log_or + 1.96 * se)
    return {
        "log_or": log_or,
        "se": se,
        "or_value": or_value,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
    }


def compute_log_rr(a, b, c, d):
    """
    Compute log relative risk and 95% CI from a 2×2 table.

    Returns dict:
        log_rr    — natural log of RR
        se        — standard error of log_rr
        rr        — relative risk on original scale
        ci_lower  — lower bound of 95% CI (RR scale)
        ci_upper  — upper bound of 95% CI (RR scale)
    """
    a, b, c, d = float(a), float(b), float(c), float(d)
    n_i = a + b
    n_c = c + d
    p1 = a / n_i
    p2 = c / n_c
    log_rr = math.log(p1 / p2)
    se = math.sqrt(1/a - 1/n_i + 1/c - 1/n_c)
    rr = math.exp(log_rr)
    ci_lower = math.exp(log_rr - 1.96 * se)
    ci_upper = math.exp(log_rr + 1.96 * se)
    return {
        "log_rr": log_rr,
        "se": se,
        "rr": rr,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
    }


def compute_rd(a, b, c, d):
    """
    Compute risk difference (absolute risk reduction) and 95% CI.

    Returns dict:
        rd        — risk difference (p_intervention - p_control)
        se        — standard error
        ci_lower  — lower bound of 95% CI
        ci_upper  — upper bound of 95% CI
    """
    a, b, c, d = float(a), float(b), float(c), float(d)
    n_i = a + b
    n_c = c + d
    p1 = a / n_i
    p2 = c / n_c
    rd = p1 - p2
    se = math.sqrt(p1 * (1 - p1) / n_i + p2 * (1 - p2) / n_c)
    ci_lower = rd - 1.96 * se
    ci_upper = rd + 1.96 * se
    return {
        "rd": rd,
        "se": se,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
    }


# ---------------------------------------------------------------------------
# Continuous outcomes
# ---------------------------------------------------------------------------

def compute_md(mean_i, sd_i, n_i, mean_c, sd_c, n_c):
    """
    Compute mean difference and 95% CI for continuous outcomes.

    Returns dict:
        md        — mean difference (intervention - control)
        se        — standard error
        ci_lower  — lower bound of 95% CI
        ci_upper  — upper bound of 95% CI
    """
    n_i, n_c = float(n_i), float(n_c)
    md = mean_i - mean_c
    se = math.sqrt(sd_i**2 / n_i + sd_c**2 / n_c)
    ci_lower = md - 1.96 * se
    ci_upper = md + 1.96 * se
    return {
        "md": md,
        "se": se,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
    }


def compute_smd(mean_i, sd_i, n_i, mean_c, sd_c, n_c):
    """
    Compute standardised mean difference using Hedges' g (small-sample corrected).

    Formula:
        s_pooled = sqrt(((n_i-1)*sd_i² + (n_c-1)*sd_c²) / (n_i + n_c - 2))
        J        = 1 - 3 / (4*(n_i + n_c - 2) - 1)   [small-sample correction]
        g        = (mean_i - mean_c) / s_pooled * J
        SE       = sqrt((n_i+n_c)/(n_i*n_c) + g²/(2*(n_i+n_c-2))) * J

    Returns dict:
        smd       — Hedges' g
        se        — standard error of g
        ci_lower  — lower bound of 95% CI
        ci_upper  — upper bound of 95% CI
    """
    n_i, n_c = float(n_i), float(n_c)
    df = n_i + n_c - 2
    s_pooled = math.sqrt(((n_i - 1) * sd_i**2 + (n_c - 1) * sd_c**2) / df)
    J = 1 - 3 / (4 * df - 1)
    # Cohen's d then apply Hedges' correction
    d = (mean_i - mean_c) / s_pooled if s_pooled != 0 else 0.0
    g = d * J
    se = math.sqrt((n_i + n_c) / (n_i * n_c) + g**2 / (2 * df)) * J
    ci_lower = g - 1.96 * se
    ci_upper = g + 1.96 * se
    return {
        "smd": g,
        "se": se,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
    }
