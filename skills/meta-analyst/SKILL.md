---
name: meta-analyst
description: >
  End-to-end clinical meta-analysis of RCT intervention studies following Cochrane
  Handbook methodology. Three-phase pipeline: (1) PICO-driven search across PubMed,
  CENTRAL, and ClinicalTrials.gov with screening, (2) data extraction with RoB 2.0
  assessment via Evidence Evaluator composition, (3) deterministic statistical pooling
  (DerSimonian-Laird), heterogeneity, sensitivity analyses, publication bias, and
  GRADE certainty ratings. Outputs Cochrane-style Markdown report + structured JSON.
  USE THIS SKILL when the user asks to perform a meta-analysis; wants to pool clinical
  trial results; asks about forest plots or funnel plots; wants GRADE evidence certainty;
  asks to combine RCTs; requests a systematic review; or asks "what does the evidence say?"
---

# Meta-Analyst Skill

An end-to-end clinical meta-analysis pipeline following **Cochrane Handbook** methodology. Three phases: literature identification (PICO search + screening), critical appraisal (extraction + RoB 2.0), and deterministic statistical synthesis (DL pooling + GRADE). Outputs a Cochrane-style Markdown report and structured JSON.

---

## Setup

Install Python dependencies before running any pipeline phase:

```bash
pip install scipy statsmodels numpy
```

Verify all pipeline modules load correctly (run from the skill directory):

```bash
cd ${CLAUDE_SKILL_DIR} && python3 -c "from pipeline.effect_sizes import compute_log_or; from pipeline.pooling import pool_random_effects_dl; from pipeline.grade import compute_grade; from pipeline.report import assemble_report; print('OK')"
```

**Important:** All Python commands must be run from the `skills/meta-analyst/` directory so that `from pipeline.X import ...` resolves correctly. Always prefix Python calls with `cd ${CLAUDE_SKILL_DIR} &&`.

---

## Quick Start

1. **Receive question** — free-text clinical question from the user (e.g., "Do SGLT2 inhibitors reduce mortality in HFrEF?")
2. **Run Phase 1** — formalise PICO, build and approve search strategy, execute searches, screen abstracts, generate PRISMA flow
3. **Run Phase 2** — extract data, assess RoB 2.0, assemble characteristics table
4. **Run Phase 3** — compute effect sizes, pool (DL random-effects), assess heterogeneity, run sensitivity analyses, test publication bias, rate GRADE, assemble report
5. **Export report** — save as `meta_analysis_[question_slug].md` and `meta_analysis_[question_slug].json`
6. **Reply with brief summary** — pooled estimate + GRADE certainty + path to exported files

Read the phase reference documents before executing each phase. The agent reads them to resolve any ambiguity.

---

## Pipeline Architecture

```
User question (free-text clinical question)
  │
  ▼
PHASE 1 — IDENTIFY
  Stage 1.1  PICO Formalization          [LLM: extract P, I, C, O with MeSH + synonyms]
  Stage 1.2  Search Strategy             [LLM: Cochrane MECIR + RCT filter → human ✓]
  Stage 1.3  Search Execution            [API: PubMed E-utilities, CENTRAL, CTG v2 → dedup]
  Stage 1.4  Abstract Screening          [LLM: include/exclude/uncertain → human ✓]
  Stage 1.5  PRISMA Flow                 [Python: prisma_flow_svg()]
  │
  ▼
PHASE 2 — APPRAISE
  Stage 2.1  Data Extraction             [LLM: 3× majority-vote extraction from full text]
  Stage 2.2  Risk of Bias Assessment     [Evidence Evaluator + fallback RoB 2.0 checklist]
  Stage 2.3  Characteristics Table       [Python: format_characteristics_table()]
                                         [→ human ✓ before synthesis]
  │
  ▼
PHASE 3 — SYNTHESIZE
  Stage 3.1  Effect Size Computation     [Python: effect_sizes.py]
  Stage 3.2  Meta-Analytic Pooling       [Python: pooling.py — DL default, FE comparison]
  Stage 3.3  Heterogeneity              [Python: heterogeneity.py — Q, I², tau², PI]
  Stage 3.4  Sensitivity Analyses        [Python: sensitivity.py — LOO, high-RoB, FvR]
  Stage 3.5  Publication Bias            [Python: publication_bias.py — Egger's (k≥10)]
  Stage 3.6  GRADE Certainty             [Python + LLM: 5 domains]
  Stage 3.7  Report Assembly             [Python: report.py — Markdown + JSON]
  │
  ▼
Output: meta_analysis_[slug].md + meta_analysis_[slug].json
```

