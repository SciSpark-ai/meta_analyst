# Meta-Analyst: Clinical Meta-Analysis Agent Skill — Design Spec

**Date:** 2026-03-23
**Authors:** Cu's CCbot, Tong Shan, Lei Li
**Status:** Draft

---

## 1 Overview

Meta-Analyst is an executable agent skill that performs end-to-end pairwise meta-analysis of RCT intervention studies, following the Cochrane Handbook methodology. It takes a free-text clinical question as input and produces a Cochrane-style report with forest plots, GRADE certainty ratings, and structured JSON — all through a semi-automated pipeline with human checkpoints at critical decision points.

**Scope constraints (v1):**
- Pairwise meta-analysis only (no network meta-analysis)
- RCT intervention studies only (no observational, diagnostic, or prognostic)
- Binary + continuous outcomes (no time-to-event as primary input, though HR can be approximated)
- Three search databases: PubMed, Cochrane CENTRAL, ClinicalTrials.gov (all free APIs)

**Conference target:** Claw4S 2026 (deadline April 5, 2026)

---

## 2 Architecture

### 2.1 Three-Phase Pipeline

```
Input: Free-text clinical question
  → Phase 1 — IDENTIFY (search + screen)
      Stage 1.1: PICO Formalization                    [LLM]
      Stage 1.2: Search Strategy Construction           [LLM → human checkpoint #1]
      Stage 1.3: Search Execution                       [PubMed API]
      Stage 1.4: Abstract Screening                     [LLM → human checkpoint #2]
      Stage 1.5: PRISMA Flow Diagram                    [deterministic]
  → Phase 2 — APPRAISE (extract + assess)
      Stage 2.1: Data Extraction                        [LLM, 3× majority vote]
      Stage 2.2: Risk of Bias Assessment                [Evidence Evaluator / fallback LLM]
      Stage 2.3: Characteristics of Included Studies    [deterministic assembly]
      → human checkpoint #3
  → Phase 3 — SYNTHESIZE (pool + grade + report)
      Stage 3.1: Effect Size Computation                [deterministic Python]
      Stage 3.2: Meta-Analytic Pooling                  [deterministic Python]
      Stage 3.3: Heterogeneity Assessment               [deterministic Python]
      Stage 3.4: Sensitivity Analyses                   [deterministic Python]
      Stage 3.5: Publication Bias                       [deterministic Python]
      Stage 3.6: GRADE Summary of Findings              [rule engine + LLM]
      Stage 3.7: Report Assembly                        [deterministic + LLM narrative]
  → Output: Markdown report + JSON export
```

### 2.2 Design Principles

