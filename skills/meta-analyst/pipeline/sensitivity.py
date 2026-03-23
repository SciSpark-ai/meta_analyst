"""
sensitivity.py — Sensitivity analysis module for meta-analysis.

Three sensitivity analyses:
  1. leave_one_out              — Re-pool k-1 studies for each excluded study
  2. exclude_high_rob           — Re-pool excluding high risk-of-bias studies
  3. fixed_vs_random_comparison — Compare fixed-effect vs random-effects estimates

Dependencies: pipeline.pooling
"""

from .pooling import pool_fixed_effect_iv, pool_random_effects_dl


# ---------------------------------------------------------------------------
# 1. Leave-one-out sensitivity analysis
# ---------------------------------------------------------------------------

def leave_one_out(effects, ses, study_labels=None):
    """
    Leave-one-out sensitivity analysis.

    For each study i, re-pool the remaining k-1 studies using DL random-effects.

    Parameters
    ----------
    effects       : list of float   — effect estimates
    ses           : list of float   — standard errors
    study_labels  : list of str, optional — study labels; if None, uses integer indices

    Returns
    -------
    list of dicts, one per excluded study:
        excluded_study       — label (str) or index (int) of the excluded study
        pooled               — pooled estimate from k-1 studies
        ci_lower             — lower 95% CI
        ci_upper             — upper 95% CI
        p_value              — two-sided p-value
        direction_changed    — bool: pooled sign changed vs full pooling
        significance_changed — bool: p_value crossed 0.05 threshold vs full pooling
    """
    k = len(effects)

    # Full pooling for reference
    full_result = pool_random_effects_dl(effects, ses)
    full_pooled = full_result["pooled"]
    full_p = full_result["p_value"]
    full_significant = full_p < 0.05

    results = []
    for i in range(k):
        # Build subset excluding study i
        sub_effects = effects[:i] + effects[i+1:]
        sub_ses = ses[:i] + ses[i+1:]

        sub_result = pool_random_effects_dl(sub_effects, sub_ses)

        sub_pooled = sub_result["pooled"]
        sub_p = sub_result["p_value"]
        sub_significant = sub_p < 0.05

        # direction_changed: sign of pooled changed
        direction_changed = bool((sub_pooled * full_pooled) < 0)

        # significance_changed: p crossed 0.05
        significance_changed = bool(sub_significant != full_significant)

        excluded_study = study_labels[i] if study_labels is not None else i

        results.append({
            "excluded_study": excluded_study,
            "pooled": sub_pooled,
            "ci_lower": sub_result["ci_lower"],
            "ci_upper": sub_result["ci_upper"],
            "p_value": sub_p,
            "direction_changed": direction_changed,
            "significance_changed": significance_changed,
        })

    return results


# ---------------------------------------------------------------------------
# 2. Exclude high risk-of-bias studies
# ---------------------------------------------------------------------------

def exclude_high_rob(effects, ses, rob_ratings, study_labels=None):
    """
    Re-pool excluding studies with rob_rating == "high".

    Parameters
    ----------
    effects      : list of float   — effect estimates
    ses          : list of float   — standard errors
    rob_ratings  : list of str     — risk-of-bias rating per study ("low", "moderate", "high")
    study_labels : list of str, optional — study labels (not used in output but accepted)

    Returns
    -------
    dict with keys:
        n_remaining          — number of studies after exclusion
        n_excluded           — number of high-RoB studies excluded
        pooled               — pooled estimate (None if n_remaining == 0)
        ci_lower             — lower 95% CI (None if n_remaining == 0)
        ci_upper             — upper 95% CI (None if n_remaining == 0)
        p_value              — two-sided p-value (None if n_remaining == 0)
        changed_significance — bool: significance changed vs full pooling (None if n_remaining == 0)
    """
    # Identify non-high studies
    keep_indices = [i for i, r in enumerate(rob_ratings) if r != "high"]
    n_excluded = len(effects) - len(keep_indices)
    n_remaining = len(keep_indices)

    # All excluded
    if n_remaining == 0:
        return {
            "n_remaining": 0,
            "n_excluded": n_excluded,
            "pooled": None,
            "ci_lower": None,
            "ci_upper": None,
            "p_value": None,
            "changed_significance": None,
        }

    sub_effects = [effects[i] for i in keep_indices]
    sub_ses = [ses[i] for i in keep_indices]

    # Full pooling for significance reference
    full_result = pool_random_effects_dl(effects, ses)
    full_significant = full_result["p_value"] < 0.05

    sub_result = pool_random_effects_dl(sub_effects, sub_ses)
    sub_significant = sub_result["p_value"] < 0.05

    return {
        "n_remaining": n_remaining,
        "n_excluded": n_excluded,
        "pooled": sub_result["pooled"],
        "ci_lower": sub_result["ci_lower"],
        "ci_upper": sub_result["ci_upper"],
        "p_value": sub_result["p_value"],
        "changed_significance": bool(sub_significant != full_significant),
    }


# ---------------------------------------------------------------------------
# 3. Fixed vs random effects comparison
# ---------------------------------------------------------------------------

def fixed_vs_random_comparison(effects, ses):
    """
    Compare fixed-effect and random-effects pooled estimates.

    Parameters
    ----------
    effects : list of float   — effect estimates
    ses     : list of float   — standard errors

    Returns
    -------
    dict with keys:
        fixed_pooled     — fixed-effect pooled estimate
        fixed_ci         — dict {lower, upper}
        random_pooled    — random-effects pooled estimate
        random_ci        — dict {lower, upper}
        divergence       — abs(fixed_pooled - random_pooled)
        small_study_flag — bool: True if divergence > 0.1 OR
                           abs(fixed-random)/max(abs(fixed),abs(random)) > 0.2
    """
    fe = pool_fixed_effect_iv(effects, ses)
    re = pool_random_effects_dl(effects, ses)

    fixed_pooled = fe["pooled"]
    random_pooled = re["pooled"]

    divergence = abs(fixed_pooled - random_pooled)

    max_abs = max(abs(fixed_pooled), abs(random_pooled))
    if max_abs > 0:
        relative_diff = abs(fixed_pooled - random_pooled) / max_abs
    else:
        relative_diff = 0.0

    small_study_flag = (divergence > 0.1) or (relative_diff > 0.2)

    return {
        "fixed_pooled": fixed_pooled,
        "fixed_ci": {"lower": fe["ci_lower"], "upper": fe["ci_upper"]},
        "random_pooled": random_pooled,
        "random_ci": {"lower": re["ci_lower"], "upper": re["ci_upper"]},
        "divergence": divergence,
        "small_study_flag": small_study_flag,
    }
