# Meta-Analyst Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an end-to-end clinical meta-analysis agent skill (PICO → search → screen → extract → pool → GRADE → report) following Cochrane Handbook methodology.

**Architecture:** Three-phase pipeline (Identify → Appraise → Synthesize). All statistical computation in deterministic Python (scipy, statsmodels, numpy). LLM handles extraction, screening, and GRADE indirectness. Composes with Evidence Evaluator for per-study RoB 2.0. Tests use custom pass/fail counter (same pattern as evidence_evaluator).

**Tech Stack:** Python 3.10+, scipy, statsmodels, numpy. PubMed E-utilities, Cochrane CENTRAL API, ClinicalTrials.gov API v2. SVG generation for forest/funnel/PRISMA plots.

---

## File Structure

```
meta_analyst/
├── .claude-plugin/plugin.json              ← Plugin manifest
├── .gitignore
├── CLAUDE.md                               ← Project guidance for Claude Code
├── README.md
├── skills/meta-analyst/
│   ├── SKILL.md                            ← Skill entry point
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── effect_sizes.py                 ← log(OR), log(RR), RD, MD, SMD + SE
│   │   ├── pooling.py                      ← DL random-effects, IV fixed-effect, MH
│   │   ├── heterogeneity.py                ← Q, I², tau², H², prediction interval
│   │   ├── sensitivity.py                  ← Leave-one-out, high-RoB exclusion
│   │   ├── publication_bias.py             ← Egger's test
│   │   ├── grade.py                        ← GRADE certainty rule engine
│   │   ├── visualizations.py               ← Forest plot, funnel plot, PRISMA flow, RoB traffic light (SVG)
│   │   └── report.py                       ← Report assembly (Markdown + JSON)
│   └── references/
│       ├── phase_1_identify.md             ← PICO, search strategy, screening specs
│       ├── phase_2_appraise.md             ← Extraction, RoB, characteristics table specs
│       ├── phase_3_synthesize.md           ← Pooling, heterogeneity, sensitivity, GRADE specs
│       └── formulas.md                     ← All statistical formulas reference
├── tests/
│   ├── test_effect_sizes.py
│   ├── test_pooling.py
│   ├── test_heterogeneity.py
│   ├── test_sensitivity.py
│   ├── test_publication_bias.py
│   ├── test_grade.py
│   ├── test_visualizations.py
│   └── test_report.py
├── paper/
│   ├── research_note.md
│   └── submission/
│       └── submit.sh
└── docs/
    └── implementation-plan.md              ← This file
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `.gitignore`
- Create: `CLAUDE.md`
- Create: `skills/meta-analyst/pipeline/__init__.py`

- [ ] **Step 1: Create plugin manifest**

```json
{
  "name": "meta-analyst",
  "description": "End-to-end clinical meta-analysis of RCT intervention studies. Three-phase agentic pipeline: PICO-driven literature search, data extraction with RoB assessment, and deterministic statistical pooling with GRADE certainty ratings.",
  "version": "0.1.0",
  "author": {
    "name": "SciSpark"
  },
  "homepage": "https://scispark.ai",
  "repository": "https://github.com/SciSpark-ai/meta_analyst",
  "license": "MIT"
}
```

- [ ] **Step 2: Create .gitignore**

```
__pycache__/
*.pyc
*.pyo
.env
meta_analysis_*.md
meta_analysis_*.json
```

- [ ] **Step 3: Create initial CLAUDE.md**

Minimal version with repo structure, running tests, and architecture overview. Will be updated as modules are built.

- [ ] **Step 4: Create pipeline __init__.py**

Empty file to make `pipeline/` a package.

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin/plugin.json .gitignore CLAUDE.md skills/meta-analyst/pipeline/__init__.py
git commit -m "feat: project scaffolding — plugin manifest, gitignore, CLAUDE.md"
```

---

## Task 2: Effect Size Module

**Files:**
- Create: `skills/meta-analyst/pipeline/effect_sizes.py`
- Create: `tests/test_effect_sizes.py`

- [ ] **Step 1: Write failing tests for binary effect sizes**

Test `compute_log_or`, `compute_log_rr`, `compute_rd` against hand-calculated values. Use the custom pass/fail counter pattern from evidence_evaluator.

