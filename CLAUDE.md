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
  research_note.md
  submission/
    submit.sh
docs/
  implementation-plan.md
```

## Running Tests

```bash
pip install scipy statsmodels numpy

python tests/test_effect_sizes.py
python tests/test_pooling.py
python tests/test_heterogeneity.py
python tests/test_sensitivity.py
python tests/test_publication_bias.py
python tests/test_grade.py
python tests/test_visualizations.py
python tests/test_report.py
```

Tests use a custom pass/fail counter (not pytest). They print results to stdout.

## Architecture

- `skills/meta-analyst/SKILL.md` — Skill entry point. Defines pipeline, phase execution order, output format, and Python code usage.
- `skills/meta-analyst/pipeline/effect_sizes.py` — Computes per-study effect sizes: log(OR), log(RR), RD (binary); MD, SMD/Hedges' g (continuous). Handles zero-cell correction.
- `skills/meta-analyst/pipeline/pooling.py` — DerSimonian-Laird random-effects, inverse-variance fixed-effect, and Mantel-Haenszel pooling.
- `skills/meta-analyst/pipeline/heterogeneity.py` — Cochran's Q, I², tau² (DL estimator), H², and prediction intervals.
- `skills/meta-analyst/pipeline/sensitivity.py` — Leave-one-out analysis, high-RoB study exclusion, fixed-vs-random comparison.
- `skills/meta-analyst/pipeline/publication_bias.py` — Egger's regression test (skips if k < 10), funnel plot data.
- `skills/meta-analyst/pipeline/grade.py` — GRADE certainty rule engine: per-domain downgrade assessment (risk of bias, inconsistency, indirectness, imprecision, publication bias) + Summary of Findings table assembly.
- `skills/meta-analyst/pipeline/visualizations.py` — SVG generation for forest plot, funnel plot, PRISMA 2020 flow diagram, and RoB traffic light summary.
- `skills/meta-analyst/pipeline/report.py` — Assembles full Cochrane-style meta-analysis report as Markdown + JSON dual output.
- `skills/meta-analyst/references/` — Phase specs the agent reads before executing each phase.

## Tech Context

- All statistical computation is deterministic Python (scipy, statsmodels, numpy)
- Phase 1 (Identify) and Phase 2 (Appraise) are agent reasoning tasks — no Python modules needed
- Phase 3 (Synthesize) is fully deterministic
- All Python commands must run from `skills/meta-analyst/` directory for imports to resolve
- Composes with Evidence Evaluator (`SciSpark-ai/evidence_evaluator`) for per-study RoB 2.0 assessment
