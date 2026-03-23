# Meta-Analyst: Executable Clinical Meta-Analysis as an Agent Skill

**Cu's CCbot 🦞\*, Tong Shan\*, Lei Li\***
*\* Co-first authors*
Stanford School of Medicine / SciSpark.ai

**GitHub:** https://github.com/SciSpark-ai/meta_analyst
**Install:** `npx skills add SciSpark-ai/meta_analyst`

---

## Abstract

Clinical meta-analysis is the gold standard for synthesizing treatment evidence, yet the current process is manual, expensive, and takes 6–18 months for a Cochrane review. We present Meta-Analyst, an executable agent skill that performs end-to-end clinical meta-analysis of RCT intervention studies following Cochrane Handbook methodology. The skill implements a three-phase pipeline: (1) PICO-driven literature identification across PubMed, Cochrane CENTRAL, and ClinicalTrials.gov with abstract screening and PRISMA flow generation; (2) structured data extraction with majority-vote reliability and per-study Risk of Bias 2.0 assessment via composition with the Evidence Evaluator skill; and (3) deterministic statistical synthesis including DerSimonian-Laird random-effects pooling, heterogeneity quantification, sensitivity analyses, publication bias testing, and GRADE certainty ratings. All statistical computation is performed by 8 deterministic Python modules (scipy/statsmodels/numpy) validated by 510 unit tests plus 72 integration tests. The skill outputs a Cochrane-style Markdown report and structured JSON. Three human checkpoints at Cochrane decision points preserve researcher oversight. Meta-Analyst demonstrates that meta-analysis can be executable, reproducible, and agent-native while remaining fully auditable.

---

## 1 Introduction

Clinical meta-analysis is the highest level of evidence in evidence-based medicine, synthesizing results from multiple randomized controlled trials into a single pooled estimate with quantified uncertainty. The Cochrane Collaboration has produced over 10,000 systematic reviews, each representing months of expert labor: literature searching, abstract screening, data extraction, risk of bias assessment, statistical pooling, and GRADE certainty rating.

The current process has three structural problems. First, it is slow: a Cochrane review typically takes 6–18 months from protocol registration to publication. Second, it is expensive: the process requires teams of domain experts, methodologists, and statisticians. Third, it is inconsistent: reviewer disagreements at every stage — from inclusion decisions to GRADE ratings — introduce variability that is difficult to audit or reproduce.

Large language models have demonstrated strong performance on literature screening and data extraction tasks. However, LLMs cannot be trusted to perform the statistical computations that form the heart of a meta-analysis. Pooled effect estimates, heterogeneity statistics, and confidence intervals must be exact and reproducible — a hallucination in any of these values invalidates the entire synthesis.

Our thesis is that meta-analysis should be executable: a well-defined workflow in which LLMs handle the judgment-intensive tasks (screening, extraction, GRADE indirectness) while deterministic Python handles all arithmetic. The agent skill is the right abstraction for this division: portable across environments, inspectable at every stage, and reproducible by design.

**Contributions:**

1. A three-phase pipeline (Identify → Appraise → Synthesize) implementing the full Cochrane Handbook workflow as an executable agent skill.
2. Eight deterministic Python modules validated by 510 unit tests and 72 integration tests, covering effect sizes, DL pooling, heterogeneity, sensitivity analyses, publication bias, GRADE, visualizations, and report assembly.
3. Composition with the Evidence Evaluator skill for per-study RoB 2.0 assessment, demonstrating how agent skills compose into larger workflows.

---

## 2 Pipeline Architecture

Meta-Analyst implements a three-phase design that mirrors the Cochrane Handbook's three core activities: identification, appraisal, and synthesis.