```python
# Example test cases (from Cochrane training data):
# Study: a=15, b=85, c=30, d=70
# OR = (15*70)/(85*30) = 0.4118, log(OR) = -0.8873
# SE = sqrt(1/15 + 1/85 + 1/30 + 1/70) = 0.3953
check("log_or_value", result.log_or, -0.8873, tol=0.001)
check("log_or_se", result.se, 0.3953, tol=0.001)
```

Also test zero-cell correction: `a=0, b=100, c=10, d=90` → adds 0.5 to all cells before computing.

- [ ] **Step 2: Run tests to verify they fail**

```bash
python tests/test_effect_sizes.py
```

Expected: ImportError or FAIL on all checks.

- [ ] **Step 3: Implement binary effect size functions**

```python
# effect_sizes.py exports:
def compute_log_or(a, b, c, d) -> dict:
    """Log odds ratio + SE from 2x2 table. Returns {log_or, se, or, ci_lower, ci_upper}."""

def compute_log_rr(a, b, c, d) -> dict:
    """Log risk ratio + SE from 2x2 table. Returns {log_rr, se, rr, ci_lower, ci_upper}."""

def compute_rd(a, b, c, d) -> dict:
    """Risk difference + SE from 2x2 table. Returns {rd, se, ci_lower, ci_upper}."""

def zero_cell_correction(a, b, c, d, correction=0.5) -> tuple:
    """Apply continuity correction if any cell is 0. Returns corrected (a, b, c, d)."""
```

Formulas:
- `log_OR = log(a*d / (b*c))`, `SE = sqrt(1/a + 1/b + 1/c + 1/d)`
- `log_RR = log((a/(a+b)) / (c/(c+d)))`, `SE = sqrt(1/a - 1/(a+b) + 1/c - 1/(c+d))`
- `RD = a/(a+b) - c/(c+d)`, `SE = sqrt(p1*(1-p1)/(a+b) + p2*(1-p2)/(c+d))`

- [ ] **Step 4: Run tests to verify they pass**

```bash
python tests/test_effect_sizes.py
```

Expected: All binary effect size checks PASS.

- [ ] **Step 5: Write failing tests for continuous effect sizes**

