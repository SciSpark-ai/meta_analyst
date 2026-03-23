# Phase 1 — Identify

Phase 1 covers literature identification: PICO formalization, search strategy construction, search execution across three databases, abstract screening, and PRISMA flow generation. This phase is entirely agent-driven (no Python computation). Read this document before executing any Phase 1 stage.

---

## Stage 1.1 — PICO Formalization

**Purpose:** Convert a free-text clinical question into a structured PICO JSON with MeSH terms and a search string.

**Input:** Free-text clinical question from the user (e.g., "Does SGLT2 inhibition reduce mortality in heart failure with reduced ejection fraction?").

**Process:**

1. Identify and extract each PICO element:
   - **P (Population/Patients):** Who are the participants? Include disease, severity, age group, setting.
   - **I (Intervention):** What is the intervention or exposure?
   - **C (Comparator):** What is it compared to? (placebo, standard of care, active comparator)
   - **O (Outcome):** What outcomes are measured? Prioritise patient-important outcomes. List primary and secondary.

2. For each PICO element, identify:
   - Preferred MeSH term(s) from the NLM MeSH vocabulary
   - Common synonyms and brand names (for OR expansion in search)
   - Abbreviations

3. Construct `pico_search_string`: combine all synonyms within each concept using OR, then join concepts with AND. Wrap each concept group in parentheses.

**Output — structured PICO JSON:**

```json
{
  "population": "Adults with heart failure with reduced ejection fraction (HFrEF)",
  "population_mesh": ["Heart Failure"],
  "population_synonyms": ["HFrEF", "heart failure reduced ejection", "systolic heart failure", "congestive heart failure"],
  "intervention": "SGLT2 inhibitors",
  "intervention_mesh": ["Sodium-Glucose Transporter 2 Inhibitors"],
  "intervention_synonyms": ["SGLT2i", "dapagliflozin", "empagliflozin", "canagliflozin", "sotagliflozin"],
  "comparator": "Placebo or standard care",
  "comparator_mesh": ["Placebos"],
  "comparator_synonyms": ["placebo", "standard of care", "usual care"],
  "outcome": "All-cause mortality, cardiovascular mortality, HF hospitalisation",
  "outcome_mesh": ["Mortality", "Hospitalization", "Cardiovascular Diseases"],
  "outcome_synonyms": ["death", "all-cause death", "CV death", "heart failure admission", "worsening heart failure"],
  "study_design": "RCT",
  "pico_search_string": "(HFrEF OR \"heart failure with reduced ejection\" OR \"systolic heart failure\" OR \"congestive heart failure\") AND (SGLT2 OR \"sodium-glucose transporter 2\" OR dapagliflozin OR empagliflozin OR canagliflozin) AND (placebo OR \"standard care\" OR \"usual care\") AND (mortality OR death OR hospitalisation OR hospitalization)"
}
```

**Validation:** Before proceeding, confirm the PICO JSON covers the full question. If the user's question is ambiguous (e.g., no explicit comparator), infer the most clinically appropriate comparator (typically placebo) and document the assumption.

---

## Stage 1.2 — Search Strategy Construction

**Purpose:** Build a reproducible, Cochrane-standard Boolean query for each target database.

**Standards:** Follow Cochrane MECIR (Methodological Expectations of Cochrane Intervention Reviews) standard M11: "Search all relevant databases using a comprehensive search strategy."

### Boolean Query Structure

- Use **OR** within each PICO concept group (to capture synonyms and MeSH variants)
- Use **AND** across P, I, and C concept groups
- Do **not** AND on outcomes — outcome filtering occurs at screening, not search, to preserve sensitivity
- Place each concept group in parentheses

**Example base query structure:**

```
(P_terms OR P_mesh OR P_synonyms)
AND
(I_terms OR I_mesh OR I_synonyms)
AND
(C_terms OR C_mesh OR C_synonyms)
AND
(RCT_filter)
```

### Cochrane Highly Sensitive Search Strategy — RCT Filter (PubMed version)

Append the following RCT sensitivity filter to limit to randomised controlled trials:

```
AND (randomized controlled trial[pt] OR controlled clinical trial[pt]
     OR randomized[tiab] OR randomised[tiab] OR placebo[tiab]
     OR drug therapy[sh] OR randomly[tiab] OR trial[tiab]
     OR groups[tiab])
NOT (animals[mh] NOT humans[mh])
```

Source: Cochrane Handbook Section 4.4.2, "Sensitivity- and precision-maximising version (2008 revision)."

### Syntax Adaptation per Database

| Database | Syntax notes |
|---|---|
| PubMed | Use `[MeSH Terms]` for controlled vocabulary, `[tiab]` for title/abstract, `[pt]` for publication type. Boolean operators in ALL CAPS. |
| Cochrane CENTRAL | Use `MeSH descriptor:` for controlled vocabulary, `:ti,ab` for title/abstract. CENTRAL indexes only controlled trials — omit the RCT filter. |
| ClinicalTrials.gov | Use keyword search via API `query.term` parameter. No Boolean nesting; separate concepts with comma-separated terms or `+`. Filter by `filter.overallStatus=COMPLETED` and `filter.studyType=INTERVENTIONAL`. |

### Human Checkpoint #1 — Query Review

**Before executing searches, present the following to the user:**

```
HUMAN CHECKPOINT 1: Search Strategy Review

Proposed PubMed query:
[paste full query]

Proposed Cochrane CENTRAL query:
[paste full query]

Proposed ClinicalTrials.gov query:
[paste parameters]

Please review the search strategy. You may:
  (a) Approve as written → type "approve"
  (b) Edit specific terms → provide corrections
  (c) Add/remove synonyms or MeSH terms → specify changes

Proceeding will execute live database searches.
```

**Do not execute searches until the user approves or edits.**

---

## Stage 1.3 — Search Execution

**Purpose:** Execute the approved queries against three databases and deduplicate results.

### PubMed via E-utilities

**Step 1: ESearch — get PMIDs**

```
GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi
  ?db=pubmed
  &term={URL-encoded query}
  &retmax=10000
  &usehistory=y
  &retmode=json
```

Capture `WebEnv` and `query_key` from the response for EFetch.

**Step 2: EFetch — retrieve records**

```
GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi
  ?db=pubmed
  &query_key={query_key}
  &WebEnv={WebEnv}
  &rettype=abstract
  &retmode=xml
  &retmax=10000
```

Parse each `<PubmedArticle>` to extract:
- PMID
- Title (`<ArticleTitle>`)
- Abstract (`<AbstractText>`)
- Authors (`<Author>` list, first author)
- Year (`<PubDate>/<Year>`)
- Journal (`<Journal>/<Title>`)
- DOI (from `<ArticleId IdType="doi">`)

**Rate limit:** Maximum 3 requests/second without API key. Use NCBI API key if available.

### Cochrane CENTRAL API

```
GET https://www.cochranelibrary.com/central/doi/10.1002/central/search/results
  ?q={URL-encoded query}
  &p_p_id=scolarSearchResultsPortlet_WAR_scolarSearchResultsportlet_INSTANCE_*
  &showSearchForm=true
```

Note: Cochrane does not have a fully public REST API. Use web scraping of search results or the Cochrane Register API if institutional access is available. Log attempted records and note any access limitations.

Fallback: If CENTRAL is inaccessible, note in the PRISMA diagram and proceed with PubMed + ClinicalTrials.gov.

### ClinicalTrials.gov API v2

```
GET https://clinicaltrials.gov/api/v2/studies
  ?query.term={URL-encoded terms}
  &filter.overallStatus=COMPLETED
  &filter.studyType=INTERVENTIONAL
  &pageSize=100
  &format=json
```

Paginate via `nextPageToken` until exhausted. Extract:
- NCT ID
- Official Title
- Brief Summary
- Conditions (population)
- Interventions
- Primary outcomes
- Completion date
- Results section URL (if results posted)

### Deduplication

After collecting all records, deduplicate using this priority order:

1. **PMID match:** exact PMID match → remove duplicate
2. **DOI match:** exact DOI match → remove duplicate
3. **Title fuzzy match:** normalise titles (lowercase, remove punctuation, collapse whitespace); if normalised Levenshtein similarity > 0.90, treat as duplicate — keep the PubMed record if available, otherwise keep the first encountered

