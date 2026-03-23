"""
test_integration.py — Integration test for the full Phase 3 deterministic pipeline.

Runs all pipeline modules end-to-end on a synthetic 8-study RCT dataset (binary
mortality outcome) and verifies internal consistency across modules.

Run from repo root:
    python tests/test_integration.py
"""

import sys
import os
import math
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "meta-analyst"))

from pipeline.effect_sizes import compute_log_or, zero_cell_correction
from pipeline.pooling import pool_random_effects_dl, pool_fixed_effect_iv, pool_mantel_haenszel
from pipeline.heterogeneity import cochrans_q, i_squared, tau_squared_dl, prediction_interval
from pipeline.sensitivity import leave_one_out, exclude_high_rob, fixed_vs_random_comparison
from pipeline.publication_bias import eggers_test, funnel_plot_data
from pipeline.grade import (
    assess_risk_of_bias,
    assess_inconsistency,
    assess_imprecision,
    assess_publication_bias,
    compute_grade,
    grade_summary_row,
)
from pipeline.visualizations import (
    forest_plot_svg,
    funnel_plot_svg,
    prisma_flow_svg,
    rob_traffic_light_svg,
)
from pipeline.report import assemble_report, format_characteristics_table, format_grade_sof_table


# ---------------------------------------------------------------------------
# Pass/fail counter
# ---------------------------------------------------------------------------

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}" + (f": {detail}" if detail else ""))


# ---------------------------------------------------------------------------
# Test dataset — 8 RCTs with 2×2 tables (binary mortality outcome)
# ---------------------------------------------------------------------------

studies_2x2 = [
    # (a=events_int, b=nonevents_int, c=events_ctrl, d=nonevents_ctrl)
    (14, 186, 25, 175),   # Study 1: N=400, moderate effect
    (22, 178, 30, 170),   # Study 2: N=400, small effect
    (8,  92,  15, 85),    # Study 3: N=200, moderate effect
    (45, 455, 60, 440),   # Study 4: N=1000, moderate effect
    (18, 182, 20, 180),   # Study 5: N=400, small effect
    (5,  95,  12, 88),    # Study 6: N=200, larger effect
    (30, 270, 35, 265),   # Study 7: N=600, small effect
    (10, 190, 18, 182),   # Study 8: N=400, moderate effect
]

labels = [f"Study {i+1}" for i in range(8)]
rob_ratings = ["low", "low", "high", "low", "some concerns", "low", "high", "low"]


# ---------------------------------------------------------------------------
# Step 1: Effect sizes
# ---------------------------------------------------------------------------

print("\n=== Step 1: Effect sizes ===")

or_results = []
for i, (a, b, c, d) in enumerate(studies_2x2):
    a, b, c, d = zero_cell_correction(a, b, c, d)
    res = compute_log_or(a, b, c, d)
    or_results.append(res)

log_ors = [r["log_or"] for r in or_results]
ses     = [r["se"]     for r in or_results]
or_vals = [r["or_value"] for r in or_results]

# No NaN / Inf values
all_finite_log_or = all(math.isfinite(v) for v in log_ors)
all_finite_se     = all(math.isfinite(v) for v in ses)
check("No NaN/Inf in log ORs", all_finite_log_or,
      f"log_ors={log_ors}")
check("No NaN/Inf in SEs", all_finite_se,
      f"ses={ses}")

# All ORs < 1 (intervention favored in every study)
all_or_lt1 = all(v < 1.0 for v in or_vals)
check("All ORs < 1 (intervention favored)",
      all_or_lt1,
      f"ORs={[round(v, 3) for v in or_vals]}")

# All SEs > 0
all_se_positive = all(v > 0 for v in ses)
check("All SEs > 0", all_se_positive)


# ---------------------------------------------------------------------------
# Step 2: Pooling
# ---------------------------------------------------------------------------

print("\n=== Step 2: Pooling ===")

dl_result = pool_random_effects_dl(log_ors, ses)
iv_result = pool_fixed_effect_iv(log_ors, ses)
mh_result = pool_mantel_haenszel(studies_2x2, measure="OR")

# DL random-effects pooled OR < 1 and p < 0.05
dl_or = math.exp(dl_result["pooled"])
check("DL pooled OR < 1",
      dl_or < 1.0,
      f"DL pooled OR={dl_or:.4f}")
