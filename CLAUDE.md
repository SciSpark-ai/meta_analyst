# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Meta-Analyst is an installable Claude Code plugin containing a three-phase agentic pipeline that performs end-to-end clinical meta-analysis of RCT intervention studies following Cochrane Handbook methodology. Distributed as an open-source skill via `npx skills add SciSpark-ai/meta_analyst`.

## Repo Structure

```
.claude-plugin/plugin.json              ← Plugin manifest
skills/meta-analyst/
  SKILL.md                              ← Skill entry point
  pipeline/
    __init__.py
    effect_sizes.py                     ← log(OR), log(RR), RD, MD, SMD + SE
    pooling.py                          ← DL random-effects, IV fixed-effect, MH
    heterogeneity.py                    ← Q, I², tau², H², prediction interval
    sensitivity.py                      ← Leave-one-out, high-RoB exclusion
    publication_bias.py                 ← Egger's test
    grade.py                            ← GRADE certainty rule engine
    visualizations.py                   ← Forest plot, funnel plot, PRISMA flow, RoB traffic light (SVG)
    report.py                           ← Report assembly (Markdown + JSON)
  references/
    phase_1_identify.md                 ← PICO, search strategy, screening specs
    phase_2_appraise.md                 ← Extraction, RoB, characteristics table specs
    phase_3_synthesize.md               ← Pooling, heterogeneity, sensitivity, GRADE specs
    formulas.md                         ← All statistical formulas reference
tests/
  test_effect_sizes.py
  test_pooling.py
  test_heterogeneity.py
  test_sensitivity.py
  test_publication_bias.py
  test_grade.py
  test_visualizations.py
  test_report.py
paper/
  submission/
    submit.sh
docs/
  implementation-plan.md
```

## Running Tests

```bash
pip install scipy statsmodels numpy

python tests/test_effect_sizes.py       # 56/56 pass
python tests/test_pooling.py            # 63/63 pass
python tests/test_heterogeneity.py      # 60/60 pass
python tests/test_sensitivity.py        # 96/96 pass
python tests/test_publication_bias.py   # 69/69 pass
python tests/test_grade.py              # 52/52 pass
python tests/test_visualizations.py     # 53/53 pass
python tests/test_report.py             # 61/61 pass
```

All Python commands must run from `skills/meta-analyst/` directory for imports to resolve. Tests use a custom pass/fail counter (not pytest). They print results to stdout.

## Architecture

- `skills/meta-analyst/SKILL.md` — Skill entry point. Defines pipeline, phase execution order, output format, and Python code usage.
- `skills/meta-analyst/pipeline/effect_sizes.py` — Computes per-study effect sizes: log(OR), log(RR), RD (binary); MD, SMD/Hedges' g (continuous). Handles zero-cell correction (add 0.5 to all cells).
- `skills/meta-analyst/pipeline/pooling.py` — DerSimonian-Laird random-effects, inverse-variance fixed-effect, and Mantel-Haenszel pooling. Exports `pool_random_effects()`, `pool_fixed_effect()`, `pool_mantel_haenszel()`.
- `skills/meta-analyst/pipeline/heterogeneity.py` — Cochran's Q, I², tau² (DL estimator), H², and prediction intervals. Exports `assess_heterogeneity()`.
- `skills/meta-analyst/pipeline/sensitivity.py` — Leave-one-out analysis, high-RoB study exclusion, fixed-vs-random model comparison. Exports `leave_one_out()`, `exclude_high_rob()`, `fixed_vs_random()`.
- `skills/meta-analyst/pipeline/publication_bias.py` — Egger's regression test (skips automatically if k < 10), funnel plot asymmetry data. Exports `egger_test()`, `funnel_plot_data()`.
- `skills/meta-analyst/pipeline/grade.py` — GRADE certainty rule engine: per-domain downgrade assessment (risk of bias, inconsistency, indirectness, imprecision, publication bias) + Summary of Findings table assembly. Exports `assess_grade()`, `build_sof_table()`.
- `skills/meta-analyst/pipeline/visualizations.py` — SVG generation for forest plot, funnel plot, PRISMA 2020 flow diagram, and RoB traffic light summary. Exports `forest_plot_svg()`, `funnel_plot_svg()`, `prisma_flow_svg()`, `rob_traffic_light_svg()`.
- `skills/meta-analyst/pipeline/report.py` — Assembles full Cochrane-style meta-analysis report as Markdown + JSON dual output. Exports `assemble_report()`.
- `skills/meta-analyst/references/` — Phase specs the agent reads before executing each phase.

## Key Domain Rules

- **Default pooling**: DerSimonian-Laird random-effects model; switch to fixed-effect only when explicitly justified
- **I² interpretation**: Cochrane Handbook 10.10.2 (0–40% may not be important, 30–60% moderate, 50–90% substantial, 75–100% considerable)
- **Egger's test**: Only performed when k ≥ 10; skipped silently with a note when k < 10
- **GRADE starting point**: High for RCTs, Low for observational studies; downgrade only (never upgrade from RCT base)
- **Zero-cell correction**: Add 0.5 to all four cells of any 2×2 table containing a zero before computing log(OR) or log(RR)
- **GRADE indirectness**: Assessed by LLM reasoning against the PICO question; all other GRADE domains assessed by rule engine
- **Human checkpoints**: Three mandatory pause points — (1) search strategy approval before running searches, (2) title/abstract screening review, (3) full-text extraction + RoB review before pooling
- **Composes with Evidence Evaluator**: Use `SciSpark-ai/evidence_evaluator` for per-study RoB 2.0 assessment in Phase 2

## Claw4S 2026 Submission

- **clawRxiv post:** #287 — http://18.118.210.52/api/posts/287
- **Claw agent name:** Cu's CCbot
- **Human author:** Tong Shan
- **API key:** `oc_a4196eaa6ecdf22ed15cd7ffeb3a3e72d04de0a41b86057e51dbed7c49a18643`
- **Submit script:** `bash paper/submission/submit.sh <API_KEY>`
- **Conference site:** https://claw4s.github.io/
- **Submission spec:** https://claw4s.github.io/Claw4S_conference.md
- **Deadline:** April 5, 2026
- **Companion skill:** Evidence Evaluator (clawRxiv posts #270, #272) — same agent, same API key

## Sibling Repos

- **Evidence Evaluator:** https://github.com/SciSpark-ai/evidence_evaluator — single-study evidence quality evaluation (6-stage pipeline). Meta-Analyst composes with this for per-study RoB 2.0.
- **Planned:** Meta-Reviewer (inter-rater agreement benchmark), Systematic Screener (PRISMA screening)

## Tech Context

- All Phase 3 statistical computation is deterministic Python (scipy, statsmodels, numpy)
- Phase 1 (Identify) and Phase 2 (Appraise) are agent reasoning + API calls — no Python modules needed
- Phase 3 (Synthesize) invokes Python pipeline modules deterministically
- All Python commands must run from `skills/meta-analyst/` directory for imports to resolve
- Search databases: PubMed E-utilities, Cochrane CENTRAL, ClinicalTrials.gov API v2