Test `compute_md` and `compute_smd` (Hedges' g):

```python
# Example: mean_i=5.2, sd_i=1.1, n_i=50, mean_c=4.8, sd_c=1.2, n_c=50
# MD = 0.4, SE = sqrt(1.1^2/50 + 1.2^2/50) = 0.2302
# s_pooled = sqrt(((49*1.21)+(49*1.44))/98) = 1.1511
# J = 1 - 3/(4*98-1) = 0.9924
# g = 0.4/1.1511 * 0.9924 = 0.3447
check("md_value", result.md, 0.4, tol=0.001)
check("smd_hedges_g", result.smd, 0.3447, tol=0.01)
```

- [ ] **Step 6: Implement continuous effect size functions**

```python
def compute_md(mean_i, sd_i, n_i, mean_c, sd_c, n_c) -> dict:
    """Mean difference + SE. Returns {md, se, ci_lower, ci_upper}."""

def compute_smd(mean_i, sd_i, n_i, mean_c, sd_c, n_c) -> dict:
    """Standardized mean difference (Hedges' g) + SE. Returns {smd, se, ci_lower, ci_upper}."""
```

- [ ] **Step 7: Run all effect size tests**

```bash
python tests/test_effect_sizes.py
```

Expected: All checks PASS (binary + continuous).

- [ ] **Step 8: Commit**

```bash
git add skills/meta-analyst/pipeline/effect_sizes.py tests/test_effect_sizes.py
git commit -m "feat: effect size module — log(OR), log(RR), RD, MD, SMD with tests"
```

---

## Task 3: Pooling Module

**Files:**
- Create: `skills/meta-analyst/pipeline/pooling.py`
- Create: `tests/test_pooling.py`

- [ ] **Step 1: Write failing tests for inverse-variance fixed-effect pooling**

Use a known dataset (e.g., 5 studies with known log(OR) + SE values, verify pooled estimate against RevMan/metafor output).

```python
# 5-study dataset (from Cochrane Handbook Table 10.3 or equivalent):
effects = [-0.887, -0.511, -0.223, -0.693, -0.357]
ses =     [0.395,  0.302,  0.250,  0.412,  0.280]
# Expected fixed-effect pooled log(OR) ≈ -0.424, SE ≈ 0.138
check("fixed_pooled", result.pooled, -0.424, tol=0.02)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python tests/test_pooling.py
```

- [ ] **Step 3: Implement inverse-variance fixed-effect**

```python
def pool_fixed_effect_iv(effects, ses) -> dict:
    """Inverse-variance fixed-effect pooling.
    Returns {pooled, se, ci_lower, ci_upper, p_value, weights}."""
```

Formula: `w_i = 1/SE_i²`, `pooled = Σ(w_i * θ_i) / Σw_i`, `SE = sqrt(1/Σw_i)`

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Write failing tests for DerSimonian-Laird random-effects**

Same dataset, verify tau², random-effects pooled estimate, prediction interval.

```python
# Expected: tau² > 0 (heterogeneity present), RE pooled ≈ -0.468, wider CI than fixed
check("tau_sq_positive", result.tau_sq > 0, True)
check("re_pooled", result.pooled, -0.468, tol=0.05)
check("re_ci_wider", result.ci_upper - result.ci_lower > fixed_ci_width, True)
```

- [ ] **Step 6: Implement DerSimonian-Laird random-effects**

```python
def pool_random_effects_dl(effects, ses) -> dict:
    """DerSimonian-Laird random-effects pooling.
    Returns {pooled, se, ci_lower, ci_upper, p_value, tau_sq, weights, prediction_interval}."""
```

Formula:
1. Fixed weights → Q → tau² = max(0, (Q-(k-1)) / (Σw - Σw²/Σw))
2. RE weights: `w_i* = 1/(SE_i² + tau²)`
3. Prediction interval: `pooled ± t_(k-2,0.975) * sqrt(SE² + tau²)`

- [ ] **Step 7: Write failing tests for Mantel-Haenszel pooling**

Test with 2x2 tables directly (not pre-computed effect sizes).

```python
# tables = [(a1,b1,c1,d1), (a2,b2,c2,d2), ...]
# Verify MH OR matches manual computation
```

- [ ] **Step 8: Implement Mantel-Haenszel**

```python
def pool_mantel_haenszel(tables, measure="OR") -> dict:
    """Mantel-Haenszel pooling from 2x2 tables.
    measure: 'OR' or 'RR'. Returns {pooled, se, ci_lower, ci_upper, p_value}."""
```

- [ ] **Step 9: Run all pooling tests**

```bash
python tests/test_pooling.py
```

Expected: All checks PASS.

- [ ] **Step 10: Commit**

```bash
git add skills/meta-analyst/pipeline/pooling.py tests/test_pooling.py
git commit -m "feat: pooling module — DL random-effects, IV fixed-effect, MH"
```

---

## Task 4: Heterogeneity Module

**Files:**
- Create: `skills/meta-analyst/pipeline/heterogeneity.py`
- Create: `tests/test_heterogeneity.py`

- [ ] **Step 1: Write failing tests**

```python
# Using same 5-study dataset from Task 3:
# Q = Σ w_i * (θ_i - θ_fixed)² — expected ≈ 6.8
# I² = max(0, (Q-df)/Q * 100) — expected ≈ 41%
# Interpretation: "moderate heterogeneity"
check("q_stat", result.q, 6.8, tol=0.5)
check("i_squared", result.i_squared, 41.0, tol=5.0)
check("interpretation", result.interpretation, "moderate")
```

Also test edge cases:
- k=1 study: Q=0, I²=0, tau²=0
- Homogeneous studies (identical effects): Q≈0, I²=0
- Extreme heterogeneity (I²>90%)

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement heterogeneity functions**

```python
def cochrans_q(effects, ses) -> dict:
    """Returns {q, df, p_value}."""

def i_squared(q, df) -> dict:
    """Returns {i_squared, interpretation}."""
    # 0-40%: "low", 30-60%: "moderate", 50-75%: "substantial", 75-100%: "considerable"

def tau_squared_dl(q, df, weights) -> float:
    """DerSimonian-Laird tau² estimator."""

def h_squared(q, df) -> float:
    """H² = Q/df."""

def prediction_interval(pooled, se_pooled, tau_sq, k) -> dict:
    """Returns {lower, upper}. Uses t-distribution with k-2 df."""
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add skills/meta-analyst/pipeline/heterogeneity.py tests/test_heterogeneity.py
git commit -m "feat: heterogeneity module — Q, I², tau², prediction interval"
```

---

## Task 5: Sensitivity Analysis Module

**Files:**
- Create: `skills/meta-analyst/pipeline/sensitivity.py`
- Create: `tests/test_sensitivity.py`

- [ ] **Step 1: Write failing tests**

```python
# Leave-one-out: remove each study, re-pool, check:
# - Correct number of results (k results for k studies)
# - Removing most extreme study shifts pooled estimate toward null
# - Each result has correct N-1 studies

# High-RoB exclusion:
# rob_ratings = ["low", "low", "high", "low", "high"]
# Should re-pool with only indices 0,1,3 (the 3 "low" studies)
check("n_remaining", result.n_studies, 3)
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement sensitivity functions**

```python
def leave_one_out(effects, ses, study_labels=None) -> list:
    """Returns list of {excluded_study, pooled, ci_lower, ci_upper, direction_changed, significance_changed}."""

def exclude_high_rob(effects, ses, rob_ratings, study_labels=None) -> dict:
    """Re-pool excluding studies with overall='high'.
    Returns {n_remaining, pooled, ci_lower, ci_upper, changed_significance}."""

def fixed_vs_random_comparison(effects, ses) -> dict:
    """Returns {fixed_pooled, random_pooled, divergence, small_study_flag}."""
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add skills/meta-analyst/pipeline/sensitivity.py tests/test_sensitivity.py
git commit -m "feat: sensitivity module — leave-one-out, high-RoB exclusion, fixed-vs-random"
```

---

## Task 6: Publication Bias Module

**Files:**
- Create: `skills/meta-analyst/pipeline/publication_bias.py`
- Create: `tests/test_publication_bias.py`

- [ ] **Step 1: Write failing tests**

```python
# Egger's test with known asymmetric data (biased):
# effects and SEs deliberately skewed — small studies have larger effects
# Expected: significant intercept (p < 0.10)
check("eggers_significant", result.p_value < 0.10, True)

# Symmetric data (unbiased):
# Expected: non-significant intercept (p >= 0.10)
check("eggers_not_significant", result.p_value >= 0.10, True)

# k < 10: should return skip notice
check("skip_flag", result.skipped, True)
check("skip_reason", "Fewer than 10" in result.reason, True)
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement publication bias functions**

```python
def eggers_test(effects, ses) -> dict:
    """Egger's regression test for funnel asymmetry.
    Skips if k < 10. Returns {intercept, se, p_value, skipped, reason}."""

def funnel_plot_data(effects, ses, pooled) -> dict:
    """Returns {points: [{effect, se}], pooled, pseudo_ci_lines}."""
```

Egger's: regress `effect_i / SE_i` on `1/SE_i` using OLS (`statsmodels.api.OLS`). Test intercept ≠ 0.

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add skills/meta-analyst/pipeline/publication_bias.py tests/test_publication_bias.py
git commit -m "feat: publication bias module — Egger's test with k<10 guard"
```

---

## Task 7: GRADE Certainty Module

**Files:**
- Create: `skills/meta-analyst/pipeline/grade.py`
- Create: `tests/test_grade.py`

- [ ] **Step 1: Write failing tests**

```python
# Test each domain independently:

# Risk of bias: 3 low, 2 high → majority not high → -1 (serious)
check("rob_downgrade", assess_risk_of_bias(["low","low","high","low","high"]), -1)

# Risk of bias: 4 high, 1 low → majority high → -2 (very serious)
check("rob_downgrade_severe", assess_risk_of_bias(["high","high","high","high","low"]), -2)

# Inconsistency: I²=30 → 0 (no downgrade)
check("inconsistency_none", assess_inconsistency(30.0), 0)

# Inconsistency: I²=60 → -1 (serious)
check("inconsistency_serious", assess_inconsistency(60.0), -1)

# Inconsistency: I²=80 → -2 (very serious)
check("inconsistency_very_serious", assess_inconsistency(80.0), -2)

# Imprecision: CI crosses null (e.g., OR CI [0.85, 1.20]) → -1
check("imprecision_crosses_null", assess_imprecision(0.85, 1.20, 1.0, ois=2000, total_n=1500), -1)

# Publication bias: Egger p=0.03 → -1
check("pub_bias_flag", assess_publication_bias(0.03, k=12), -1)

# Full GRADE: start High, -1 risk of bias, -1 inconsistency → "Low"
check("grade_final", compute_grade("High", {"rob": -1, "inconsistency": -1, "indirectness": 0, "imprecision": 0, "publication_bias": 0}), "Low")
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement GRADE functions**

```python
def assess_risk_of_bias(rob_ratings: list) -> int:
    """Returns downgrade: 0, -1, or -2 based on proportion of high-risk studies."""

def assess_inconsistency(i_squared: float) -> int:
    """Returns downgrade: 0 if I²<50, -1 if 50-75, -2 if >75."""

def assess_imprecision(ci_lower, ci_upper, null_value, ois=None, total_n=None) -> int:
    """Returns downgrade: 0, -1, or -2. Checks CI crosses null + OIS."""

def assess_publication_bias(eggers_p, k) -> int:
    """Returns downgrade: 0 or -1. Only applies if k>=10 and p<0.10."""

def compute_grade(start_certainty, downgrades: dict) -> str:
    """Apply downgrades to starting certainty. Returns 'High'|'Moderate'|'Low'|'Very Low'."""

def grade_summary_row(outcome_name, n_studies, total_n, pooled_effect, ci, certainty, reasons) -> dict:
    """Build one row of the Summary of Findings table."""
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add skills/meta-analyst/pipeline/grade.py tests/test_grade.py
git commit -m "feat: GRADE certainty module — per-domain assessment + summary"
```

---

## Task 8: Visualizations Module

**Files:**
- Create: `skills/meta-analyst/pipeline/visualizations.py`
- Create: `tests/test_visualizations.py`

- [ ] **Step 1: Write failing tests**

Tests verify SVG output is well-formed and contains expected elements:

```python
# Forest plot: verify SVG contains study labels, diamond for pooled, null line
svg = forest_plot_svg(studies, pooled_result)
check("is_svg", svg.startswith("<svg"), True)
check("has_null_line", 'x1="' in svg, True)  # null effect line
check("has_diamond", "polygon" in svg or "diamond" in svg, True)
check("has_study_labels", studies[0]["label"] in svg, True)

# Funnel plot: verify axes and points
svg = funnel_plot_svg(effects, ses, pooled)
check("funnel_is_svg", svg.startswith("<svg"), True)
check("has_points", svg.count("<circle") >= len(effects), True)

# PRISMA: verify boxes with counts
svg = prisma_flow_svg({"identified": 150, "screened": 140, "eligible": 25, "included": 12,
                        "duplicates_removed": 10, "excluded_screening": 115, "excluded_eligibility": 13,
                        "db_pubmed": 80, "db_central": 50, "db_ctgov": 20})
check("prisma_is_svg", svg.startswith("<svg"), True)
check("has_included_count", "12" in svg, True)

# RoB traffic light: verify colored circles
svg = rob_traffic_light_svg(rob_data)
check("traffic_is_svg", svg.startswith("<svg"), True)
check("has_green", "#4caf50" in svg or "green" in svg.lower(), True)
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement forest plot**

```python
def forest_plot_svg(studies: list, pooled: dict, fixed_pooled: dict = None,
                    title: str = "", null_value: float = 0.0, measure_label: str = "Effect") -> str:
    """Generate forest plot as SVG string.
    studies: [{label, effect, ci_lower, ci_upper, weight_pct}]
    pooled: {pooled, ci_lower, ci_upper} (random-effects)
    fixed_pooled: optional fixed-effect result for comparison line
    """
```

- [ ] **Step 4: Implement funnel plot**

```python
def funnel_plot_svg(effects: list, ses: list, pooled: float) -> str:
    """Funnel plot: effect vs SE (inverted y-axis). Includes pseudo-95% CI lines."""
```

- [ ] **Step 5: Implement PRISMA flow diagram**

```python
def prisma_flow_svg(counts: dict) -> str:
    """PRISMA 2020 flow diagram with per-database counts and exclusion reasons."""
```

- [ ] **Step 6: Implement RoB traffic light**

```python
def rob_traffic_light_svg(rob_data: list) -> str:
    """RoB summary: studies as rows, domains as columns, colored circles.
    rob_data: [{study, domains: [{domain, judgment}]}]"""
```

- [ ] **Step 7: Run all visualization tests**

```bash
python tests/test_visualizations.py
```

- [ ] **Step 8: Commit**

```bash
git add skills/meta-analyst/pipeline/visualizations.py tests/test_visualizations.py
git commit -m "feat: visualizations — forest plot, funnel plot, PRISMA flow, RoB traffic light (SVG)"
```

---

## Task 9: Report Assembly Module

**Files:**
- Create: `skills/meta-analyst/pipeline/report.py`
- Create: `tests/test_report.py`

- [ ] **Step 1: Write failing tests**

```python
# Test Markdown report assembly:
report = assemble_report(
    pico={"population": "HF patients", "intervention": "SGLT2i", ...},
    search={"date_searched": "2026-03-23", "searches": [...]},
    prisma_counts={...},
    characteristics_table=[...],
    rob_summary=[...],
    outcomes=[{
        "name": "All-cause mortality",
        "pooling": {"pooled": 0.75, "ci_lower": 0.65, "ci_upper": 0.87, ...},
        "heterogeneity": {"i_squared": 25, ...},
        "grade": {"certainty": "High", ...},
    }],
    sensitivity={...},
    publication_bias={...},
)

check("has_title", "# Meta-Analysis Report" in report["markdown"], True)
check("has_prisma", "<svg" in report["markdown"], True)
check("has_forest", "Forest Plot" in report["markdown"], True)
check("has_grade_table", "Summary of Findings" in report["markdown"], True)
check("has_disclaimer", "AI agent skill" in report["markdown"], True)
check("json_has_pooled", report["json"]["outcomes"][0]["pooling"]["pooled"], 0.75)

# Test JSON export structure:
check("json_keys", set(report["json"].keys()), {"pico", "search", "prisma", "studies", "outcomes", "grade_summary", "sensitivity", "publication_bias"})
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement report assembly**

```python
def assemble_report(pico, search, prisma_counts, characteristics_table,
                    rob_summary, outcomes, sensitivity, publication_bias,
                    prisma_svg=None, rob_svg=None) -> dict:
    """Assemble full Cochrane-style report.
    Returns {"markdown": str, "json": dict}."""

def format_characteristics_table(studies: list) -> str:
    """Format 'Characteristics of Included Studies' as Markdown table."""

def format_grade_sof_table(outcomes: list) -> str:
    """Format GRADE Summary of Findings as Markdown table with certainty symbols."""
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add skills/meta-analyst/pipeline/report.py tests/test_report.py
git commit -m "feat: report assembly — Markdown + JSON dual output"
```

---

## Task 10: Reference Documents

**Files:**
- Create: `skills/meta-analyst/references/formulas.md`
- Create: `skills/meta-analyst/references/phase_1_identify.md`
- Create: `skills/meta-analyst/references/phase_2_appraise.md`
- Create: `skills/meta-analyst/references/phase_3_synthesize.md`

- [ ] **Step 1: Write formulas.md**

All statistical formulas used by the pipeline: effect sizes (OR, RR, RD, MD, SMD/Hedges' g), pooling (IV, DL, MH), heterogeneity (Q, I², tau², H², prediction interval), Egger's regression, GRADE imprecision (OIS), zero-cell correction. Each with notation, formula, and Python function reference.

- [ ] **Step 2: Write phase_1_identify.md**

Stage specs for PICO formalization, search strategy (Cochrane MECIR, RCT filter), search execution (PubMed E-utilities, CENTRAL API, ClinicalTrials.gov API v2), abstract screening (inclusion/exclusion criteria), PRISMA flow. Typed I/O contracts per stage. Human checkpoint instructions.

- [ ] **Step 3: Write phase_2_appraise.md**

Stage specs for data extraction (field list, 3× majority vote protocol, binary/continuous outcome extraction), RoB assessment (Evidence Evaluator composition + fallback), characteristics table assembly. Human checkpoint instructions.

- [ ] **Step 4: Write phase_3_synthesize.md**

Stage specs for effect size computation, pooling (DL default, fixed comparison), heterogeneity interpretation (Cochrane Handbook 10.10.2 thresholds), sensitivity analyses (leave-one-out, high-RoB exclusion, fixed-vs-random), publication bias (Egger's, k≥10 guard), GRADE (5 domains, downgrade rules, SoF table format), report assembly.

- [ ] **Step 5: Commit**

```bash
git add skills/meta-analyst/references/
git commit -m "feat: reference documents — formulas, phase 1-3 stage specs"
```

---

## Task 11: SKILL.md Entry Point

**Files:**
- Create: `skills/meta-analyst/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

Following the evidence_evaluator SKILL.md pattern:
- Frontmatter with name, description, trigger conditions
- Setup instructions (pip install, verification command)
- Quick start (3-phase overview)
- Pipeline architecture diagram
- Per-phase execution instructions with code invocation examples
- Human checkpoint instructions
- Output format (Markdown + JSON)
- Reference doc pointers

Key trigger phrases: "meta-analysis", "pool studies", "systematic review", "combine RCTs", "forest plot", "GRADE evidence", "Cochrane review".

- [ ] **Step 2: Commit**

```bash
git add skills/meta-analyst/SKILL.md
git commit -m "feat: SKILL.md entry point — three-phase meta-analysis pipeline"
```

---

## Task 12: Integration Test with Known Meta-Analysis

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Select validation dataset**

Use a well-known published meta-analysis with available 2×2 tables. Good candidates:
- Cochrane training dataset (publicly available)
- A published Cochrane review with accessible per-study data

Extract per-study data (events, totals per arm) and known pooled results.

- [ ] **Step 2: Write integration test**

Run the full Phase 3 deterministic pipeline (effect sizes → pooling → heterogeneity → sensitivity → publication bias → GRADE) on the validation dataset. Verify all outputs match published values within rounding tolerance.

```python
# Full pipeline test:
# 1. Compute effect sizes for each study
# 2. Pool with DL random-effects
# 3. Assess heterogeneity
# 4. Run leave-one-out
# 5. Run Egger's (if k >= 10)
# 6. Compute GRADE
# 7. Assemble report
# Verify pooled OR, CI, I², and GRADE certainty match expected
```

- [ ] **Step 3: Run integration test**

```bash
python tests/test_integration.py
```

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "feat: integration test — full Phase 3 validated against published meta-analysis"
```

---

## Task 13: CLAUDE.md + README.md Update

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`

- [ ] **Step 1: Update CLAUDE.md**

Full project guidance matching evidence_evaluator pattern: project overview, repo structure, running tests (with expected pass counts), architecture, key domain rules (Cochrane methodology, GRADE domains, pooling defaults), tech context.

- [ ] **Step 2: Update README.md**

User-facing documentation: what it does, install command, quick start, example output.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md README.md
git commit -m "docs: comprehensive CLAUDE.md and README.md"
```

---

## Task 14: Research Note + Submission

**Files:**
- Create: `paper/research_note.md`
- Create: `paper/submission/submit.sh`

- [ ] **Step 1: Write research note**

Following Claw4S format (1-4 pages). Sections:
1. Abstract
2. Introduction — gap in executable meta-analysis skills
3. Pipeline Architecture — three-phase design, deterministic core
4. Evaluation — integration test results, validation against published meta-analysis
5. Related Work — ScienceClaw (computation template only), traditional tools (metafor, RevMan)
6. Conclusion

Co-authors: Cu's CCbot, Tong Shan, Lei Li.

- [ ] **Step 2: Write submit.sh**

Copy from evidence_evaluator, adapt field names and title.

- [ ] **Step 3: Commit**

```bash
git add paper/
git commit -m "feat: research note and submission script for Claw4S"
```

---

## Task 15: Final Push + Submit

- [ ] **Step 1: Run all tests**

```bash
python tests/test_effect_sizes.py
python tests/test_pooling.py
python tests/test_heterogeneity.py
python tests/test_sensitivity.py
python tests/test_publication_bias.py
python tests/test_grade.py
python tests/test_visualizations.py
python tests/test_report.py
python tests/test_integration.py
```

All must pass.

- [ ] **Step 2: Push to GitHub**

```bash
git push origin main
```

- [ ] **Step 3: Register and submit to clawRxiv**

```bash
bash paper/submission/submit.sh <API_KEY>
```

- [ ] **Step 4: Verify submission**

```bash
curl -s http://18.118.210.52/api/posts/<POST_ID> | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Title: {d[\"title\"]}\nSkill: {d[\"skillMd\"] is not None}')"
```
