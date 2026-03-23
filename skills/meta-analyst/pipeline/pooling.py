"""
pooling.py — Meta-analytic pooling module.

Three pooling methods:
  1. pool_fixed_effect_iv   — Inverse-variance fixed-effect
  2. pool_random_effects_dl — DerSimonian-Laird random-effects
  3. pool_mantel_haenszel   — Mantel-Haenszel (raw 2×2 tables)

Dependencies: math, scipy.stats
"""

import math
from scipy.stats import norm as _norm, t as _t


# ---------------------------------------------------------------------------
# 1. Fixed-effect inverse-variance pooling
# ---------------------------------------------------------------------------

def pool_fixed_effect_iv(effects, ses):
    """
    Inverse-variance fixed-effect pooling.

    Parameters
    ----------
    effects : list of float   — effect estimates (e.g. log OR, MD, SMD)
    ses     : list of float   — standard errors for each effect

    Returns
    -------
    dict with keys:
        pooled    — pooled effect estimate
        se        — standard error of pooled estimate
        ci_lower  — lower 95% CI bound
        ci_upper  — upper 95% CI bound
        p_value   — two-sided p from z-test
        weights   — list of per-study weights (1/SE_i^2)
    """
    weights = [1.0 / (s ** 2) for s in ses]
    sum_w = sum(weights)
    pooled = sum(w * e for w, e in zip(weights, effects)) / sum_w
    se = math.sqrt(1.0 / sum_w)
    ci_lower = pooled - 1.96 * se
    ci_upper = pooled + 1.96 * se
    z = pooled / se
    p_value = 2.0 * _norm.sf(abs(z))
    return {
        "pooled": pooled,
        "se": se,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "p_value": p_value,
        "weights": weights,
    }


# ---------------------------------------------------------------------------
# 2. DerSimonian-Laird random-effects pooling
# ---------------------------------------------------------------------------

def pool_random_effects_dl(effects, ses):
    """
    DerSimonian-Laird random-effects pooling.

    Parameters
    ----------
    effects : list of float   — effect estimates
    ses     : list of float   — standard errors

    Returns
    -------
    dict with keys:
        pooled              — pooled random-effects estimate
        se                  — SE of pooled estimate
        ci_lower            — lower 95% CI
        ci_upper            — upper 95% CI
        p_value             — two-sided p from z-test
        tau_sq              — between-study variance (tau^2 >= 0)
        q_stat              — Cochran's Q heterogeneity statistic
        weights             — per-study random-effects weights
        prediction_interval — dict {lower, upper} or None if k < 3
    """
    k = len(effects)

    # Step 1: fixed-effect weights
    w_fe = [1.0 / (s ** 2) for s in ses]
    sum_w = sum(w_fe)

    # Step 2: fixed-effect pooled (needed for Q)
    theta_fe = sum(w * e for w, e in zip(w_fe, effects)) / sum_w

    # Step 3: Q statistic
    q_stat = sum(w * (e - theta_fe) ** 2 for w, e in zip(w_fe, effects))

    # Step 4: tau^2 (DL estimator, floor at 0)
    # When k=1, c=0 and there is no heterogeneity to estimate; tau^2 = 0
    sum_w_sq = sum(wi ** 2 for wi in w_fe)
    c = sum_w - sum_w_sq / sum_w
    if c == 0.0 or k < 2:
        tau_sq = 0.0
    else:
        tau_sq = max(0.0, (q_stat - (k - 1)) / c)

    # Step 5: random-effects weights
    w_re = [1.0 / (s ** 2 + tau_sq) for s in ses]
    sum_w_re = sum(w_re)

    # Step 6: pooled RE estimate
    pooled = sum(w * e for w, e in zip(w_re, effects)) / sum_w_re

    # Step 7: SE and CI
    se = math.sqrt(1.0 / sum_w_re)
    ci_lower = pooled - 1.96 * se
    ci_upper = pooled + 1.96 * se
    z = pooled / se
    p_value = 2.0 * _norm.sf(abs(z))

    # Prediction interval (requires k >= 3 for df = k-2 >= 1)
    if k >= 3:
        df = k - 2
        t_crit = _t.ppf(0.975, df)
        pi_se = math.sqrt(se ** 2 + tau_sq)
        pi_lower = pooled - t_crit * pi_se
        pi_upper = pooled + t_crit * pi_se
        prediction_interval = {"lower": pi_lower, "upper": pi_upper}
    else:
        prediction_interval = None

    return {
        "pooled": pooled,
        "se": se,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "p_value": p_value,
        "tau_sq": tau_sq,
        "q_stat": q_stat,
        "weights": w_re,
        "prediction_interval": prediction_interval,
    }


# ---------------------------------------------------------------------------
# 3. Mantel-Haenszel pooling from raw 2×2 tables
# ---------------------------------------------------------------------------

