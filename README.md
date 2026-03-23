# Meta-Analyst

End-to-end clinical meta-analysis of RCT intervention studies, packaged as an installable AI agent skill.

## What it does

Meta-Analyst runs a three-phase agentic pipeline that takes a clinical question and produces a full Cochrane-style meta-analysis report. Phase 1 identifies eligible studies via structured database searches (PubMed, Cochrane CENTRAL, ClinicalTrials.gov). Phase 2 extracts data and appraises study quality using RoB 2.0. Phase 3 performs deterministic statistical pooling, heterogeneity assessment, sensitivity analyses, publication bias testing, and GRADE certainty ratings — then assembles a complete report with forest plots, funnel plots, a PRISMA flow diagram, and a Summary of Findings table.

## Install

```bash
npx skills add SciSpark-ai/meta_analyst
```

## Quick Start

After installing, open Claude Code and ask a clinical question:

```
What is the effect of beta-blockers on mortality in patients with heart failure?
```

The pipeline will pause at three human checkpoints to get your approval before proceeding:

1. **Search strategy** — review and approve the PICO formulation and search terms
2. **Screening** — review the title/abstract inclusion decisions
3. **Extraction + RoB** — review the extracted data and risk of bias assessments

After the final checkpoint, Phase 3 runs automatically and delivers the complete report.

## Pipeline

**Phase 1 — Identify**
Decomposes the clinical question into a PICO framework, constructs Boolean search strings, queries PubMed E-utilities, Cochrane CENTRAL, and ClinicalTrials.gov, deduplicates results, and screens titles/abstracts for eligibility.

**Phase 2 — Appraise**
Retrieves full texts, extracts quantitative data (event counts, means, SDs, sample sizes), assesses risk of bias using RoB 2.0 (via Evidence Evaluator), and builds the study characteristics table.

**Phase 3 — Synthesize**
Computes per-study effect sizes, pools with DerSimonian-Laird random effects, assesses heterogeneity (I², tau², prediction interval), runs leave-one-out and high-RoB sensitivity analyses, tests for publication bias (Egger's test when k ≥ 10), applies GRADE certainty ratings, and assembles the final report.

## Output

The report is delivered as Markdown (with embedded SVGs) and a structured JSON file, containing:

- Forest plot with individual and pooled effect sizes
- Funnel plot (when k ≥ 10)
- PRISMA 2020 flow diagram
- RoB traffic light summary
- Summary of Findings table with GRADE certainty ratings
- Heterogeneity statistics (I², tau², Q, prediction interval)
- Sensitivity analysis results
- Publication bias assessment

## Development

```bash
pip install scipy statsmodels numpy

# Run from skills/meta-analyst/ directory
cd skills/meta-analyst

python ../../tests/test_effect_sizes.py       # 56/56 pass
python ../../tests/test_pooling.py            # 63/63 pass
python ../../tests/test_heterogeneity.py      # 60/60 pass
python ../../tests/test_sensitivity.py        # 96/96 pass
python ../../tests/test_publication_bias.py   # 69/69 pass
python ../../tests/test_grade.py              # 52/52 pass
python ../../tests/test_visualizations.py     # 53/53 pass
python ../../tests/test_report.py             # 61/61 pass
```

## License

MIT