check("DL p-value < 0.05",
      dl_result["p_value"] < 0.05,
      f"p={dl_result['p_value']:.4f}")

# IV fixed-effect result close to DL (within 0.2 on log scale)
iv_or = math.exp(iv_result["pooled"])
dl_iv_diff = abs(dl_result["pooled"] - iv_result["pooled"])
check("IV fixed-effect close to DL (|diff| <= 0.2 log scale)",
      dl_iv_diff <= 0.2,
      f"DL={dl_result['pooled']:.4f}, IV={iv_result['pooled']:.4f}, diff={dl_iv_diff:.4f}")

# MH result close to IV fixed-effect (within 0.2 on log scale)
mh_log = mh_result["log_pooled"]
iv_mh_diff = abs(iv_result["pooled"] - mh_log)
check("MH close to IV fixed-effect (|diff| <= 0.2 log scale)",
      iv_mh_diff <= 0.2,
      f"IV={iv_result['pooled']:.4f}, MH log={mh_log:.4f}, diff={iv_mh_diff:.4f}")

# Prediction interval wider than CI
pi = dl_result["prediction_interval"]
check("DL prediction interval is not None (k=8 >= 3)",
      pi is not None)
if pi is not None:
    ci_width = dl_result["ci_upper"] - dl_result["ci_lower"]
    pi_width = pi["upper"] - pi["lower"]
    check("Prediction interval wider than CI",
          pi_width > ci_width,
          f"PI width={pi_width:.4f}, CI width={ci_width:.4f}")

# tau² from pooling matches heterogeneity module
fe_weights = [1.0 / (s ** 2) for s in ses]
q_res = cochrans_q(log_ors, ses)
tau2_hetmod = tau_squared_dl(q_res["q"], q_res["df"], fe_weights)
tau2_pooling = dl_result["tau_sq"]
tau2_diff = abs(tau2_pooling - tau2_hetmod)
check("tau² from pooling matches heterogeneity module (tol=1e-9)",
      tau2_diff < 1e-9,
      f"pooling tau²={tau2_pooling:.8f}, hetmod tau²={tau2_hetmod:.8f}")


# ---------------------------------------------------------------------------
# Step 3: Heterogeneity
# ---------------------------------------------------------------------------

print("\n=== Step 3: Heterogeneity ===")

q_stat  = q_res["q"]
df_q    = q_res["df"]
q_pval  = q_res["p_value"]
isq_res = i_squared(q_stat, df_q)
isq_val = isq_res["i_squared"]
tau2_val = tau2_hetmod

check("Q statistic > 0", q_stat > 0, f"Q={q_stat:.4f}")
check("I² >= 0",         isq_val >= 0, f"I²={isq_val:.2f}")
check("tau² >= 0",       tau2_val >= 0, f"tau²={tau2_val:.6f}")

# I² is bounded and finite
check("I² is finite and non-negative",
      math.isfinite(isq_val) and isq_val >= 0.0,
      f"I²={isq_val:.2f}")
check("I² < 99 (not extreme heterogeneity)",
      isq_val < 99.0,
      f"I²={isq_val:.2f}")
# Q statistic itself is > 0 (there is some dispersion in the data)
check("Q statistic reflects non-zero dispersion (Q > 0)",
      q_stat > 0.0,
      f"Q={q_stat:.4f}")

# interpretation is a valid category
valid_interps = {"low", "moderate", "substantial", "considerable"}
check("I² interpretation is a valid category",
      isq_res["interpretation"] in valid_interps,
      f"got: {isq_res['interpretation']}")

# Prediction interval from heterogeneity module consistent with pooling
pi_hetmod = prediction_interval(
    dl_result["pooled"], dl_result["se"], tau2_val, k=len(log_ors)
)
check("Prediction interval from heterogeneity module is not None (k=8)",
      pi_hetmod is not None)
if pi_hetmod is not None and pi is not None:
    check("Prediction interval lower matches pooling module (tol=1e-9)",
          abs(pi_hetmod["lower"] - pi["lower"]) < 1e-9,
          f"hetmod={pi_hetmod['lower']:.8f}, pooling={pi['lower']:.8f}")
    check("Prediction interval upper matches pooling module (tol=1e-9)",
          abs(pi_hetmod["upper"] - pi["upper"]) < 1e-9,
          f"hetmod={pi_hetmod['upper']:.8f}, pooling={pi['upper']:.8f}")


