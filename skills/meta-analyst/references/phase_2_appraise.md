# Phase 2 — Appraise

Phase 2 covers critical appraisal of included studies: structured data extraction, risk-of-bias assessment using RoB 2.0, and assembly of the characteristics table. All work is agent-driven. Read this document before executing any Phase 2 stage.

---

## Stage 2.1 — Data Extraction

**Purpose:** Extract all quantitative and qualitative data needed for pooling and the characteristics table from each included study.

### Extraction Protocol

Run **3× independent extraction passes** for each study using the standardised form below. On numeric fields, apply majority vote: if 2 of 3 extractions agree, accept that value. If all three differ, flag the field as `low_confidence` and record all three values for human review.

This simulates double-extraction with conflict resolution. Document which fields were flagged.

### Standardised Extraction Form

Extract the following fields for every included study:

**Study identification:**
- `study_id` — first author + year (e.g., "McMurray 2019")
- `full_citation` — full reference string
- `pmid` — PubMed ID
- `doi` — DOI
- `nct_id` — ClinicalTrials.gov identifier (if available)
- `registration_number` — any trial registry number

**Design:**
- `study_design` — RCT / cluster-RCT / crossover-RCT
- `blinding` — double-blind / single-blind / open-label
- `allocation_concealment` — adequate / unclear / inadequate
- `n_randomised_total` — total randomised
- `n_intervention` — randomised to intervention arm
- `n_control` — randomised to comparator arm
- `n_analysed_intervention` — analysed in intervention arm (ITT or per-protocol — note which)
- `n_analysed_control` — analysed in comparator arm
- `analysis_method` — ITT / modified ITT / per-protocol
- `multicenter` — yes / no
- `n_sites` — number of sites (if reported)
- `country` — country or countries

**Population:**
- `population_description` — free text description of enrolled patients
- `mean_age` — mean or median age
- `pct_female` — percentage female
- `key_inclusion_criteria` — summary
- `key_exclusion_criteria` — summary
- `baseline_characteristic_1` — (e.g., mean LVEF %)
- `baseline_characteristic_2` — (e.g., median NT-proBNP)

**Intervention and comparator:**
- `intervention_description` — drug/dose/duration
- `comparator_description` — placebo/active comparator description
- `followup_duration` — median or mean follow-up in months
- `adherence_reported` — yes / no; adherence rate if reported

**Binary outcomes** (for each reported outcome):
- `outcome_name` — standardised outcome label
- `outcome_type` — binary / continuous / time-to-event
- `events_intervention` — event count in intervention arm
- `n_intervention_outcome` — total in intervention arm for this outcome
- `events_control` — event count in comparator arm
- `n_control_outcome` — total in comparator arm for this outcome
- `reported_effect` — OR / RR / HR as reported in paper
- `reported_ci_lower` — lower bound of 95% CI as reported
- `reported_ci_upper` — upper bound of 95% CI as reported
- `reported_p_value` — p-value as reported

**Continuous outcomes** (for each reported outcome):
- `outcome_name` — standardised outcome label
- `mean_intervention` — mean (or median) in intervention arm
- `sd_intervention` — SD (or IQR — note which)
- `n_intervention_outcome` — n in intervention arm
- `mean_control` — mean in comparator arm
- `sd_control` — SD in comparator arm
- `n_control_outcome` — n in comparator arm
- `reported_md` — mean difference as reported (if available)
- `reported_ci_lower` / `reported_ci_upper` — CI as reported
- `scale_name` — name of measurement scale (for SMD pooling)
- `scale_direction` — higher = better / higher = worse

**Low-confidence flags:**
- `low_confidence_fields` — list of field names where the 3 extraction passes disagreed

### Output Format

Return extracted data as a list of study dicts. Example:

```python
studies = [
    {
        "study_id": "McMurray 2019",
        "pmid": "31535829",
        "n_randomised_total": 4744,
        "n_intervention": 2373,
        "n_control": 2371,
        "blinding": "double-blind",
        "followup_duration": 18.2,
        "outcomes": [
            {
                "outcome_name": "CV death or worsening HF",
                "outcome_type": "binary",
                "events_intervention": 386,
                "n_intervention_outcome": 2373,
                "events_control": 502,
                "n_control_outcome": 2371,
                "reported_effect": 0.74,
                "reported_ci_lower": 0.65,
                "reported_ci_upper": 0.85,
            }
        ],
        "low_confidence_fields": [],
    }
]
```

---

## Stage 2.2 — Risk of Bias Assessment

**Purpose:** Assess the risk of bias for each included study using the Cochrane RoB 2.0 tool.

### Primary Approach: Evidence Evaluator Composition

For each included study, invoke the Evidence Evaluator skill to perform a full RoB 2.0 assessment. This provides the most comprehensive domain-level evaluation.

**Install Evidence Evaluator (if not already installed):**

```bash
npx skills add SciSpark-ai/evidence_evaluator
```

**Invocation:** For each study, pass the full text (or the extracted abstract + methods + results) to the Evidence Evaluator skill and request Stage 2 (RoB 2.0) output. Extract the domain judgments:

```python
# Expected structure from Evidence Evaluator:
rob_data = {
    "study_id": "McMurray 2019",
    "domains": {
        "randomisation_process":        "low",       # D1
        "deviations_from_interventions": "low",      # D2
        "missing_outcome_data":         "low",       # D3
        "measurement_of_outcomes":      "low",       # D4
        "selection_of_reported_result": "some concerns",  # D5
    },
    "overall": "some concerns",
}
```