def pool_mantel_haenszel(tables, measure="OR"):
    """
    Mantel-Haenszel pooling from raw 2×2 tables.

    Parameters
    ----------
    tables  : list of tuples (a, b, c, d)
                a = events in intervention arm
                b = non-events in intervention arm
                c = events in control arm
                d = non-events in control arm
    measure : "OR" (default) or "RR"

    Returns
    -------
    dict with keys:
        pooled      — pooled estimate on original scale
        se          — SE of log-transformed pooled estimate
        ci_lower    — lower 95% CI (original scale)
        ci_upper    — upper 95% CI (original scale)
        p_value     — two-sided p from z-test on log scale
        log_pooled  — natural log of pooled estimate
    """
    if measure == "OR":
        return _mh_or(tables)
    elif measure == "RR":
        return _mh_rr(tables)
    else:
        raise ValueError(f"Unsupported measure '{measure}'. Use 'OR' or 'RR'.")


def _mh_or(tables):
    """Mantel-Haenszel OR with Robins-Breslow-Greenland variance estimator."""
    # MH OR numerator/denominator
    num = 0.0  # sum(a_i * d_i / N_i)
    den = 0.0  # sum(b_i * c_i / N_i)

    # RBG variance components (Robins, Breslow, Greenland 1986)
    # V = sum(P_i * R_i) / (2*R^2) + sum(P_i*S_i + Q_i*R_i) / (2*R*S) + sum(Q_i*S_i) / (2*S^2)
    # where R = num, S = den, and per-study:
    #   R_i = a_i * d_i / N_i
    #   S_i = b_i * c_i / N_i
    #   P_i = (a_i + d_i) / N_i
    #   Q_i = (b_i + c_i) / N_i
    sum_PR = 0.0
    sum_PS_QR = 0.0
    sum_QS = 0.0

    r_i_list = []
    s_i_list = []
    p_i_list = []
    q_i_list = []

    for (a, b, c, d) in tables:
        a, b, c, d = float(a), float(b), float(c), float(d)
        N = a + b + c + d
        r_i = a * d / N
        s_i = b * c / N
        p_i = (a + d) / N
        q_i = (b + c) / N
        num += r_i
        den += s_i
        r_i_list.append(r_i)
        s_i_list.append(s_i)
        p_i_list.append(p_i)
        q_i_list.append(q_i)

    mh_or = num / den

    # RBG variance of log(MH OR)
    for r_i, s_i, p_i, q_i in zip(r_i_list, s_i_list, p_i_list, q_i_list):
        sum_PR  += p_i * r_i
        sum_PS_QR += p_i * s_i + q_i * r_i
        sum_QS  += q_i * s_i

    var_log_or = (
        sum_PR / (2.0 * num ** 2)
        + sum_PS_QR / (2.0 * num * den)
        + sum_QS / (2.0 * den ** 2)
    )
    se = math.sqrt(var_log_or)
    log_pooled = math.log(mh_or)
    z = log_pooled / se
    p_value = 2.0 * _norm.sf(abs(z))
    ci_lower = math.exp(log_pooled - 1.96 * se)
    ci_upper = math.exp(log_pooled + 1.96 * se)

    return {
        "pooled": mh_or,
        "se": se,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "p_value": p_value,
        "log_pooled": log_pooled,
    }


def _mh_rr(tables):
    """Mantel-Haenszel RR with Greenland-Robins variance estimator."""
    # MH RR = sum(a_i * (c_i+d_i) / N_i) / sum(c_i * (a_i+b_i) / N_i)
    num = 0.0  # sum(a_i * n_c_i / N_i)
    den = 0.0  # sum(c_i * n_i_i / N_i)

    # Greenland-Robins variance of log(MH RR):
    # V = sum((n_i_i * n_c_i * (a_i + c_i) - a_i * c_i * N_i) / N_i^2) / (num * den)
    # where n_i_i = a_i+b_i, n_c_i = c_i+d_i
    gr_sum = 0.0

    for (a, b, c, d) in tables:
        a, b, c, d = float(a), float(b), float(c), float(d)
        N = a + b + c + d
        n_i = a + b   # intervention arm total
        n_c = c + d   # control arm total
        num += a * n_c / N
        den += c * n_i / N
        gr_sum += (n_i * n_c * (a + c) - a * c * N) / (N ** 2)

    mh_rr = num / den
    var_log_rr = gr_sum / (num * den)
    se = math.sqrt(var_log_rr)
    log_pooled = math.log(mh_rr)
    z = log_pooled / se
    p_value = 2.0 * _norm.sf(abs(z))
    ci_lower = math.exp(log_pooled - 1.96 * se)
    ci_upper = math.exp(log_pooled + 1.96 * se)

    return {
        "pooled": mh_rr,
        "se": se,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "p_value": p_value,
        "log_pooled": log_pooled,
    }