# ---------------------------------------------------------------------------
# Step 4: Sensitivity analyses
# ---------------------------------------------------------------------------

print("\n=== Step 4: Sensitivity analyses ===")

loo_results = leave_one_out(log_ors, ses, study_labels=labels)

# 8 leave-one-out results
check("Leave-one-out yields 8 results",
      len(loo_results) == 8,
      f"got {len(loo_results)}")

# All results have required keys
required_loo_keys = {
    "excluded_study", "pooled", "ci_lower", "ci_upper",
    "p_value", "direction_changed", "significance_changed",
}
all_have_keys = all(required_loo_keys.issubset(r.keys()) for r in loo_results)
check("All LOO results have required keys", all_have_keys)

# No single removal flips direction (all sub-pooled should remain negative on log scale)
no_direction_flip = not any(r["direction_changed"] for r in loo_results)
check("No single removal flips direction of effect",
      no_direction_flip,
      f"flips: {[r['excluded_study'] for r in loo_results if r['direction_changed']]}")

# High-RoB exclusion: 2 high studies → 6 remaining
high_rob_res = exclude_high_rob(log_ors, ses, rob_ratings, study_labels=labels)
check("High-RoB exclusion: n_remaining = 6",
      high_rob_res["n_remaining"] == 6,
      f"got {high_rob_res['n_remaining']}")
check("High-RoB exclusion: n_excluded = 2",
      high_rob_res["n_excluded"] == 2,
      f"got {high_rob_res['n_excluded']}")
check("High-RoB excluded pool still significant (p < 0.05)",
      high_rob_res["p_value"] is not None and high_rob_res["p_value"] < 0.05,
      f"p={high_rob_res['p_value']}")

# Fixed vs random comparison completes without error
fvr = fixed_vs_random_comparison(log_ors, ses)
check("Fixed vs random comparison returns divergence",
      "divergence" in fvr and math.isfinite(fvr["divergence"]),
      f"divergence={fvr.get('divergence')}")
check("Fixed vs random comparison returns small_study_flag (bool)",
      isinstance(fvr["small_study_flag"], bool))


# ---------------------------------------------------------------------------
# Step 5: Publication bias
# ---------------------------------------------------------------------------

print("\n=== Step 5: Publication bias ===")

egger = eggers_test(log_ors, ses)

# k=8 < 10 → test should be skipped
check("Egger's test skipped (k=8 < 10)",
      egger["skipped"] is True,
      f"skipped={egger['skipped']}")
check("Egger's skipped reason string is non-empty",
      isinstance(egger.get("reason"), str) and len(egger["reason"]) > 0)

# Funnel plot data: 8 points
pooled_log_or = dl_result["pooled"]
fp_data = funnel_plot_data(log_ors, ses, pooled_log_or)
check("Funnel plot data has 8 points",
      len(fp_data["points"]) == 8,
      f"got {len(fp_data['points'])}")
check("Funnel plot pseudo-CI lines present",
      "pseudo_ci_lines" in fp_data)
check("Funnel plot pooled value matches DL pooled",
      abs(fp_data["pooled"] - pooled_log_or) < 1e-12)


# ---------------------------------------------------------------------------
# Step 6: GRADE
# ---------------------------------------------------------------------------

print("\n=== Step 6: GRADE ===")

rob_delta      = assess_risk_of_bias(rob_ratings)
inconsistency_delta = assess_inconsistency(isq_val)
# For imprecision: OR CI on log scale; null = 0 (log scale). Convert to OR scale.
ci_lower_or = math.exp(dl_result["ci_lower"])
ci_upper_or = math.exp(dl_result["ci_upper"])
imprecision_delta  = assess_imprecision(ci_lower_or, ci_upper_or, null_value=1.0)
pub_bias_delta     = assess_publication_bias(eggers_p=1.0, k=8)  # skipped → p=1.0

downgrades = {
    "rob":             rob_delta,
    "inconsistency":   inconsistency_delta,
    "indirectness":    0,
    "imprecision":     imprecision_delta,
    "publication_bias": pub_bias_delta,
}