### Fallback: Streamlined RoB 2.0 Checklist

If Evidence Evaluator is unavailable or produces no output for a study, apply the following 5-domain streamlined checklist directly:

**Domain 1 — Randomisation process**
- Was the allocation sequence truly random? (computer-generated, random number table, etc.)
- Was allocation adequately concealed? (central randomisation, sealed envelopes, etc.)
- Were baseline characteristics balanced between arms?
- **Low risk:** All three satisfied. **Some concerns:** Insufficient reporting. **High risk:** Non-random sequence or no concealment.

**Domain 2 — Deviations from intended interventions**
- Were participants and caregivers blinded to assignment?
- Were there protocol deviations that could bias the effect estimate?
- Was analysis conducted as ITT?
- **Low risk:** Double-blind, no important deviations, ITT analysis. **Some concerns:** Single-blind or minor deviations. **High risk:** Open-label with evidence of differential care, or substantial deviations not accounted for.

**Domain 3 — Missing outcome data**
- Was the proportion of missing data low (<10%) and similar between arms?
- Was the reason for missingness unrelated to the true outcome?
- Were missing data handled appropriately (e.g., multiple imputation, sensitivity analysis)?
- **Low risk:** <5% missing, balanced, appropriate handling. **Some concerns:** Moderate missingness or imbalanced drop-out. **High risk:** >20% missing or imbalanced attrition likely related to outcome.

**Domain 4 — Measurement of the outcome**
- Was the outcome assessor blinded to intervention assignment?
- Was the outcome measured consistently across arms?
- Were outcomes defined prospectively and objectively?
- **Low risk:** Blinded adjudication or objective outcome (mortality, hospitalisation). **Some concerns:** Self-reported but blinded. **High risk:** Non-blinded assessment of a subjective outcome.

**Domain 5 — Selection of the reported result**
- Were outcomes and analyses pre-specified in a protocol or trial registration?
- Was the primary endpoint consistent between protocol and publication?
- Were there signs of outcome switching or selective reporting?
- **Low risk:** Pre-registered, all outcomes reported. **Some concerns:** Protocol not available, minor discrepancies. **High risk:** Evidence of outcome switching or undisclosed analyses.

**Overall RoB judgment:**
- **Low:** All domains rated "low"
- **Some concerns:** At least one domain "some concerns," none "high"
- **High:** At least one domain rated "high"

### Traffic Light Visualisation

After completing all per-study RoB assessments, generate the traffic light SVG:

```python
from pipeline.visualizations import rob_traffic_light_svg

rob_input = [
    {
        "study": "McMurray 2019",
        "domains": [
            {"domain": "D1: Randomisation",   "judgment": "low"},
            {"domain": "D2: Deviations",       "judgment": "low"},
            {"domain": "D3: Missing data",     "judgment": "low"},
            {"domain": "D4: Measurement",      "judgment": "low"},
            {"domain": "D5: Reporting",        "judgment": "some concerns"},
        ]
    },
    # ... additional studies
]

svg = rob_traffic_light_svg(rob_input)
```

---

## Stage 2.3 — Characteristics Table Assembly

**Purpose:** Assemble the "Characteristics of Included Studies" table from the extraction data and RoB judgments.

**This stage is deterministic.** Invoke the Python function directly:

```python
from pipeline.report import format_characteristics_table

# Build study dicts for the table:
table_studies = [
    {
        "first_author":               "McMurray",
        "year":                       2019,
        "n_intervention":             2373,
        "n_control":                  2371,
        "intervention_description":   "Dapagliflozin 10 mg/day",
        "comparator_description":     "Placebo",
        "followup_duration":          "18.2 months",
        "rob_overall":                "some concerns",
    },
    # ... additional studies
]

table_md = format_characteristics_table(table_studies)
```

The function returns a Markdown table string. Include this in the Phase 2 summary and pass it to `assemble_report()` in Stage 3.7.

---

## Human Checkpoint #3 — Extraction + RoB Review

**Present to the user before beginning synthesis:**

```
HUMAN CHECKPOINT 3: Data Extraction & Risk of Bias Review

Included studies: {n}
Studies with low-confidence extractions: {list study IDs where low_confidence_fields is non-empty}

Risk of Bias summary:
  Low overall RoB:           {n} studies
  Some concerns overall:     {n} studies
  High overall RoB:          {n} studies

[Embed RoB traffic light SVG here]

Please review:
  (a) Approve extraction and RoB data → "approve" to proceed to Phase 3
  (b) Correct specific extraction fields → specify study ID + field + corrected value
  (c) Override a RoB judgment → specify study ID + domain + new judgment + reason
  (d) Exclude a study based on full-text review → specify study ID + reason

Studies with extraction flags (review recommended):
[list of study IDs + flagged fields]
```

**Do not begin Phase 3 synthesis until the user approves the extraction and RoB data.**

---

## Phase 2 Outputs

After completing all Stage 2.x steps, produce:

1. **Extracted studies list** — list of study dicts with all numeric fields and outcome data
2. **RoB data list** — per-study, per-domain RoB judgments and overall ratings
3. **Characteristics table** — Markdown string from `format_characteristics_table()`
4. **RoB traffic light SVG** — SVG string from `rob_traffic_light_svg()`
5. **Low-confidence log** — list of (study_id, field, values from 3 passes) for any flagged fields

Pass all five outputs forward to Phase 3.
