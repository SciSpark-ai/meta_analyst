"""
publication_bias.py — Publication bias assessment module for meta-analysis.

Two functions:
  1. eggers_test       — Egger's regression test for funnel plot asymmetry
  2. funnel_plot_data  — Compute coordinates and pseudo-CI lines for funnel plot

Dependencies: statsmodels, numpy
"""

import numpy as np
import statsmodels.api as sm


# ---------------------------------------------------------------------------
# 1. Egger's test for funnel plot asymmetry
# ---------------------------------------------------------------------------

def eggers_test(effects, ses):
    """
    Egger's regression test for funnel plot asymmetry.

    Regresses standardized effect (effect_i / SE_i) on precision (1 / SE_i).
    Tests whether the intercept differs from zero.

    Parameters
    ----------
    effects : list of float   — effect estimates
    ses     : list of float   — standard errors

    Returns
    -------
    If k < 10:
        {skipped: True, reason: "Fewer than 10 studies; ..."}
    Otherwise:
        {intercept, se, p_value, skipped: False, reason: None}
    """
    k = len(effects)

    if k < 10:
        return {
            "skipped": True,
            "reason": (
                "Fewer than 10 studies; formal test for funnel asymmetry not recommended "
                "(Cochrane Handbook 10.4.3.1)"
            ),
        }

    effects_arr = np.array(effects, dtype=float)
    ses_arr = np.array(ses, dtype=float)

    # Dependent variable: standardized effect = effect / SE
    y = effects_arr / ses_arr

    # Independent variable: precision = 1 / SE
    x = 1.0 / ses_arr

    # Add intercept to design matrix
    x_with_const = sm.add_constant(x)

    model = sm.OLS(y, x_with_const)
    fit = model.fit()

    # Intercept is the first parameter (index 0 after add_constant)
    intercept = float(fit.params[0])
    se = float(fit.bse[0])
    p_value = float(fit.pvalues[0])

    return {
        "intercept": intercept,
        "se": se,
        "p_value": p_value,
        "skipped": False,
        "reason": None,
    }


# ---------------------------------------------------------------------------
# 2. Funnel plot data
# ---------------------------------------------------------------------------

def funnel_plot_data(effects, ses, pooled):
    """
    Compute coordinates for a funnel plot.

    The funnel plot has effect on the x-axis and SE on the y-axis (inverted).
    Pseudo-CI lines show the expected range: pooled ± 1.96 * SE.

    Parameters
    ----------
    effects : list of float   — effect estimates
    ses     : list of float   — standard errors
    pooled  : float           — pooled effect estimate (center of the funnel)

    Returns
    -------
    dict with keys:
        points           — list of dicts [{effect, se}, ...]
        pooled           — pooled effect (passed through)
        pseudo_ci_lines  — dict {
                              se_range: [min_se, max_se],
                              lower_bound: [...],   # pooled - 1.96 * se at each grid point
                              upper_bound: [...]    # pooled + 1.96 * se at each grid point
                           }
    """
    ses_arr = np.array(ses, dtype=float)
    min_se = float(ses_arr.min())
    max_se = float(ses_arr.max())

    # Build grid of SE values for pseudo-CI lines (one per study SE value, sorted)
    se_grid = np.sort(ses_arr)
    lower_bound = [pooled - 1.96 * s for s in se_grid]
    upper_bound = [pooled + 1.96 * s for s in se_grid]

    points = [{"effect": float(e), "se": float(s)} for e, s in zip(effects, ses)]

    return {
        "points": points,
        "pooled": pooled,
        "pseudo_ci_lines": {
            "se_range": [min_se, max_se],
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
        },
    }