certainty = compute_grade("High", downgrades)
valid_certainties = {"High", "Moderate", "Low", "Very Low"}
check("GRADE certainty is a valid level",
      certainty in valid_certainties,
      f"got: {certainty}")
check("RoB downgrade is 0, -1, or -2",
      rob_delta in {0, -1, -2},
      f"got: {rob_delta}")
check("Inconsistency downgrade is 0, -1, or -2",
      inconsistency_delta in {0, -1, -2},
      f"got: {inconsistency_delta}")
check("Imprecision downgrade is 0, -1, or -2",
      imprecision_delta in {0, -1, -2},
      f"got: {imprecision_delta}")
check("Publication bias downgrade is 0 (k < 10)",
      pub_bias_delta == 0,
      f"got: {pub_bias_delta}")

# Build SoF row
total_n_int = sum(studies_2x2[i][0] + studies_2x2[i][1] for i in range(8))
total_n_ctrl = sum(studies_2x2[i][2] + studies_2x2[i][3] for i in range(8))
total_n = total_n_int + total_n_ctrl

downgrade_reasons = []
if rob_delta < 0:
    downgrade_reasons.append("Risk of bias")
if inconsistency_delta < 0:
    downgrade_reasons.append("Inconsistency")
if imprecision_delta < 0:
    downgrade_reasons.append("Imprecision")

sof_row = grade_summary_row(
    outcome_name="All-cause mortality",
    n_studies=8,
    total_n=total_n,
    pooled_effect=dl_or,
    ci_lower=ci_lower_or,
    ci_upper=ci_upper_or,
    certainty=certainty,
    downgrade_reasons=downgrade_reasons,
)

required_sof_keys = {
    "outcome", "n_studies", "total_n", "effect_with_ci",
    "certainty", "certainty_symbols", "downgrade_reasons",
}
check("SoF row has all required keys",
      required_sof_keys.issubset(sof_row.keys()),
      f"missing: {required_sof_keys - sof_row.keys()}")
check("SoF row certainty matches compute_grade result",
      sof_row["certainty"] == certainty)
check("SoF row n_studies == 8",
      sof_row["n_studies"] == 8)


# ---------------------------------------------------------------------------
# Step 7: Visualizations
# ---------------------------------------------------------------------------

print("\n=== Step 7: Visualizations ===")

# Build study list for forest plot
total_re_weight = sum(dl_result["weights"])
study_list = []
for i, res in enumerate(or_results):
    w_pct = dl_result["weights"][i] / total_re_weight * 100
    study_list.append({
        "label":     labels[i],
        "effect":    res["log_or"],
        "ci_lower":  res["ci_lower"],
        "ci_upper":  res["ci_upper"],
        "weight_pct": w_pct,
    })

pooled_dict = {
    "pooled":   dl_result["pooled"],
    "ci_lower": dl_result["ci_lower"],
    "ci_upper": dl_result["ci_upper"],
}

fp_svg = forest_plot_svg(study_list, pooled_dict, title="All-cause Mortality")
check("Forest plot SVG starts with '<svg'",
      fp_svg.strip().startswith("<svg"),
      f"starts with: {fp_svg[:20]!r}")
check("Forest plot SVG is non-empty (> 100 chars)",
      len(fp_svg) > 100)

fn_svg = funnel_plot_svg(log_ors, ses, pooled_log_or)
check("Funnel plot SVG starts with '<svg'",
      fn_svg.strip().startswith("<svg"))
check("Funnel plot SVG is non-empty (> 100 chars)",
      len(fn_svg) > 100)

prisma_counts = {
    "db_pubmed": 420,
    "db_central": 310,
    "db_ctgov": 80,
    "duplicates_removed": 95,
    "screened": 715,
    "excluded_screening": 640,
    "eligible": 75,
    "excluded_eligibility": 67,
    "included": 8,
}
pr_svg = prisma_flow_svg(prisma_counts)
check("PRISMA flow SVG starts with '<svg'",
      pr_svg.strip().startswith("<svg"))
check("PRISMA flow SVG is non-empty (> 100 chars)",
      len(pr_svg) > 100)