1. **Deterministic where possible.** All statistical computation (effect sizes, pooling, heterogeneity, sensitivity, Egger's test) runs in Python (scipy, statsmodels, numpy). The LLM never computes statistics.
2. **Composable.** Phase 2 invokes Evidence Evaluator for per-study RoB 2.0 assessment. If not installed, falls back to a streamlined built-in checklist.
3. **Human-in-the-loop.** Three checkpoints at natural Cochrane decision points: (1) search strategy approval, (2) screening shortlist confirmation, (3) extraction + RoB review before synthesis.
4. **Auditable.** Every computation includes a trace. Every LLM judgment includes a rationale. The search strategy, screening decisions, and extraction data are all logged.
5. **Dual output.** Markdown report for humans, JSON for downstream agent consumption.

### 2.3 Dependency on Evidence Evaluator

Meta-Analyst composes with Evidence Evaluator (`SciSpark-ai/evidence_evaluator`) for per-study risk-of-bias assessment. The dependency is optional:

- **If installed:** Meta-Analyst invokes Evidence Evaluator on each included study, extracting RoB 2.0 domain judgments (5 domains) and overall risk classification from the generated report.
- **If not installed:** Falls back to a streamlined RoB 2.0 checklist built into Meta-Analyst — 5 domains, low/some concerns/high per domain, brief LLM justification per judgment.

This design means Meta-Analyst is fully functional standalone but produces richer assessments when composed with Evidence Evaluator.

---

## 3 Phase 1 — Identify

### 3.1 Stage 1.1: PICO Formalization

**Input:** Free-text clinical question (e.g., "Do SGLT2 inhibitors reduce mortality in heart failure?")

**Process (LLM):**
- Extract structured PICO elements:
  - **P**opulation: condition, age range, severity, setting
  - **I**ntervention: drug class or specific agent, dose if specified
  - **C**omparator: placebo, active comparator, standard care
  - **O**utcome(s): primary and secondary, classified as binary or continuous
- Generate MeSH terms for each PICO element via NLM MeSH API lookup
- Generate free-text synonyms for each element
- Classify each outcome as binary (events/totals) or continuous (mean/SD/N)

**Output:**
```json
{
  "population": { "description": "...", "mesh_terms": [...], "synonyms": [...] },
  "intervention": { "description": "...", "mesh_terms": [...], "synonyms": [...] },
  "comparator": { "description": "...", "mesh_terms": [...], "synonyms": [...] },
  "outcomes": [
    { "name": "...", "type": "binary|continuous", "mesh_terms": [...], "synonyms": [...] }
  ],
  "pico_search_string": "..."
}
```

### 3.2 Stage 1.2: Search Strategy Construction

**Process (LLM):**
- Build Boolean query following Cochrane MECIR standards:
  - OR within each PICO concept (MeSH + free-text synonyms)
  - AND across P, I, C concepts (outcomes typically not included in search to avoid missing relevant studies)
  - Apply Cochrane Highly Sensitive Search Strategy RCT filter
- Format for PubMed syntax (MeSH[MH], field tags, Boolean operators)
- Adapt query syntax for each database (PubMed, CENTRAL, ClinicalTrials.gov)

**Human checkpoint #1:** Present the search strategy to the user. User can approve, edit, or request regeneration. The approved query is logged verbatim for reproducibility.

**Output:**
```json
{
  "searches": [
    {
      "database": "PubMed",
      "query": "((heart failure[MH] OR cardiac failure[tiab] OR ...) AND (SGLT2[tiab] OR ...) AND (randomized controlled trial[pt] OR ...))",
      "rct_filter": "Cochrane Highly Sensitive"
    },
    {
      "database": "Cochrane CENTRAL",
      "query": "...",
      "rct_filter": "built-in (CENTRAL indexes RCTs only)"
    },
    {
      "database": "ClinicalTrials.gov",
      "query": "...",
      "rct_filter": "Interventional studies filter"
    }
  ],
  "date_searched": "2026-03-23",
  "user_approved": true,
  "user_edits": "none | description of changes"
}
```

### 3.3 Stage 1.3: Search Execution

**Process (API):**
- Execute approved queries across all three databases:
  - **PubMed:** E-utilities API (`esearch.fcgi` → `efetch.fcgi`)
  - **Cochrane CENTRAL:** Cochrane Library API (free, returns structured trial records)
  - **ClinicalTrials.gov:** API v2 (`https://clinicaltrials.gov/api/v2/studies`) — captures registered trials including unpublished results, reducing publication bias
- Retrieve per record: PMID/NCT ID, title, abstract, authors, journal, year, DOI, publication type, source database
- Deduplicate across databases by PMID, DOI, and title fuzzy matching
- Log: per-database hit counts, total before/after deduplication

**Output:** Array of deduplicated study records with metadata + abstracts + source database tag.

### 3.4 Stage 1.4: Abstract Screening

**Process (LLM):**
- For each abstract, evaluate against inclusion criteria derived from PICO:
  1. Study design: Is this an RCT? (exclude non-RCTs)
  2. Population: Does the population match the PICO population?
  3. Intervention: Does the intervention match?
  4. Comparator: Is there an appropriate comparator arm?
  5. Outcome: Is at least one specified outcome reported or likely reported?
- Classification: `include` / `exclude` / `uncertain`
- Each decision includes a one-sentence rationale

**Human checkpoint #2:** Present the screening results:
- Count: X included, Y excluded, Z uncertain
- List of included studies with rationales
- List of uncertain studies for user decision
- User confirms final inclusion list

**Output:**
```json
{
  "total_screened": 150,
  "included": [{ "pmid": "...", "title": "...", "rationale": "..." }, ...],
  "excluded": [{ "pmid": "...", "reason": "..." }, ...],
  "uncertain_resolved": [{ "pmid": "...", "user_decision": "include|exclude" }, ...]
}
```

### 3.5 Stage 1.5: PRISMA Flow Diagram

**Process (deterministic):**
- Generate PRISMA 2020 flow diagram from screening counts
- Sections: Identification (records per database: PubMed n=X, CENTRAL n=Y, ClinicalTrials.gov n=Z; duplicates removed) → Screening (abstracts screened, excluded with reasons) → Included (studies in quantitative synthesis)
- Render as inline SVG

**Output:** SVG string + structured counts JSON.

---

## 4 Phase 2 — Appraise

### 4.1 Stage 2.1: Data Extraction

**Input:** List of included studies (PMIDs/DOIs + abstracts, full text if accessible)

**Process (LLM, 3× majority vote):**
- For each study, extract a standardized data form:

| Field | Type | Required |
|---|---|---|
| first_author | string | yes |
| year | int | yes |
| journal | string | yes |
| pmid | string | yes |
| country | string | no |
| multicenter | boolean | no |
| n_intervention | int | yes |
| n_control | int | yes |
| age_mean | float | no |
| pct_female | float | no |
| intervention_description | string | yes |
| comparator_description | string | yes |
| followup_duration | string | yes |
| funding_source | string | no |
| registration_number | string | no |
| outcomes | array | yes |

- Each outcome entry:

| Field | Type | Applies to |
|---|---|---|
| name | string | all |
| type | "binary" or "continuous" | all |
| events_intervention | int | binary |
| n_intervention | int | binary |
| events_control | int | binary |
| n_control | int | binary |
| mean_intervention | float | continuous |
| sd_intervention | float | continuous |
| n_intervention | int | continuous |
| mean_control | float | continuous |
| sd_control | float | continuous |
| n_control | int | continuous |
| effect_estimate | float | all (if reported) |
| effect_type | string | all (OR/RR/HR/MD/SMD) |
| ci_lower | float | all |
| ci_upper | float | all |
| p_value | float | all |

- 3× independent extraction with majority vote on all numeric fields
- Fields with disagreement flagged as `low_confidence`

**Output:** Per-study extraction JSON array.

### 4.2 Stage 2.2: Risk of Bias Assessment

**Primary path (Evidence Evaluator installed):**
- For each included study, invoke Evidence Evaluator skill
- Extract from the generated report:
  - Per-domain RoB 2.0 judgments (5 domains): low / some concerns / high
  - Supporting justification per domain
  - Overall risk of bias classification
- If Evidence Evaluator is not installed or fails, fall back to secondary path

**Fallback path (built-in streamlined RoB 2.0):**
- LLM assesses 5 RoB 2.0 domains per study:
  1. Randomization process
  2. Deviations from intended interventions
  3. Missing outcome data
  4. Measurement of the outcome
  5. Selection of the reported result
- Per domain: low / some concerns / high + one-sentence justification
- Overall: low (all low) / some concerns (any some concerns, none high) / high (any high)

**Output:**
```json
{
  "rob_tool": "RoB 2.0",
  "assessment_method": "evidence_evaluator | streamlined_fallback",
  "studies": [
    {
      "pmid": "...",
      "domains": [
        { "domain": "randomization", "judgment": "low", "justification": "..." },
        ...
      ],
      "overall": "low"
    },
    ...
  ]
}
```

**Visualization:** RoB traffic light table (SVG) — studies as rows, domains as columns, colored circles (green/yellow/red).

### 4.3 Stage 2.3: Characteristics of Included Studies Table

**Process (deterministic assembly):**
- Assemble standard "Table 1" from Stages 2.1 + 2.2:
  - Columns: Study (author year), N (I/C), Population, Intervention, Comparator, Outcomes, Follow-up, RoB Overall
- Sort by year ascending

**Human checkpoint #3:** User reviews:
- Extraction data (especially numeric values — events, totals, means, SDs)
- RoB assessments (especially any "high" ratings)
- User can correct any values before synthesis proceeds

**Output:** Formatted Markdown table + structured JSON.

---

## 5 Phase 3 — Synthesize

### 5.1 Stage 3.1: Effect Size Computation

**Process (deterministic Python):**

For each study, per outcome:

**Binary outcomes:**
- Compute log(OR) + SE from 2×2 table:
  - `log_OR = log(a*d / b*c)`
  - `SE = sqrt(1/a + 1/b + 1/c + 1/d)`
- Also compute log(RR) + SE and RD + SE
- Zero-cell correction: if any cell = 0, add 0.5 to all cells of that study (continuity correction)
- Default effect measure: OR (user can override to RR or RD)

**Continuous outcomes:**
- Compute MD (mean difference) + SE:
  - `MD = mean_I - mean_C`
  - `SE = sqrt(sd_I²/n_I + sd_C²/n_C)`
- Compute SMD (Hedges' g) + SE:
  - `g = (mean_I - mean_C) / s_pooled * J`
  - Where `s_pooled = sqrt(((n_I-1)*sd_I² + (n_C-1)*sd_C²) / (n_I + n_C - 2))`
  - `J = 1 - 3/(4*(n_I + n_C - 2) - 1)` (small-sample correction)
- Default: MD if same scale across studies, SMD if different scales

**Output:** Per-study effect size + SE + weight (for forest plot).

### 5.2 Stage 3.2: Meta-Analytic Pooling

**Process (deterministic Python):**

Per outcome:

**Random-effects model (DerSimonian-Laird) — default:**
1. Compute fixed-effect weights: `w_i = 1 / SE_i²`
2. Compute Q statistic: `Q = Σ w_i * (θ_i - θ_fixed)²`
3. Compute tau²: `tau² = max(0, (Q - (k-1)) / (Σw_i - Σw_i²/Σw_i))`
4. Random-effects weights: `w_i* = 1 / (SE_i² + tau²)`
5. Pooled estimate: `θ_RE = Σ(w_i* × θ_i) / Σw_i*`
6. SE of pooled: `SE_RE = sqrt(1 / Σw_i*)`
7. 95% CI: `θ_RE ± 1.96 × SE_RE`
8. Prediction interval: `θ_RE ± t_(k-2, 0.975) × sqrt(SE_RE² + tau²)`

**Fixed-effect model (inverse-variance) — for comparison:**
- Same as above with tau² = 0

**For binary outcomes (Mantel-Haenszel) — alternative:**
- MH pooled OR/RR with Robins-Breslow-Greenland variance

**Forest plot (SVG):**
- Per-study: point estimate (square, size proportional to weight) + CI whiskers
- Pooled: diamond at bottom
- Vertical line at null (OR=1 or MD=0)
- Labels: study name, effect (95% CI), weight %
- Both fixed and random pooled shown

**Output:**
```json
{
  "outcome": "...",
  "model": "random_effects_DL",
  "pooled_effect": 0.75,
  "ci_lower": 0.65,
  "ci_upper": 0.87,
  "p_value": 0.0001,
  "prediction_interval": [0.50, 1.12],
  "per_study": [
    { "study": "...", "effect": 0.70, "ci": [0.55, 0.89], "weight_pct": 15.2 },
    ...
  ],
  "fixed_effect_comparison": { "pooled_effect": 0.74, "ci": [...] },
  "forest_plot_svg": "..."
}
```

### 5.3 Stage 3.3: Heterogeneity Assessment

**Process (deterministic Python):**

- **Cochran's Q:** `Q = Σ w_i × (θ_i - θ_pooled)²`, df = k-1, p-value from χ² distribution
- **I²:** `I² = max(0, (Q - df) / Q × 100%)`
  - Interpretation per Cochrane Handbook 10.10.2:
    - 0–40%: might not be important
    - 30–60%: moderate heterogeneity
    - 50–75%: substantial heterogeneity
    - 75–100%: considerable heterogeneity
- **Tau²:** between-study variance (from DL estimator)
- **H²:** `H² = Q / df`

**Output:** Heterogeneity metrics + interpretation string. If I² > 50%, flag for subgroup exploration.

### 5.4 Stage 3.4: Sensitivity Analyses

**Process (deterministic Python):**

1. **Leave-one-out analysis:** For each study, re-pool excluding that study. Report:
   - Pooled estimate and CI without study X
   - Whether direction/significance changes
   - Identify influential studies (those whose removal changes significance)

2. **Fixed vs random comparison:**
   - If pooled estimates diverge substantially, flag potential small-study effects
   - Report both estimates side by side

3. **High RoB exclusion:**
   - Re-pool excluding all studies with overall "high" risk of bias
   - Report: N studies remaining, new pooled estimate + CI
   - If result changes direction or loses significance, flag as sensitivity concern

**Output:** Sensitivity analysis table (JSON + formatted Markdown).

### 5.5 Stage 3.5: Publication Bias

**Process (deterministic Python):**

- **Funnel plot (SVG):** x-axis = effect size, y-axis = SE (inverted). Per-study point. Pseudo-95% CI lines around pooled estimate.
- **Egger's regression test** (if k ≥ 10 studies):
  - Regress standardized effect (effect/SE) on precision (1/SE)
  - Report intercept, SE, p-value
  - Significant intercept (p < 0.10) → evidence of funnel asymmetry
- **If k < 10:** skip Egger's test, note: "Fewer than 10 studies; formal test for funnel asymmetry not recommended (Cochrane Handbook 10.4.3.1)"

**Output:** Funnel plot SVG + Egger's test results (or skip note).

### 5.6 Stage 3.6: GRADE Summary of Findings

**Process (rule engine + LLM):**

Per outcome, rate certainty starting from High (RCTs):

| Domain | Method | Downgrade criteria |
|---|---|---|
| Risk of bias | Rule engine from RoB summary | Majority high → -1 serious; all high → -2 very serious |
| Inconsistency | Rule engine from I² | I² 50-75% → -1 serious; I² > 75% → -2 very serious |
| Indirectness | LLM assessment | Population/intervention/outcome mismatch to PICO → -1 or -2 |
| Imprecision | Rule engine | CI crosses null → -1; CI crosses null AND clinical threshold → -2; or optimal information size (OIS) not met → -1 |
| Publication bias | Rule engine from Egger's/funnel | Significant Egger's or visually asymmetric funnel → -1 |

- OIS (optimal information size): for binary outcomes, compute the total N needed to detect the pooled effect at α=0.05, power=0.80. If total N across studies < OIS → imprecision flag.

**Summary of Findings table format:**

| Outcome | Studies (N) | Effect (95% CI) | Certainty | Reason for downgrade |
|---|---|---|---|---|
| Mortality | 5 (12,450) | OR 0.75 (0.65–0.87) | ⊕⊕⊕⊕ High | — |
| Hospitalization | 4 (10,200) | OR 0.68 (0.50–0.93) | ⊕⊕⊕◯ Moderate | Imprecision (-1) |

**Output:** GRADE SoF table (JSON + Markdown) + per-domain justifications.

### 5.7 Stage 3.7: Report Assembly

**Process (deterministic assembly + LLM narrative):**

**Markdown report structure:**
1. **Title page:** Clinical question, date, authors
2. **Abstract:** structured (Background, Objectives, Search methods, Selection criteria, Main results, Conclusions)
3. **PRISMA flow diagram** (SVG from Stage 1.5)
4. **Search strategy** (verbatim approved query from Stage 1.2)
5. **Characteristics of included studies** (table from Stage 2.3)
6. **Risk of bias summary** (traffic light SVG from Stage 2.2)
7. **Results per outcome:**
   - Forest plot (SVG)
   - Pooled estimate with CI, p-value, prediction interval
   - Heterogeneity metrics
8. **Sensitivity analyses** (table from Stage 3.4)
9. **Publication bias** (funnel plot SVG + Egger's from Stage 3.5)
10. **GRADE Summary of Findings** (table from Stage 3.6)
11. **Narrative summary** (800–1200 words, LLM-generated, findings only — no clinical recommendations)
12. **Computation traces** (full audit trail for all deterministic stages)
13. **Disclaimer:** "This meta-analysis was generated by an AI agent skill. Results should be verified by qualified researchers before use in clinical decision-making."

**JSON export:** All structured data from every stage, enabling downstream consumption.

**File naming:** `meta_analysis_[topic_slug]_[date].md` + `meta_analysis_[topic_slug]_[date].json`

---

## 6 Deterministic Python Modules

### 6.1 `pipeline/effect_sizes.py`
- `compute_log_or(a, b, c, d)` → log(OR), SE
- `compute_log_rr(a, b, c, d)` → log(RR), SE
- `compute_rd(a, b, c, d)` → RD, SE
- `compute_md(mean_i, sd_i, n_i, mean_c, sd_c, n_c)` → MD, SE
- `compute_smd(mean_i, sd_i, n_i, mean_c, sd_c, n_c)` → Hedges' g, SE
- `zero_cell_correction(a, b, c, d, correction=0.5)` → corrected cells

### 6.2 `pipeline/pooling.py`
- `pool_random_effects_dl(effects, ses)` → pooled, CI, tau², Q, I², prediction interval
- `pool_fixed_effect_iv(effects, ses)` → pooled, CI
- `pool_mantel_haenszel(tables, measure="OR"|"RR")` → pooled, CI

### 6.3 `pipeline/heterogeneity.py`
- `cochrans_q(effects, ses, pooled)` → Q, df, p
- `i_squared(Q, df)` → I², interpretation
- `tau_squared_dl(Q, df, weights)` → tau²
- `prediction_interval(pooled, se_pooled, tau2, k)` → lower, upper

### 6.4 `pipeline/sensitivity.py`
- `leave_one_out(effects, ses)` → array of pooled results with each study removed
- `exclude_high_rob(effects, ses, rob_ratings)` → re-pooled result

### 6.5 `pipeline/publication_bias.py`
- `eggers_test(effects, ses)` → intercept, se, p_value
- `funnel_plot_data(effects, ses, pooled)` → plot coordinates

### 6.6 `pipeline/grade.py`
- `assess_risk_of_bias(rob_ratings)` → downgrade (0, -1, -2)
- `assess_inconsistency(i_squared)` → downgrade (0, -1, -2)
- `assess_imprecision(ci_lower, ci_upper, null_value, ois, total_n)` → downgrade (0, -1, -2)
- `assess_publication_bias(eggers_p, k)` → downgrade (0, -1)
- `compute_grade(start_certainty, downgrades)` → final certainty label

### 6.7 `pipeline/visualizations.py`
- `forest_plot_svg(studies, pooled, fixed_pooled)` → SVG string
- `funnel_plot_svg(effects, ses, pooled)` → SVG string
- `rob_traffic_light_svg(rob_data)` → SVG string
- `prisma_flow_svg(counts)` → SVG string

---

## 7 File Structure

```
meta_analyst/
├── .claude-plugin/
│   └── plugin.json                    ← Plugin manifest
├── skills/
│   └── meta-analyst/
│       ├── SKILL.md                   ← Skill entry point
│       ├── pipeline/
│       │   ├── __init__.py
│       │   ├── effect_sizes.py        ← Effect size computation
│       │   ├── pooling.py             ← DL random-effects + fixed-effect + MH
│       │   ├── heterogeneity.py       ← Q, I², tau², H²
│       │   ├── sensitivity.py         ← Leave-one-out, high-RoB exclusion
│       │   ├── publication_bias.py    ← Egger's test
│       │   ├── grade.py               ← GRADE certainty rule engine
│       │   ├── visualizations.py      ← Forest/funnel/PRISMA/traffic light SVGs
│       │   └── report.py              ← Report assembly (Markdown + JSON)
│       └── references/
│           ├── phase_1_identify.md    ← Stage specs for Phase 1
│           ├── phase_2_appraise.md    ← Stage specs for Phase 2
│           ├── phase_3_synthesize.md  ← Stage specs for Phase 3
│           └── formulas.md            ← All statistical formulas
├── tests/
│   ├── test_effect_sizes.py
│   ├── test_pooling.py
│   ├── test_heterogeneity.py
│   ├── test_sensitivity.py
│   ├── test_publication_bias.py
│   └── test_grade.py
├── paper/
│   ├── research_note.md               ← Claw4S submission
│   └── submission/
│       └── submit.sh
├── CLAUDE.md
└── README.md
```

---

## 8 Testing Strategy

### 8.1 Unit Tests (deterministic modules)

Each Python module gets a dedicated test file with known-input/known-output cases:

- **Effect sizes:** Verify against hand-computed examples and published Cochrane training data
- **Pooling:** Verify DL and IV pooled estimates against RevMan/metafor output for published meta-analyses
- **Heterogeneity:** Verify Q, I², tau² against known datasets
- **Sensitivity:** Verify leave-one-out produces correct re-pooled estimates
- **Publication bias:** Verify Egger's intercept against statsmodels OLS
- **GRADE:** Verify downgrade logic for boundary conditions

### 8.2 Integration Tests

- Run full Phase 3 on a known meta-analysis dataset (e.g., a published Cochrane review with available 2×2 tables) and verify all pooled estimates, CIs, and heterogeneity metrics match published values within rounding tolerance.

### 8.3 Acceptance Tests

| Test | Scenario | Expected |
|---|---|---|
| T1 | 5 RCTs, binary outcome, low heterogeneity | Pooled OR with tight CI, I² < 30%, GRADE High |
| T2 | 8 RCTs, continuous outcome, high heterogeneity | SMD with wide prediction interval, I² > 75%, GRADE downgraded |
| T3 | 3 RCTs, one with zero events in treatment arm | Continuity correction applied, no crash |
| T4 | 12 RCTs, significant Egger's test | Publication bias flagged, GRADE downgraded |
| T5 | 6 RCTs, 2 high RoB | Sensitivity analysis shows impact of excluding high-RoB studies |
| T6 | Single study only | No pooling performed, report notes single-study limitation |
| T7 | All studies high RoB | GRADE downgraded -2 for risk of bias |

---

## 9 Dependencies

- **Python:** scipy, statsmodels, numpy (same as Evidence Evaluator)
- **APIs:** PubMed E-utilities (free, < 3 req/sec without key), Cochrane CENTRAL API (free), ClinicalTrials.gov API v2 (free)
- **Optional:** Evidence Evaluator skill (`npx skills add SciSpark-ai/evidence_evaluator`)

---

## 10 Conference Evaluation Alignment

| Criterion (weight) | How Meta-Analyst addresses it |
|---|---|
| Executability (25%) | Deterministic Python core; typed stage specs; setup verification command |
| Reproducibility (25%) | Logged search strategy; 3× extraction vote; computation traces; JSON export |
| Scientific Rigor (20%) | Follows Cochrane Handbook methodology; GRADE framework; standard statistical methods |
| Generalizability (15%) | Any RCT pairwise comparison; binary + continuous outcomes; modular pipeline |
| Agent Clarity (15%) | Three-phase structure; typed I/O contracts; reference docs per phase; composable with EE |

---

## 11 Open Questions

1. ~~**Search scope:** PubMed only for v1.~~ **Resolved:** PubMed + Cochrane CENTRAL + ClinicalTrials.gov. All free APIs. Covers Cochrane Handbook minimum recommendation.
2. **Full-text access:** Many papers will be behind paywalls. Strategy: extract from abstract + metadata first; flag when full-text extraction is needed; user provides access.
3. **Subgroup analysis:** Not included in v1. Would require user-defined subgroup variables. Consider for v2.
4. **Network meta-analysis:** Out of scope for v1. Different statistical framework (frequentist NMA or Bayesian).
5. **Forest plot rendering:** SVG generated by Python string construction (like Evidence Evaluator). Consider matplotlib backend if SVG gets too complex.
