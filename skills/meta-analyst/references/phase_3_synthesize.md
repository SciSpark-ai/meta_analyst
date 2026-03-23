# Phase 3 — Synthesize

Phase 3 covers all statistical computation: effect size calculation, meta-analytic pooling, heterogeneity assessment, sensitivity analyses, publication bias, GRADE certainty ratings, and final report assembly. All computation in Stages 3.1–3.6 is deterministic Python. Read this document before executing any Phase 3 stage.

**All Python commands must be run from the `skills/meta-analyst/` directory:**

```bash
cd ${CLAUDE_SKILL_DIR}
```

---

## Stage 3.1 — Effect Size Computation

**Purpose:** Convert raw study data from Phase 2 into per-study effect estimates and standard errors suitable for pooling.

```python
from pipeline.effect_sizes import (
    compute_log_or, compute_log_rr, compute_rd,
    compute_md, compute_smd, zero_cell_correction
)
```

### Selection Rules

| Outcome type | Data available | Preferred effect size | Function |
|---|---|---|---|
| Binary | 2×2 table (events + totals) | log OR or log RR | `compute_log_or` / `compute_log_rr` |
| Binary | RR preferred (common event >10%) | log RR | `compute_log_rr` |
| Continuous, same scale | Mean + SD + N | MD | `compute_md` |
| Continuous, different scales | Mean + SD + N | SMD (Hedges' g) | `compute_smd` |

### Zero-Cell Handling

Before calling any log-transform function, check for zero cells:

```python
a, b, c, d = zero_cell_correction(a, b, c, d)
# Then compute:
result = compute_log_or(a, b, c, d)
```

`zero_cell_correction` adds 0.5 to all four cells only when at least one cell is 0. Apply to every study in the dataset, not just those with zeros (for consistency of SE estimation is not required — apply only when any cell equals 0).

### Example — Binary Outcome

```python
studies_data = [
    {"study_id": "McMurray 2019", "a": 386, "b": 1987, "c": 502, "d": 1869},
    {"study_id": "Packer 2020",   "a": 229, "b": 1794, "c": 289, "d": 1734},
]

effects = []
ses = []
for s in studies_data:
    a, b, c, d = zero_cell_correction(s["a"], s["b"], s["c"], s["d"])
    res = compute_log_or(a, b, c, d)
    effects.append(res["log_or"])
    ses.append(res["se"])
```

### Example — Continuous Outcome

```python
result = compute_smd(
    mean_i=5.2, sd_i=1.1, n_i=50,
    mean_c=4.8, sd_c=1.2, n_c=50
)
# result["smd"] is Hedges' g; result["se"] is the SE of g
```

### Output

For each outcome, produce parallel lists `effects` and `ses` of length $k$ (number of studies), plus a `study_labels` list. Pass these to Stage 3.2.

---

## Stage 3.2 — Meta-Analytic Pooling

**Purpose:** Pool per-study effect sizes into a single summary estimate with 95% CI.

```python
from pipeline.pooling import pool_random_effects_dl, pool_fixed_effect_iv, pool_mantel_haenszel
```

### Default: DerSimonian-Laird Random-Effects

Use DL random-effects as the primary pooling method for all outcomes. DL is the Cochrane Handbook default when between-study heterogeneity is plausible (Handbook Section 10.7.3.1).

```python
re_result = pool_random_effects_dl(effects, ses)

# Returns:
# {
#   "pooled": float,              — pooled estimate (log scale for OR/RR)
#   "se": float,
#   "ci_lower": float,
#   "ci_upper": float,
#   "p_value": float,
#   "tau_sq": float,              — between-study variance
#   "q_stat": float,              — Cochran's Q
#   "weights": list,              — per-study RE weights
#   "prediction_interval": dict   — {lower, upper} or None if k < 3
# }
```

**Back-transformation:** For log OR and log RR, exponentiate pooled and CIs before reporting:
```python
import math
pooled_or = math.exp(re_result["pooled"])
ci_lower_or = math.exp(re_result["ci_lower"])
ci_upper_or = math.exp(re_result["ci_upper"])
```

### Comparison: Fixed-Effect

Run fixed-effect pooling for sensitivity comparison (report alongside DL, not as the primary result):

```python
fe_result = pool_fixed_effect_iv(effects, ses)
```

If DL and FE estimates diverge substantially (see Stage 3.4 `fixed_vs_random_comparison`), this may indicate small-study effects or influential outliers.

### Alternative: Mantel-Haenszel

For sparse binary data (any study with expected cell count < 5), use MH as a cross-check:

```python
tables = [(a1, b1, c1, d1), (a2, b2, c2, d2), ...]   # raw 2×2 tables
mh_result = pool_mantel_haenszel(tables, measure="OR")  # or "RR"
```

Compare MH OR against DL OR. If they differ by more than 10% relatively, investigate the discrepant studies.

---

## Stage 3.3 — Heterogeneity Assessment

**Purpose:** Quantify and interpret between-study heterogeneity.

```python
from pipeline.heterogeneity import cochrans_q, i_squared, tau_squared_dl, h_squared, prediction_interval
```

### Computation

```python
# Cochran's Q
q_result = cochrans_q(effects, ses)
# {"q": float, "df": int, "p_value": float}

# I²
i2_result = i_squared(q_result["q"], q_result["df"])
# {"i_squared": float, "interpretation": "low"|"moderate"|"substantial"|"considerable"}

# tau²
fe_weights = [1.0 / s**2 for s in ses]
tau2 = tau_squared_dl(q_result["q"], q_result["df"], fe_weights)

# H²
h2 = h_squared(q_result["q"], q_result["df"])

# Prediction interval (if k >= 3)
pi = prediction_interval(
    pooled=re_result["pooled"],
    se_pooled=re_result["se"],
    tau_sq=tau2,
    k=len(effects)
)
```

### Interpretation Thresholds (Cochrane Handbook 10.10.2)

| I² | Label | Action |
|---|---|---|
| 0–40% | Low | Pooling is appropriate; note the range |
| 40–60% | Moderate | Pool with RE; investigate sources via subgroup or meta-regression |
| 60–75% | Substantial | Pool with RE; substantial unexplained heterogeneity; downgrade GRADE for inconsistency by −1 |
| ≥75% | Considerable | Pooling may be misleading; consider not pooling; downgrade GRADE for inconsistency by −2 |

**Always report all four statistics:** Q (with p-value), I², tau², and the prediction interval when $k \ge 3$.

**Note:** The Q test is low-power for $k < 5$. A non-significant Q does not rule out heterogeneity. Rely on I² and the prediction interval for interpretation, not Q significance alone.

---

## Stage 3.4 — Sensitivity Analyses

**Purpose:** Assess the robustness of the pooled estimate under alternative assumptions.

```python
from pipeline.sensitivity import leave_one_out, exclude_high_rob, fixed_vs_random_comparison
```

### Leave-One-Out

Remove each study in turn and re-pool the remaining $k-1$ studies:

```python
loo_results = leave_one_out(effects, ses, study_labels=study_labels)

# Returns list of k dicts, each containing:
# {
#   "excluded_study": str,
#   "pooled": float,
#   "ci_lower": float, "ci_upper": float, "p_value": float,
#   "direction_changed": bool,    — pooled sign reversed vs full analysis
#   "significance_changed": bool  — p crossed 0.05 threshold
# }
```

Flag any study whose exclusion causes `direction_changed=True` or `significance_changed=True`. These are influential studies that warrant additional scrutiny (examine study characteristics, check for errors).

### High-RoB Exclusion

Re-pool excluding studies with overall RoB = "high":

```python
rob_ratings = [s["rob_overall"] for s in studies_data]  # "low", "some concerns", "high"

rob_result = exclude_high_rob(effects, ses, rob_ratings, study_labels=study_labels)

# Returns:
# {
#   "n_remaining": int,
#   "n_excluded": int,
#   "pooled": float or None,
#   "ci_lower": float, "ci_upper": float, "p_value": float,
#   "changed_significance": bool
# }
```

If `changed_significance=True`, note this in the report as a potential concern about bias.

### Fixed-Effect vs Random-Effects Comparison

```python
fvr = fixed_vs_random_comparison(effects, ses)

# Returns:
# {
#   "fixed_pooled": float,
#   "fixed_ci": {"lower": float, "upper": float},
#   "random_pooled": float,
#   "random_ci": {"lower": float, "upper": float},
#   "divergence": float,       — abs(fixed - random)
#   "small_study_flag": bool   — True if divergence > 0.1 OR relative diff > 20%
# }
```

If `small_study_flag=True`, this suggests small-study effects: smaller studies may show larger effects than larger studies, which can bias the DL estimate upward. Mention in the publication bias discussion.

---

## Stage 3.5 — Publication Bias Assessment

**Purpose:** Test for funnel plot asymmetry as an indicator of potential publication bias.

```python
from pipeline.publication_bias import eggers_test, funnel_plot_data
```

### Egger's Test

```python
egger = eggers_test(effects, ses)

# If k < 10:
# {"skipped": True, "reason": "Fewer than 10 studies; ..."}

# If k >= 10:
# {"intercept": float, "se": float, "p_value": float, "skipped": False, "reason": None}
```

**k < 10 guard:** Do not report or act on Egger's test results when $k < 10$. Instead, note: "Formal test for funnel asymmetry not conducted (k < 10; Cochrane Handbook 10.4.3.1)."

**Interpretation:** If `p_value < 0.10`, report suspected publication bias. Apply GRADE publication bias downgrade of −1 (see Stage 3.6). A significant Egger's intercept may reflect true publication bias, small-study effects, or heterogeneity — state this caveat.

### Funnel Plot Data

```python
funnel = funnel_plot_data(effects, ses, pooled=re_result["pooled"])
# Returns {points, pooled, pseudo_ci_lines}
# Pass to funnel_plot_svg() in Stage 3.7
```

---

## Stage 3.6 — GRADE Certainty Assessment

**Purpose:** Rate the certainty of evidence for each outcome using the GRADE framework.

```python
from pipeline.grade import (
    assess_risk_of_bias, assess_inconsistency, assess_imprecision,
    assess_publication_bias, compute_grade, grade_summary_row
)
```

### Starting Certainty

- RCTs begin at **High** certainty
- Observational studies begin at **Low** certainty (not applicable in this pipeline — all included studies are RCTs)

### Domain 1 — Risk of Bias (deterministic)

```python
rob_ratings = [s["rob_overall"] for s in studies_data]
rob_downgrade = assess_risk_of_bias(rob_ratings)

# Returns: 0, -1, or -2
# 0 high-risk studies → 0
# <50% high-risk → -1 (serious)
# ≥50% high-risk → -2 (very serious)
```

### Domain 2 — Inconsistency (deterministic)

```python
inconsistency_downgrade = assess_inconsistency(i2_result["i_squared"])

# Returns: 0, -1, or -2
# I² < 50% → 0
# 50% ≤ I² < 75% → -1 (serious)
# I² ≥ 75% → -2 (very serious)
```

### Domain 3 — Indirectness (LLM reasoning)

Assess manually based on the PICO match:

- **0 (no concerns):** Study population, intervention, comparator, and outcomes directly match the PICO question.
- **−1 (serious):** One important indirect element (e.g., surrogate outcome instead of patient-important outcome; slightly different population; active comparator differs from specified).
- **−2 (very serious):** Multiple indirect elements; extrapolation is substantial.

Document the reasoning and assign `indirectness_downgrade` as 0, -1, or -2.

### Domain 4 — Imprecision (deterministic)

```python
# For OR/RR: null_value = 1.0
# For MD/RD/SMD: null_value = 0.0

imprecision_downgrade = assess_imprecision(
    ci_lower=ci_lower_or,    # original scale
    ci_upper=ci_upper_or,
    null_value=1.0,
    ois=2000,    # computed OIS — see formulas.md section 8; use None if not computed
    total_n=sum(s["n_randomised_total"] for s in studies_data)
)

# Returns: 0, -1, or -2
# CI crosses null AND OIS not met → -2
# Either condition alone → -1
# Neither → 0
```

**Computing OIS:** Use the control event rate from the pooled data and the MCID agreed with the user (or a clinically accepted threshold). Document the OIS calculation in the report. If no MCID is available, base OIS solely on CI crossing the null.

### Domain 5 — Publication Bias (deterministic)

```python
pub_bias_downgrade = assess_publication_bias(
    eggers_p=egger.get("p_value", 1.0),
    k=len(effects)
)

# Returns: 0 or -1
# k < 10 → always 0 (skipped)
# k ≥ 10 and p < 0.10 → -1
# k ≥ 10 and p ≥ 0.10 → 0
```

### Final GRADE

```python
downgrades = {
    "rob":               rob_downgrade,
    "inconsistency":     inconsistency_downgrade,
    "indirectness":      indirectness_downgrade,   # set by agent reasoning
    "imprecision":       imprecision_downgrade,
    "publication_bias":  pub_bias_downgrade,
}

certainty = compute_grade("High", downgrades)
# Returns: "High", "Moderate", "Low", or "Very Low"
```

### Summary of Findings Row

```python
sof_row = grade_summary_row(
    outcome_name="CV death or worsening HF",
    n_studies=len(effects),
    total_n=sum(s["n_randomised_total"] for s in studies_data),
    pooled_effect=pooled_or,
    ci_lower=ci_lower_or,
    ci_upper=ci_upper_or,
    certainty=certainty,
    downgrade_reasons=[
        reason for reason, delta in [
            ("Serious risk of bias", rob_downgrade),
            ("Substantial inconsistency", inconsistency_downgrade),
            ("Indirect evidence", indirectness_downgrade),
            ("Imprecise estimate", imprecision_downgrade),
            ("Suspected publication bias", pub_bias_downgrade),
        ] if delta < 0
    ],
)
```

---

## Stage 3.7 — Report Assembly

**Purpose:** Assemble the final Cochrane-style Markdown report and structured JSON export.

```python
from pipeline.report import assemble_report, format_characteristics_table, format_grade_sof_table
```

### Assemble the Report

```python
report = assemble_report(
    pico=pico_json,
    search={
        "query": approved_pubmed_query,
        "date_range": "2000-01-01 to 2026-03-23",
        "databases": ["PubMed", "Cochrane CENTRAL", "ClinicalTrials.gov"],
    },
    prisma_counts=prisma_counts,
    characteristics_table=format_characteristics_table(table_studies),
    rob_summary="Narrative RoB summary here.",
    outcomes=[
        {
            "name": "CV death or worsening HF",
            "pooling": {
                "pooled": pooled_or,
                "ci_lower": ci_lower_or,
                "ci_upper": ci_upper_or,
                "p_value": re_result["p_value"],
            },
            "heterogeneity": {
                "i2": i2_result["i_squared"],
                "q": q_result["q"],
                "q_p_value": q_result["p_value"],
                "tau_sq": tau2,
                "prediction_lower": pi["lower"] if pi else None,
                "prediction_upper": pi["upper"] if pi else None,
            },
            "studies": [
                {
                    "label": s["study_id"],
                    "effect": math.exp(e),     # back-transformed for display
                    "ci_lower": math.exp(e - 1.96 * se),
                    "ci_upper": math.exp(e + 1.96 * se),
                    "weight_pct": w / sum(re_result["weights"]) * 100,
                }
                for s, e, se, w in zip(
                    studies_data, effects, ses, re_result["weights"]
                )
            ],
            "effects_for_funnel": effects,
            "ses_for_funnel": ses,
            "grade": {
                "certainty": certainty,
                "certainty_symbols": sof_row["certainty_symbols"],
                "downgrade_reasons": sof_row["downgrade_reasons"],
            },
        }
    ],
    sensitivity={
        "CV death or worsening HF": {
            "leave_one_out": [
                {"removed": r["excluded_study"], "pooled": math.exp(r["pooled"])}
                for r in loo_results
            ],
            "fixed_vs_random": {
                "fixed": math.exp(fvr["fixed_pooled"]),
                "random": math.exp(fvr["random_pooled"]),
            },
            "high_rob_excluded": {
                "n_removed": rob_result["n_excluded"],
                "pooled": math.exp(rob_result["pooled"]) if rob_result["pooled"] else None,
            },
        }
    },
    publication_bias={
        "CV death or worsening HF": {
            "egger_p": egger.get("p_value"),
            "note": egger.get("reason") if egger.get("skipped") else "",
        }
    },
    prisma_svg=None,   # auto-generated inside assemble_report
    rob_svg=rob_svg,
)

# report["markdown"] — full Markdown string
# report["json"]     — structured dict
```

### Output Files

Write the report to disk:

```python
import json

with open("meta_analysis_output.md", "w") as f:
    f.write(report["markdown"])

with open("meta_analysis_output.json", "w") as f:
    json.dump(report["json"], f, indent=2)
```

### Report Structure

The assembled Markdown report contains these sections in order:

1. Title and metadata (date, databases searched)
2. PRISMA Flow Diagram (embedded SVG)
3. Search Strategy (query text, date range)
4. Characteristics of Included Studies (Markdown table)
5. Risk of Bias Summary (traffic light SVG + narrative)
6. Results (one subsection per outcome):
   - Forest plot SVG
   - Pooled estimate + 95% CI + p-value
   - Heterogeneity: I², Q, tau², prediction interval
7. Sensitivity Analyses (leave-one-out table, fixed vs random, high-RoB exclusion)
8. Publication Bias (funnel plot SVG + Egger's result)
9. GRADE Summary of Findings (Markdown table)
10. Summary (narrative — agent-generated)
11. Disclaimer

### JSON Export Structure

```json
{
  "pico":             { ... },
  "search":           { ... },
  "prisma":           { ... },
  "studies":          [ ... ],
  "outcomes": [
    {
      "name":          "...",
      "pooling":       { "pooled": ..., "ci_lower": ..., "ci_upper": ..., "p_value": ... },
      "heterogeneity": { ... },
      "sensitivity":   { ... },
      "grade":         { "certainty": "...", ... }
    }
  ],
  "grade_summary":    [ { "outcome": "...", "certainty": "...", "symbols": "..." } ],
  "publication_bias": { ... }
}
```

---

## Phase 3 Summary Checklist

Before finalising, verify all of the following:

- [ ] Effect sizes computed and zero-cell correction applied where needed
- [ ] DL random-effects is the primary pooled result
- [ ] Fixed-effect run as comparison
- [ ] Heterogeneity reported: Q, I², tau², prediction interval (if k ≥ 3)
- [ ] I² interpretation assigned per Cochrane Handbook thresholds
- [ ] Leave-one-out completed; influential studies flagged
- [ ] High-RoB exclusion completed
- [ ] Fixed-vs-random comparison completed
- [ ] Egger's test skipped if k < 10; run if k ≥ 10
- [ ] GRADE assessed for each outcome: all 5 domains rated
- [ ] Indirectness domain documented with reasoning
- [ ] OIS computed or stated as not available
- [ ] Summary of Findings table generated
- [ ] Report assembled: both Markdown and JSON
- [ ] Disclaimer included in report
