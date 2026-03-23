"""
heterogeneity.py — Heterogeneity quantification for meta-analysis.

Functions:
  cochrans_q(effects, ses)              → dict {q, df, p_value}
  i_squared(q, df)                      → dict {i_squared, interpretation}
  tau_squared_dl(q, df, weights)        → float
  h_squared(q, df)                      → float
  prediction_interval(pooled, se_pooled, tau_sq, k) → dict {lower, upper} or None

Dependencies: math, scipy.stats
"""

import math
from scipy.stats import chi2 as _chi2, t as _t


# ---------------------------------------------------------------------------
# 1. Cochran's Q heterogeneity statistic
# ---------------------------------------------------------------------------

def cochrans_q(effects, ses):
    """
    Compute Cochran's Q statistic for heterogeneity.

    Parameters
    ----------
    effects : list of float   — effect estimates (e.g. log OR, MD, SMD)
    ses     : list of float   — standard errors for each effect

    Returns
    -------
    dict with keys:
        q        — Cochran's Q statistic (sum of weighted squared deviations)
        df       — degrees of freedom (k - 1)
        p_value  — p-value from chi-squared distribution with df degrees of freedom
    """
    k = len(effects)
    df = k - 1

    # Fixed-effect weights: w_i = 1 / SE_i^2
    weights = [1.0 / (s ** 2) for s in ses]
    sum_w = sum(weights)

    # Fixed-effect pooled estimate
    theta = sum(w * e for w, e in zip(weights, effects)) / sum_w

    # Q = sum(w_i * (theta_i - theta)^2)
    q = sum(w * (e - theta) ** 2 for w, e in zip(weights, effects))

    # p-value from chi-squared distribution (right tail)
    if df > 0:
        p_value = _chi2.sf(q, df)
    else:
        # k=1: no degrees of freedom, p is undefined; return 1.0 (no evidence of heterogeneity)
        p_value = 1.0

    return {"q": q, "df": df, "p_value": p_value}


# ---------------------------------------------------------------------------
# 2. I² statistic
# ---------------------------------------------------------------------------

def i_squared(q, df):
    """
    Compute I² heterogeneity statistic.

    I² = max(0, (Q - df) / Q * 100)

    Interpretation per Cochrane Handbook 10.10.2:
      I² < 40        → "low"
      40 <= I² < 60  → "moderate"
      60 <= I² < 75  → "substantial"
      I² >= 75       → "considerable"

    Parameters
    ----------
    q  : float — Cochran's Q statistic
    df : int   — degrees of freedom (k - 1)

    Returns
    -------
    dict with keys:
        i_squared      — I² percentage (0 to 100)
        interpretation — one of "low", "moderate", "substantial", "considerable"
    """
    # Edge case: Q = 0 (or Q <= 0)
    if q <= 0.0:
        return {"i_squared": 0.0, "interpretation": "low"}

    isq = max(0.0, (q - df) / q * 100.0)

    if isq < 40.0:
        interpretation = "low"
    elif isq < 60.0:
        interpretation = "moderate"
    elif isq < 75.0:
        interpretation = "substantial"
    else:
        interpretation = "considerable"

    return {"i_squared": isq, "interpretation": interpretation}


# ---------------------------------------------------------------------------
# 3. tau² (DerSimonian-Laird estimator)
# ---------------------------------------------------------------------------

def tau_squared_dl(q, df, weights):
    """
    Estimate between-study variance tau² using DerSimonian-Laird method.

    c = sum(w_i) - sum(w_i^2) / sum(w_i)
    tau² = max(0, (Q - df) / c)

    Parameters
    ----------
    q       : float       — Cochran's Q statistic
    df      : int         — degrees of freedom (k - 1)
    weights : list of float — fixed-effect weights (1/SE_i^2)

    Returns
    -------
    float — tau² (non-negative)
    """
    sum_w = sum(weights)
    sum_w_sq = sum(wi ** 2 for wi in weights)

    if sum_w == 0.0 or len(weights) < 2:
        return 0.0

    c = sum_w - sum_w_sq / sum_w

    if c == 0.0:
        return 0.0

    return max(0.0, (q - df) / c)


# ---------------------------------------------------------------------------
# 4. H² statistic
# ---------------------------------------------------------------------------

def h_squared(q, df):
    """
    Compute H² heterogeneity statistic.

    H² = Q / df  (when df > 0, else 1.0)

    H² = 1 means no heterogeneity; H² > 1 indicates heterogeneity.

    Parameters
    ----------
    q  : float — Cochran's Q statistic
    df : int   — degrees of freedom (k - 1)

    Returns
    -------
    float — H²
    """
    if df <= 0:
        return 1.0
    return float(q) / float(df)


# ---------------------------------------------------------------------------
# 5. Prediction interval
# ---------------------------------------------------------------------------

def prediction_interval(pooled, se_pooled, tau_sq, k):
    """
    Compute 95% prediction interval for a future study's effect.

    lower = pooled - t * sqrt(se_pooled^2 + tau^2)
    upper = pooled + t * sqrt(se_pooled^2 + tau^2)

    where t is from t-distribution with k-2 degrees of freedom at 97.5th percentile.

    Requires k >= 3 (otherwise df = k-2 <= 0, interval undefined).

    Parameters
    ----------
    pooled    : float — pooled effect estimate
    se_pooled : float — standard error of pooled estimate
    tau_sq    : float — between-study variance (tau²)
    k         : int   — number of studies

    Returns
    -------
    dict with keys {lower, upper}, or None if k < 3
    """
    if k < 3:
        return None

    df = k - 2
    t_crit = _t.ppf(0.975, df)
    pi_se = math.sqrt(se_pooled ** 2 + tau_sq)
    lower = pooled - t_crit * pi_se
    upper = pooled + t_crit * pi_se

    return {"lower": lower, "upper": upper}