rob_data = [
    {
        "study": labels[i],
        "domains": [
            {"domain": "Randomisation", "judgment": rob_ratings[i]},
            {"domain": "Blinding",      "judgment": rob_ratings[i]},
            {"domain": "Attrition",     "judgment": "low"},
        ],
    }
    for i in range(8)
]
rob_svg = rob_traffic_light_svg(rob_data)
check("RoB traffic-light SVG starts with '<svg'",
      rob_svg.strip().startswith("<svg"))
check("RoB traffic-light SVG is non-empty (> 100 chars)",
      len(rob_svg) > 100)


# ---------------------------------------------------------------------------
# Step 8: Full report assembly
# ---------------------------------------------------------------------------

print("\n=== Step 8: Full report assembly ===")

pico = {
    "population":    "Adults with cardiovascular risk",
    "intervention":  "Novel therapy",
    "comparator":    "Placebo",
    "outcome":       "All-cause mortality",
    "question":      "Effect of novel therapy on all-cause mortality in adults",
}

search = {
    "query":      "(novel therapy) AND mortality AND RCT",
    "date_range": "2000-2024",
    "databases":  ["PubMed", "Cochrane CENTRAL", "ClinicalTrials.gov"],
}

char_studies = [
    {
        "first_author": f"Author{i+1}",
        "year":         2010 + i,
        "n_intervention": studies_2x2[i][0] + studies_2x2[i][1],
        "n_control":      studies_2x2[i][2] + studies_2x2[i][3],
        "intervention_description": "Novel therapy",
        "comparator_description":   "Placebo",
        "followup_duration":        "12 months",
        "rob_overall":              rob_ratings[i],
    }
    for i in range(8)
]
char_table = format_characteristics_table(char_studies)

outcome_entry = {
    "name":            "All-cause mortality",
    "pooling": {
        "pooled":   dl_result["pooled"],
        "ci_lower": dl_result["ci_lower"],
        "ci_upper": dl_result["ci_upper"],
        "p_value":  dl_result["p_value"],
    },
    "heterogeneity": {
        "i2":              isq_val,
        "q":               q_stat,
        "q_p_value":       q_pval,
        "prediction_lower": pi["lower"] if pi else None,
        "prediction_upper": pi["upper"] if pi else None,
    },
    "studies":          study_list,
    "effects_for_funnel": log_ors,
    "ses_for_funnel":     ses,
    "grade": {
        "certainty":          certainty,
        "certainty_symbols":  sof_row["certainty_symbols"],
        "downgrade_reasons":  downgrade_reasons,
    },
}

sensitivity_data = {
    "All-cause mortality": {
        "leave_one_out": [
            {"removed": r["excluded_study"], "pooled": r["pooled"]}
            for r in loo_results
        ],
        "fixed_vs_random": {
            "fixed":  fvr["fixed_pooled"],
            "random": fvr["random_pooled"],
        },
        "high_rob_excluded": {
            "n_removed": high_rob_res["n_excluded"],
            "pooled":    high_rob_res["pooled"],
        },
    }
}

pub_bias_data = {
    "All-cause mortality": {
        "egger_p": None,
        "note":    egger["reason"],
    }
}

report = assemble_report(
    pico=pico,
    search=search,
    prisma_counts=prisma_counts,
    characteristics_table=char_table,
    rob_summary="Two studies (Study 3, Study 7) were rated high risk of bias.",
    outcomes=[outcome_entry],
    sensitivity=sensitivity_data,
    publication_bias=pub_bias_data,
    prisma_svg=pr_svg,
    rob_svg=rob_svg,
)

# Markdown checks
md = report["markdown"]
check("Report markdown is a string",
      isinstance(md, str))
check("Markdown contains '# Meta-Analysis Report'",
      "# Meta-Analysis Report" in md)
check("Markdown contains '## PRISMA Flow Diagram'",
      "## PRISMA Flow Diagram" in md)
check("Markdown contains '## Characteristics of Included Studies'",
      "## Characteristics of Included Studies" in md)
check("Markdown contains '## Risk of Bias Summary'",
      "## Risk of Bias Summary" in md)
check("Markdown contains '## Results'",
      "## Results" in md)
check("Markdown contains '## Sensitivity Analyses'",
      "## Sensitivity Analyses" in md)
check("Markdown contains '## Publication Bias'",
      "## Publication Bias" in md)