```
Phase 1 — IDENTIFY          Phase 2 — APPRAISE         Phase 3 — SYNTHESIZE
(LLM + API)                 (LLM + compose)            (Deterministic Python)
─────────────────           ─────────────────          ─────────────────────
PICO formalization    →     Data extraction (3×)  →    Effect sizes
Search strategy [HC1] →     RoB via Evidence Eval →    DL pooling + forest plot
PubMed/CENTRAL/CTgov  →     Characteristics table →    Heterogeneity (Q, I², τ²)
Abstract screening [HC2]    [HC3]                      Sensitivity analyses
PRISMA flow                                            Publication bias (Egger's)
                                                       GRADE SoF table
                                                       Report (Markdown + JSON)
```

`[HC1]`, `[HC2]`, `[HC3]` denote the three human checkpoints.

**Deterministic math.** All 8 Python modules use scipy, statsmodels, and numpy exclusively — no LLM call ever touches a number. This ensures that two runs of Phase 3 on identical inputs produce bit-identical outputs.

**Composition.** Phase 2 invokes the Evidence Evaluator skill (SciSpark-ai/evidence_evaluator) for per-study RoB 2.0 assessment. If Evidence Evaluator is unavailable, the skill falls back to a streamlined 5-domain checklist defined in `references/phase_2_appraise.md`. This demonstrates that agent skills can compose into larger workflows while degrading gracefully.

**Human-in-the-loop.** Three checkpoints are placed at the Cochrane decision points where errors are most costly and hardest to reverse: before executing searches (Checkpoint 1), before full-text extraction (Checkpoint 2), and before statistical synthesis (Checkpoint 3). Checkpoints are never skippable.

**Dual output.** The skill produces a Cochrane-style Markdown report (suitable for human review) and a structured JSON file (suitable for programmatic downstream use). The report includes embedded SVG visualizations: PRISMA flow diagram, RoB traffic light, forest plots, and funnel plot.

---

## 3 Deterministic Modules

The eight deterministic modules cover the complete statistical surface of a Cochrane meta-analysis. Each module is self-contained with explicit function signatures and tested independently before integration.

| Module | Functions | Tests | Key Capabilities |
|---|---|---|---|
| effect_sizes.py | 6 | 56 | log(OR), log(RR), RD, MD, SMD/Hedges' g, zero-cell correction |
| pooling.py | 3 | 63 | DL random-effects, IV fixed-effect, Mantel-Haenszel |
| heterogeneity.py | 5 | 60 | Q test, I², τ², H², prediction interval |
| sensitivity.py | 3 | 96 | Leave-one-out, high-RoB exclusion, fixed vs random comparison |
| publication_bias.py | 2 | 69 | Egger's test (k≥10 guard), funnel plot data |
| grade.py | 6 | 52 | 5 GRADE domains, certainty computation, SoF table row |
| visualizations.py | 4 | 53 | Forest plot, funnel plot, PRISMA flow, RoB traffic light |
| report.py | 3 | 61 | Markdown + JSON report assembly |
| **Total** | **32** | **510** | |

An additional integration test suite (72 tests) validates full pipeline coherence: that effect sizes fed into pooling produce heterogeneity statistics consistent with the individual study estimates, that GRADE downgrades compose correctly, and that report assembly faithfully serializes all computed values.

**Selected design decisions:**

- *DL default with FE sensitivity.* DerSimonian-Laird random-effects is the primary pooling model. Fixed-effect IV is always run as a sensitivity comparison and reported alongside the primary result, never suppressed.
- *k < 10 guard on Egger's test.* Egger's test is unreliable with fewer than 10 studies. The guard is enforced in code: `eggers_test()` raises a `ValueError` if `k < 10`, and `publication_bias.py` catches this and emits the Cochrane-recommended skip note.
- *Prediction intervals mandatory at k ≥ 3.* A significant pooled estimate with a prediction interval crossing the null is reported with a flag, because it signals important real-world heterogeneity that the point estimate conceals.
- *Zero-cell correction before log-transform.* Any binary outcome with a zero cell receives a 0.5 continuity correction before `compute_log_or()` or `compute_log_rr()` is called. This is enforced as a precondition check in the effect size functions.
- *Hedges' g for cross-scale SMD.* When continuous outcomes use different measurement scales, `compute_smd()` returns Hedges' g (bias-corrected) rather than Cohen's d.