**Log per-database hit counts (before and after deduplication):**

```
Search results:
  PubMed:             {n} records
  Cochrane CENTRAL:   {n} records
  ClinicalTrials.gov: {n} records
  Total before dedup: {n} records
  Duplicates removed: {n} records
  Total after dedup:  {n} records
```

These counts feed the PRISMA flow diagram in Stage 1.5.

---

## Stage 1.4 — Abstract Screening

**Purpose:** Classify each deduplicated record as include / exclude / uncertain based on PICO inclusion criteria.

### Inclusion Criteria

Apply all of the following (must satisfy all to include):

| Criterion | Requirement |
|---|---|
| Study design | Randomised controlled trial (RCT) or quasi-RCT with clear allocation |
| Population | Matches the P element of the PICO — check title/abstract for disease, severity, setting |
| Intervention | Matches the I element — at least one arm uses the specified intervention or drug class |
| Comparator | Matches the C element — active comparator, placebo, or standard care as specified |
| Outcome | At least one outcome from the O element is reported or likely reported |
| Language | English, or a machine translation is available |
| Publication status | Full published article or registered trial with results; conference abstracts only if results are complete |

### Exclusion Criteria (automatic exclusions)

- Animal or in vitro studies
- Reviews, meta-analyses, editorials, letters (without original data)
- Protocols without results
- Population clearly outside the P element (e.g., wrong disease, wrong age group)
- Intervention clearly different (e.g., different drug class)

### Classification Rules

- **Include:** All inclusion criteria clearly met based on title and abstract
- **Exclude:** Any mandatory exclusion criterion clearly met, or population/intervention clearly outside PICO
- **Uncertain:** Cannot determine from title/abstract alone; full text retrieval needed

**Process:** Screen title and abstract for each record. Assign classification. Generate a short one-line reason for all exclusions and uncertainties.

### Human Checkpoint #2 — Shortlist Review

**Present to the user:**

```
HUMAN CHECKPOINT 2: Abstract Screening Review

Include:    {n} papers
Uncertain:  {n} papers (require full-text review)
Exclude:    {n} papers

Included papers:
[numbered list with title, first author, year, reason for inclusion]

Uncertain papers (recommend full-text retrieval):
[numbered list with title, first author, year, reason for uncertainty]

Please review:
  (a) Approve shortlist + request full-text for uncertain papers → "approve"
  (b) Move specific papers between categories → specify adjustments
  (c) Add any papers you know are missing → provide PMIDs/DOIs

After your approval, full-text retrieval and data extraction begin (Phase 2).
```

**Do not proceed to Phase 2 until the user approves the shortlist.**

---

## Stage 1.5 — PRISMA Flow Diagram

**Purpose:** Generate a PRISMA 2020-compliant flow diagram summarising the identification and screening process.

**Required counts dict:**

```python
prisma_counts = {
    "db_pubmed":           n,   # PubMed records before dedup
    "db_central":          n,   # CENTRAL records before dedup
    "db_ctgov":            n,   # ClinicalTrials.gov records before dedup
    "identified":          n,   # total before dedup
    "duplicates_removed":  n,
    "screened":            n,   # after dedup
    "excluded_screening":  n,   # excluded at title/abstract stage
    "eligible":            n,   # sent for full-text review
    "excluded_eligibility":n,   # excluded after full-text review
    "included":            n,   # final included studies
}
```

**Code invocation:**

```python
from pipeline.visualizations import prisma_flow_svg

svg = prisma_flow_svg(prisma_counts)
# svg is an SVG string; embed in the Markdown report
```

**Output:** SVG string embedded in the Phase 1 summary and the final report.

---

## Phase 1 Outputs

After completing all Stage 1.x steps, produce:

1. **PICO JSON** — structured search parameters
2. **Search log** — per-database hit counts, query text, date executed
3. **Screened records list** — all records with classification and reason
4. **PRISMA counts dict** — feeds Stage 3.7 report assembly
5. **Included studies list** — PMIDs / DOIs / NCT IDs for Phase 2 data extraction

Pass all five outputs forward to Phase 2.