---

## Phase 1 — Identify

**Reference document:** `references/phase_1_identify.md`

Read this document before starting Phase 1. It defines the exact I/O contracts, API endpoints, deduplication rules, inclusion/exclusion criteria, and human checkpoint scripts.

### Stage 1.1 — PICO Formalization

Extract Population, Intervention, Comparator, and Outcome from the user's question. Assign MeSH terms and synonyms to each element. Construct the `pico_search_string` (OR within concepts, AND across P/I/C).

Output: PICO JSON with `pico_search_string`.

### Stage 1.2 — Search Strategy Construction

Build Boolean queries for PubMed, Cochrane CENTRAL, and ClinicalTrials.gov following Cochrane MECIR standards. Append the Cochrane Highly Sensitive Search Strategy RCT filter to the PubMed query.

**Human Checkpoint #1:** Present the proposed queries to the user. Do not execute searches until the user approves or edits.

### Stage 1.3 — Search Execution

Execute the approved queries:
- **PubMed:** `esearch.fcgi` → `efetch.fcgi` (E-utilities)
- **Cochrane CENTRAL:** REST API or web interface
- **ClinicalTrials.gov:** `https://clinicaltrials.gov/api/v2/studies` (paginate via `nextPageToken`)

Deduplicate by PMID, DOI, then title fuzzy match (≥0.90 normalised similarity). Log per-database hit counts.

### Stage 1.4 — Abstract Screening

Classify each deduplicated record as include / exclude / uncertain against the PICO inclusion criteria (RCT design, population match, intervention match, comparator match, outcome reported).

**Human Checkpoint #2:** Present the shortlist of included + uncertain papers. Do not proceed to Phase 2 until approved.

### Stage 1.5 — PRISMA Flow

```python
from pipeline.visualizations import prisma_flow_svg

svg = prisma_flow_svg({
    "db_pubmed": n, "db_central": n, "db_ctgov": n,
    "identified": n, "duplicates_removed": n, "screened": n,
    "excluded_screening": n, "eligible": n,
    "excluded_eligibility": n, "included": n,
})
```

---

## Phase 2 — Appraise

**Reference document:** `references/phase_2_appraise.md`

Read this document before starting Phase 2.

### Stage 2.1 — Data Extraction

Run 3× independent extraction passes per study. Apply majority vote on numeric fields. Flag `low_confidence_fields` when all three passes disagree. Extract the full standardised form (study ID, design, population, N per arm, events per arm for binary outcomes, mean/SD/N for continuous outcomes, follow-up duration, blinding, allocation concealment).

### Stage 2.2 — Risk of Bias Assessment

**Primary approach:** Invoke the Evidence Evaluator skill for each included study.

```bash
npx skills add SciSpark-ai/evidence_evaluator
```

Extract per-domain RoB 2.0 judgments (D1: Randomisation, D2: Deviations, D3: Missing data, D4: Measurement, D5: Reporting) and the overall judgment.

**Fallback:** If Evidence Evaluator is unavailable, apply the streamlined 5-domain RoB 2.0 checklist defined in `references/phase_2_appraise.md`.

Generate the traffic light SVG:

```python
from pipeline.visualizations import rob_traffic_light_svg

svg = rob_traffic_light_svg([
    {"study": "McMurray 2019", "domains": [
        {"domain": "D1: Randomisation", "judgment": "low"},
        {"domain": "D2: Deviations",    "judgment": "low"},
        {"domain": "D3: Missing data",  "judgment": "low"},
        {"domain": "D4: Measurement",   "judgment": "low"},
        {"domain": "D5: Reporting",     "judgment": "some concerns"},
    ]}
])
```

### Stage 2.3 — Characteristics Table

```python
from pipeline.report import format_characteristics_table

table_md = format_characteristics_table(table_studies)
# table_studies: list of dicts with keys:
# first_author, year, n_intervention, n_control,
# intervention_description, comparator_description,
# followup_duration, rob_overall
```

**Human Checkpoint #3:** Present the extracted data and RoB summary for review. Do not begin Phase 3 until approved.

---

## Phase 3 — Synthesize

**Reference document:** `references/phase_3_synthesize.md`

Read this document before starting Phase 3. It contains complete code invocation examples for every stage.

### Stage 3.1 — Effect Size Computation

```python
from pipeline.effect_sizes import compute_log_or, compute_md, compute_smd, zero_cell_correction
```