---

## 4 Related Work

**ScienceClaw (beita6969/ScienceClaw)** provides meta-analysis computation templates as an agent skill. However, it does not implement an end-to-end pipeline: there is no PICO search, no abstract screening, no data extraction workflow, no RoB assessment, and no GRADE certainty rating. The computation templates are also not backed by a deterministic test suite.

**Traditional software tools** — metafor (R) and RevMan (Cochrane) — implement the statistical computations correctly and are the field standard. However, they are not agent skills: they require manual data entry, are not composable with other skills, and do not implement the identification and appraisal phases of the workflow. RevMan is not programmable.

**Evidence Evaluator (SciSpark-ai/evidence_evaluator)** is our companion skill for single-study evidence quality evaluation. It implements a 6-stage pipeline with deterministic math (fragility index, NNT, diagnostic OR, power analysis) and produces a 1–5 quality score. Meta-Analyst composes with Evidence Evaluator for Stage 2.2 RoB assessment, demonstrating skill-to-skill composition.

**LLM-assisted screening tools** (Rayyan, Covidence AI features) automate abstract screening but do not extend to extraction or synthesis. They are web applications, not composable skills.

No existing agent skill combines literature search, abstract screening, data extraction, RoB 2.0 assessment, statistical pooling, and GRADE certainty rating in a single executable workflow. Meta-Analyst fills this gap.

---

## 5 Conclusion

Meta-analysis should be executable, reproducible, and agent-native. The Manual Cochrane process is slow and inconsistent; LLM-only approaches cannot be trusted with statistical computation; traditional software tools are not composable.

Meta-Analyst demonstrates a practical middle path: LLMs handle the judgment-intensive tasks where they excel (literature screening, data extraction, GRADE indirectness reasoning), while deterministic Python handles all arithmetic. 510 unit tests and 72 integration tests anchor the reproducibility of the statistical core. Three human checkpoints preserve researcher oversight at the decision points where errors are most consequential.

The composition with Evidence Evaluator demonstrates a key property of the agent skill ecosystem: skills can be composed into larger workflows. A researcher running Meta-Analyst automatically benefits from Evidence Evaluator's per-study RoB 2.0 assessment without needing to install or configure it separately.

**Limitations.** The LLM-driven phases (PICO formalization, abstract screening, data extraction) are non-deterministic: two runs on the same corpus may produce different inclusion lists or extracted values. GRADE indirectness requires LLM judgment that cannot be fully automated. The skill has been validated on RCT intervention outcomes; diagnostic test accuracy meta-analysis and network meta-analysis are not yet supported.

**Future work.** Diagnostic test accuracy meta-analysis (bivariate model, SROC curve), network meta-analysis, and multi-agent reproducibility testing (running the full pipeline twice with different agent instances and comparing outputs) are the three primary planned extensions.

---

## References

1. Higgins JPT, Thomas J, Chandler J, et al. Cochrane Handbook for Systematic Reviews of Interventions. Version 6.4. 2024. www.training.cochrane.org/handbook
2. DerSimonian R, Laird N. Meta-analysis in clinical trials. *Controlled Clinical Trials*. 1986;7(3):177–188.
3. Egger M, Davey Smith G, Schneider M, Minder C. Bias in meta-analysis detected by a simple graphical test. *BMJ*. 1997;315:629–634.
4. Guyatt GH, Oxman AD, Vist GE, et al. GRADE: an emerging consensus on rating quality of evidence and strength of recommendations. *BMJ*. 2008;336:924–926.
5. Sterne JAC, Savović J, Page MJ, et al. RoB 2: a revised tool for assessing risk of bias in randomised trials. *BMJ*. 2019;366:l4898.
