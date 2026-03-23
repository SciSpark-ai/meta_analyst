"""
grade.py — GRADE Certainty of Evidence module for meta-analysis.

Six functions:
  1. assess_risk_of_bias      — Downgrade based on proportion of high-RoB studies
  2. assess_inconsistency     — Downgrade based on I² statistic
  3. assess_imprecision       — Downgrade based on CI crossing null / OIS not met
  4. assess_publication_bias  — Downgrade based on Egger's p-value (k >= 10 only)
  5. compute_grade            — Apply all downgrades to starting certainty level
  6. grade_summary_row        — Format one row of a Summary of Findings table

Dependencies: standard library only
"""


# ---------------------------------------------------------------------------
# 1. Risk of bias
# ---------------------------------------------------------------------------

def assess_risk_of_bias(rob_ratings: list) -> int:
    """
    Downgrade certainty based on the proportion of studies rated "high" RoB.

    Parameters
    ----------
    rob_ratings : list of str
        Per-study overall RoB judgments: "low", "some concerns", or "high".

    Returns
    -------
    int: 0 (no downgrade), -1 (serious), or -2 (very serious)
    """
    k = len(rob_ratings)
    if k == 0:
        return 0

    n_high = sum(1 for r in rob_ratings if r == "high")
    proportion_high = n_high / k

    if n_high == 0:
        return 0
    elif proportion_high < 0.50:
        return -1
    else:
        return -2


# ---------------------------------------------------------------------------
# 2. Inconsistency
# ---------------------------------------------------------------------------

def assess_inconsistency(i_squared: float) -> int:
    """
    Downgrade certainty based on I² statistic.

    Parameters
    ----------
    i_squared : float
        I² value (0–100).

    Returns
    -------
    int: 0, -1, or -2
    """
    if i_squared < 50:
        return 0
    elif i_squared < 75:
        return -1
    else:
        return -2


# ---------------------------------------------------------------------------
# 3. Imprecision
# ---------------------------------------------------------------------------

def assess_imprecision(ci_lower, ci_upper, null_value, ois=None, total_n=None) -> int:
    """
    Downgrade certainty based on CI width and optimal information size.

    Check 1: Does the CI cross the null value?
    Check 2: If ois and total_n are both provided, is total_n < ois?

    Parameters
    ----------
    ci_lower   : float  — lower bound of the confidence interval
    ci_upper   : float  — upper bound of the confidence interval
    null_value : float  — null value (e.g. 1.0 for RR/OR, 0.0 for MD)
    ois        : float or None — optimal information size (sample size threshold)
    total_n    : int or None   — actual total N across all studies

    Returns
    -------
    int: 0 (neither), -1 (one condition), or -2 (both conditions)
    """
    crosses_null = ci_lower < null_value < ci_upper

    ois_not_met = False
    if ois is not None and total_n is not None:
        ois_not_met = total_n < ois

    n_conditions = int(crosses_null) + int(ois_not_met)

    if n_conditions == 0:
        return 0
    elif n_conditions == 1:
        return -1
    else:
        return -2


# ---------------------------------------------------------------------------
# 4. Publication bias
# ---------------------------------------------------------------------------

def assess_publication_bias(eggers_p, k) -> int:
    """
    Downgrade certainty based on Egger's test for funnel plot asymmetry.

    If k < 10, the test cannot be reliably interpreted and no downgrade is applied.

    Parameters
    ----------
    eggers_p : float — p-value from Egger's test
    k        : int   — number of studies in the meta-analysis

    Returns
    -------
    int: 0 (no downgrade) or -1 (suspected publication bias)
    """
    if k < 10:
        return 0
    if eggers_p < 0.10:
        return -1
    return 0


# ---------------------------------------------------------------------------
# 5. Compute GRADE certainty
# ---------------------------------------------------------------------------

_CERTAINTY_LEVELS = ["Very Low", "Low", "Moderate", "High"]
_CERTAINTY_INDEX = {level: i for i, level in enumerate(_CERTAINTY_LEVELS)}


def compute_grade(start_certainty: str, downgrades: dict) -> str:
    """
    Apply all domain downgrades to a starting certainty level.

    Parameters
    ----------
    start_certainty : str
        Starting certainty level: "High", "Moderate", "Low", or "Very Low".
    downgrades : dict
        Keys: "rob", "inconsistency", "indirectness", "imprecision", "publication_bias"
        Values: 0, -1, or -2 (negative integers)

    Returns
    -------
    str: "High", "Moderate", "Low", or "Very Low"
    """
    start_index = _CERTAINTY_INDEX[start_certainty]
    total_downgrade = sum(downgrades.values())

    # Clamp so final index is at least 0 (Very Low)
    final_index = max(0, start_index + total_downgrade)

    return _CERTAINTY_LEVELS[final_index]


# ---------------------------------------------------------------------------
# 6. Summary of Findings row
# ---------------------------------------------------------------------------

_CERTAINTY_SYMBOLS = {
    "High":     "⊕⊕⊕⊕",
    "Moderate": "⊕⊕⊕◯",
    "Low":      "⊕⊕◯◯",
    "Very Low": "⊕◯◯◯",
}


def grade_summary_row(
    outcome_name,
    n_studies,
    total_n,
    pooled_effect,
    ci_lower,
    ci_upper,
    certainty,
    downgrade_reasons,
) -> dict:
    """
    Format one row of a GRADE Summary of Findings table.

    Parameters
    ----------
    outcome_name      : str   — name of the outcome (e.g. "All-cause mortality")
    n_studies         : int   — number of studies contributing to this outcome
    total_n           : int   — total participants across all studies
    pooled_effect     : float — pooled effect estimate
    ci_lower          : float — lower bound of the 95% CI
    ci_upper          : float — upper bound of the 95% CI
    certainty         : str   — GRADE certainty level ("High", "Moderate", "Low", "Very Low")
    downgrade_reasons : list  — list of reason strings for any downgrades applied

    Returns
    -------
    dict with keys:
        outcome, n_studies, total_n, effect_with_ci, certainty,
        certainty_symbols, downgrade_reasons
    """
    effect_with_ci = f"{pooled_effect:.2f} ({ci_lower:.2f} to {ci_upper:.2f})"

    return {
        "outcome": outcome_name,
        "n_studies": n_studies,
        "total_n": total_n,
        "effect_with_ci": effect_with_ci,
        "certainty": certainty,
        "certainty_symbols": _CERTAINTY_SYMBOLS[certainty],
        "downgrade_reasons": downgrade_reasons,
    }