Apply `zero_cell_correction` before any log-transform. Choose the effect size type based on outcome type (binary → log OR or log RR; continuous same scale → MD; continuous different scales → SMD/Hedges' g).

### Stage 3.2 — Meta-Analytic Pooling

```python
from pipeline.pooling import pool_random_effects_dl, pool_fixed_effect_iv, pool_mantel_haenszel
```

**Default:** DerSimonian-Laird random-effects. Run fixed-effect IV as sensitivity comparison. Use Mantel-Haenszel as a cross-check for sparse binary data. Back-transform log OR/RR to original scale before reporting.

### Stage 3.3 — Heterogeneity

```python
from pipeline.heterogeneity import cochrans_q, i_squared, tau_squared_dl, prediction_interval
```

Report Q (with p-value), I² (with Cochrane Handbook interpretation), tau², and the prediction interval (when k ≥ 3). I² interpretation thresholds: <40% low, 40–60% moderate, 60–75% substantial, ≥75% considerable.

### Stage 3.4 — Sensitivity Analyses

```python
from pipeline.sensitivity import leave_one_out, exclude_high_rob, fixed_vs_random_comparison
```

Run all three analyses for each pooled outcome. Flag any study whose leave-one-out exclusion changes direction or significance.

### Stage 3.5 — Publication Bias

```python
from pipeline.publication_bias import eggers_test, funnel_plot_data
```

**k < 10 guard:** If fewer than 10 studies, skip Egger's test entirely and note: "Formal test for funnel asymmetry not conducted (k < 10; Cochrane Handbook 10.4.3.1)."

If k ≥ 10 and Egger's p < 0.10, report suspected publication bias and apply GRADE downgrade of −1.

### Stage 3.6 — GRADE Certainty

```python
from pipeline.grade import (
    assess_risk_of_bias, assess_inconsistency, assess_imprecision,
    assess_publication_bias, compute_grade, grade_summary_row
)
```

Assess all 5 GRADE domains for each outcome:

| Domain | Method | Function |
|---|---|---|
| Risk of bias | Deterministic: proportion of high-RoB studies | `assess_risk_of_bias(rob_ratings)` |
| Inconsistency | Deterministic: I² thresholds | `assess_inconsistency(i_squared)` |
| Indirectness | LLM reasoning: PICO match assessment | Agent judgment → integer 0/−1/−2 |
| Imprecision | Deterministic: CI crosses null + OIS | `assess_imprecision(ci_lower, ci_upper, null_value, ois, total_n)` |
| Publication bias | Deterministic: Egger's p (k≥10 only) | `assess_publication_bias(eggers_p, k)` |

Start at **High** certainty for RCTs. Apply all downgrades:

```python
certainty = compute_grade("High", {
    "rob": rob_downgrade,
    "inconsistency": inconsistency_downgrade,
    "indirectness": indirectness_downgrade,   # agent-assigned
    "imprecision": imprecision_downgrade,
    "publication_bias": pub_bias_downgrade,
})
```

### Stage 3.7 — Report Assembly

```python
from pipeline.report import assemble_report, format_characteristics_table, format_grade_sof_table
```

```python
report = assemble_report(
    pico=pico_json,
    search={"query": query, "date_range": date_range, "databases": [...]},
    prisma_counts=prisma_counts,
    characteristics_table=format_characteristics_table(table_studies),
    rob_summary="Narrative RoB summary.",
    outcomes=[...],          # list of outcome dicts with pooling, heterogeneity, grade
    sensitivity={...},       # dict keyed by outcome name
    publication_bias={...},  # dict keyed by outcome name
    prisma_svg=None,         # auto-generated if None
    rob_svg=rob_svg,
)
```

The function returns `{"markdown": str, "json": dict}`. Write both to disk:

```python
import json
with open("meta_analysis_output.md", "w") as f:
    f.write(report["markdown"])
with open("meta_analysis_output.json", "w") as f:
    json.dump(report["json"], f, indent=2)
```

---

## Human Checkpoints

Three checkpoints require explicit user approval before continuing:

| Checkpoint | Phase/Stage | What the user reviews | What to do next |
|---|---|---|---|
| #1 — Query Review | Phase 1, Stage 1.2 | Proposed search queries for all three databases | Execute searches only after approval |
| #2 — Shortlist Review | Phase 1, Stage 1.4 | Included + uncertain papers from abstract screening | Begin Phase 2 data extraction only after approval |
| #3 — Extraction + RoB Review | Phase 2, Stage 2.3 | Extraction data, RoB judgments, flagged low-confidence fields | Begin Phase 3 synthesis only after approval |

**Never skip a checkpoint.** If the user is not available, pause and state which checkpoint is pending.

---

## Output Format

### Markdown Report Structure

The assembled report (`report["markdown"]`) contains these sections in order:

1. Title and metadata (question, date, databases)
2. PRISMA Flow Diagram (embedded SVG)
3. Search Strategy (query text, date range)
4. Characteristics of Included Studies (Markdown table)
5. Risk of Bias Summary (traffic light SVG + narrative)
6. Results (per-outcome subsections):
   - Forest plot SVG
   - Pooled estimate + 95% CI + p-value
   - Heterogeneity: I², Q, tau², prediction interval
7. Sensitivity Analyses (leave-one-out, fixed vs random, high-RoB exclusion)
8. Publication Bias (funnel plot SVG + Egger's result or skip note)
9. GRADE Summary of Findings (Markdown table with certainty symbols)
10. Narrative Summary (agent-generated)
11. Disclaimer

### JSON Export Structure

```json
{
  "pico":             { "population": "...", "intervention": "...", "comparator": "...", "outcome": "..." },
  "search":           { "query": "...", "date_range": "...", "databases": [...] },
  "prisma":           { "identified": N, "included": N, ... },
  "studies":          [ { ... } ],
  "outcomes": [
    {
      "name":          "...",
      "pooling":       { "pooled": ..., "ci_lower": ..., "ci_upper": ..., "p_value": ... },
      "heterogeneity": { "i2": ..., "q": ..., "tau_sq": ..., "prediction_lower": ..., "prediction_upper": ... },
      "sensitivity":   { ... },
      "grade":         { "certainty": "High|Moderate|Low|Very Low", "certainty_symbols": "⊕⊕⊕⊕", "downgrade_reasons": [...] }
    }
  ],
  "grade_summary":    [ { "outcome": "...", "certainty": "...", "symbols": "..." } ],
  "publication_bias": { ... }
}
```

**Disclaimer (always include):** The Markdown report footer contains: "This meta-analysis was generated by an AI agent skill. Results should be verified by qualified researchers before use in clinical decision-making."

---

## Composition with Evidence Evaluator

The meta-analyst composes with the Evidence Evaluator skill for per-study RoB 2.0 assessment (Stage 2.2).

**Install:**

```bash
npx skills add SciSpark-ai/evidence_evaluator
```

**Usage:** For each included study, invoke Evidence Evaluator with the full text or abstract + methods. Request Stage 4 (bias risk) output specifically to extract the 5 RoB 2.0 domain judgments and the overall judgment.

**Fallback behavior:** If Evidence Evaluator is not installed, or returns no output for a study, apply the streamlined 5-domain RoB 2.0 checklist defined in `references/phase_2_appraise.md`. Document which studies were assessed via Evidence Evaluator vs the fallback checklist.

---

## Reference Documents

Read the appropriate reference document before executing each phase or when resolving any ambiguity:

| Document | When to read |
|---|---|
| `references/formulas.md` | Before Stage 3.1 — all statistical formulas with notation and Python function cross-references |
| `references/phase_1_identify.md` | Before Phase 1 — PICO, search strategy, execution, screening, PRISMA |
| `references/phase_2_appraise.md` | Before Phase 2 — extraction form, RoB checklist, characteristics table |
| `references/phase_3_synthesize.md` | Before Phase 3 — pooling, heterogeneity, sensitivity, GRADE, report assembly with full code examples |

---

## Key Design Principles

- **Cochrane Handbook methodology throughout.** DL random-effects is the default; fixed-effect is always run as a sensitivity comparison, not a primary result.
- **All statistical computation is deterministic Python.** LLM handles screening, extraction, GRADE indirectness, and narrative. Python handles all numbers.
- **Three human checkpoints prevent irreversible errors.** Searching, extraction, and synthesis each require user sign-off before proceeding.
- **Prediction intervals are mandatory when k ≥ 3.** A significant pooled estimate with a prediction interval crossing the null signals important real-world heterogeneity.
- **k < 10 guard on Egger's test.** Never report or act on Egger's results with fewer than 10 studies.
- **GRADE indirectness requires documented reasoning.** Agent must explain why the PICO elements of each study match or diverge from the research question.
- **Report is the primary deliverable.** The Markdown file is comprehensive and auditable. The chat response is a brief summary pointing to it.