check("Markdown contains '## GRADE Summary of Findings'",
      "## GRADE Summary of Findings" in md)
check("Markdown contains outcome name",
      "All-cause mortality" in md)

# JSON checks
j = report["json"]
check("JSON export is a dict", isinstance(j, dict))
required_json_keys = {"pico", "search", "prisma", "studies", "outcomes",
                      "grade_summary", "publication_bias"}
check("JSON has all required top-level keys",
      required_json_keys.issubset(j.keys()),
      f"missing: {required_json_keys - j.keys()}")
check("JSON outcomes is a list with 1 entry",
      isinstance(j["outcomes"], list) and len(j["outcomes"]) == 1)
check("JSON grade_summary has 1 entry",
      isinstance(j["grade_summary"], list) and len(j["grade_summary"]) == 1)
check("JSON PICO question preserved",
      j["pico"].get("question") == pico["question"])

# Write to temp file and verify valid JSON round-trip
with tempfile.NamedTemporaryFile(
    mode="w", suffix=".json", delete=False, encoding="utf-8"
) as tmp:
    json.dump(j, tmp, indent=2, default=str)
    tmp_path = tmp.name

with open(tmp_path, "r", encoding="utf-8") as f:
    reloaded = json.load(f)

check("Report JSON serialisable and reloadable",
      reloaded["pico"]["question"] == pico["question"])

# Clean up
os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Step 9: Cross-module consistency checks
# ---------------------------------------------------------------------------

print("\n=== Step 9: Cross-module consistency checks ===")

# DL pooled from pooling.py matches value used in report
report_pooled = report["json"]["outcomes"][0]["pooling"]["pooled"]
check("DL pooled in report JSON matches pooling module result",
      abs(report_pooled - dl_result["pooled"]) < 1e-12,
      f"report={report_pooled:.8f}, module={dl_result['pooled']:.8f}")

# tau² from pooling matches heterogeneity module (already tested in Step 2,
# re-verify via the Q statistic path)
q_check = cochrans_q(log_ors, ses)
tau2_cross = tau_squared_dl(q_check["q"], q_check["df"], fe_weights)
check("tau² cross-check: pooling == heterogeneity module (tol=1e-9)",
      abs(tau2_cross - dl_result["tau_sq"]) < 1e-9,
      f"hetmod={tau2_cross:.10f}, pooling={dl_result['tau_sq']:.10f}")

# GRADE assessment uses the I² that came from heterogeneity module
i2_used_in_grade = isq_val  # this is isq_res["i_squared"] computed in Step 3
i2_recomputed    = i_squared(q_check["q"], q_check["df"])["i_squared"]
check("I² value used in GRADE matches heterogeneity module recomputation",
      abs(i2_used_in_grade - i2_recomputed) < 1e-9,
      f"used={i2_used_in_grade:.6f}, recomputed={i2_recomputed:.6f}")

# MH OR and DL OR are in the same direction
check("MH OR and DL OR in the same direction (both < 1 or both > 1)",
      (mh_result["pooled"] < 1.0) == (dl_or < 1.0),
      f"MH OR={mh_result['pooled']:.4f}, DL OR={dl_or:.4f}")

# LOO excluded study labels match input labels
loo_labels = [r["excluded_study"] for r in loo_results]
check("LOO excluded study labels match input labels",
      loo_labels == labels,
      f"loo={loo_labels}, expected={labels}")

# Prediction interval from report JSON matches heterogeneity module
pi_lower_report = report["json"]["outcomes"][0]["heterogeneity"].get("prediction_lower")
# Note: report stores the values from outcome_entry which came from dl_result["prediction_interval"]
if pi is not None and pi_lower_report is not None:
    check("Prediction interval lower in report matches DL module",
          abs(pi_lower_report - pi["lower"]) < 1e-9,
          f"report={pi_lower_report:.8f}, module={pi['lower']:.8f}")


# ---------------------------------------------------------------------------
# Final summary
# ---------------------------------------------------------------------------

print(f"\n{'='*50}")
print(f"Integration test complete: {PASS} passed, {FAIL} failed")
if FAIL == 0:
    print("ALL TESTS PASSED")
else:
    print(f"ATTENTION: {FAIL} test(s) FAILED")
    sys.exit(1)
