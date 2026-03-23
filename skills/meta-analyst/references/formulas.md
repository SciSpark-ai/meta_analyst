# Statistical Formulas Reference

All formulas used by the meta-analyst pipeline. Each entry includes the name, LaTeX notation, the corresponding Python function, and interpretation notes.

---

## 1. Zero-Cell Correction

**Name:** Continuity correction for 2×2 tables with zero cells

**Rule:** If any cell in the 2×2 table (a, b, c, d) equals zero, add 0.5 to **all four cells** before computing any log-transformed effect size.

$$a' = a + 0.5,\quad b' = b + 0.5,\quad c' = c + 0.5,\quad d' = d + 0.5$$

**Python function:** `pipeline.effect_sizes.zero_cell_correction(a, b, c, d, correction=0.5)`

**Interpretation:** Prevents division by zero and undefined logarithms. Apply before `compute_log_or`, `compute_log_rr`. Not needed for `compute_rd`, `compute_md`, or `compute_smd`.

---

## 2. Effect Sizes

### 2.1 Log Odds Ratio

**Name:** Log odds ratio (log OR) with standard error

**Formula:**

$$\log\!\widehat{OR} = \ln\!\left(\frac{a \cdot d}{b \cdot c}\right)$$

$$SE(\log\widehat{OR}) = \sqrt{\frac{1}{a} + \frac{1}{b} + \frac{1}{c} + \frac{1}{d}}$$

95% CI on OR scale: $\exp\!\left(\log\widehat{OR} \pm 1.96 \cdot SE\right)$

**Python function:** `pipeline.effect_sizes.compute_log_or(a, b, c, d)`

**Returns:** `{log_or, se, or_value, ci_lower, ci_upper}`

**Interpretation:** OR > 1 favours the intervention group for the event. Use for case-control designs or when RR is not estimable. Always apply `zero_cell_correction` first when any cell may be 0.

---

### 2.2 Log Relative Risk

**Name:** Log relative risk (log RR) with standard error

**Formula:**

$$\log\!\widehat{RR} = \ln\!\left(\frac{a/(a+b)}{c/(c+d)}\right)$$

$$SE(\log\widehat{RR}) = \sqrt{\frac{1}{a} - \frac{1}{a+b} + \frac{1}{c} - \frac{1}{c+d}}$$

95% CI on RR scale: $\exp\!\left(\log\widehat{RR} \pm 1.96 \cdot SE\right)$

**Python function:** `pipeline.effect_sizes.compute_log_rr(a, b, c, d)`

**Returns:** `{log_rr, se, rr, ci_lower, ci_upper}`

**Interpretation:** RR > 1 means the event is more common in the intervention arm. Preferred over OR for common outcomes (>10%) in cohort studies and RCTs.

---

### 2.3 Risk Difference

**Name:** Risk difference (RD, absolute risk reduction) with standard error

**Formula:**

$$\widehat{RD} = \frac{a}{a+b} - \frac{c}{c+d}$$

$$SE(\widehat{RD}) = \sqrt{\frac{\hat{p}_1(1-\hat{p}_1)}{n_1} + \frac{\hat{p}_2(1-\hat{p}_2)}{n_2}}$$

where $n_1 = a+b$, $n_2 = c+d$, $\hat{p}_1 = a/n_1$, $\hat{p}_2 = c/n_2$.

95% CI: $\widehat{RD} \pm 1.96 \cdot SE$

**Python function:** `pipeline.effect_sizes.compute_rd(a, b, c, d)`

**Returns:** `{rd, se, ci_lower, ci_upper}`

**Interpretation:** RD < 0 means fewer events in the intervention arm. Directly interpretable as the absolute risk reduction; NNT = 1/|RD|.

---

### 2.4 Mean Difference

**Name:** Mean difference (MD) with standard error

**Formula:**

$$\widehat{MD} = \bar{X}_I - \bar{X}_C$$

$$SE(\widehat{MD}) = \sqrt{\frac{s_I^2}{n_I} + \frac{s_C^2}{n_C}}$$

95% CI: $\widehat{MD} \pm 1.96 \cdot SE$

**Python function:** `pipeline.effect_sizes.compute_md(mean_i, sd_i, n_i, mean_c, sd_c, n_c)`

**Returns:** `{md, se, ci_lower, ci_upper}`

**Interpretation:** MD retains the original measurement scale. Use only when all studies use the same outcome scale. A positive MD means the intervention arm has higher values.

---

### 2.5 Standardised Mean Difference (Hedges' g)

**Name:** Standardised mean difference with small-sample (J) correction (Hedges' g)

**Formula:**

$$s_p = \sqrt{\frac{(n_I-1)s_I^2 + (n_C-1)s_C^2}{n_I+n_C-2}}$$

$$J = 1 - \frac{3}{4(n_I+n_C-2)-1}$$

$$g = \frac{\bar{X}_I - \bar{X}_C}{s_p} \cdot J$$

$$SE(g) = \sqrt{\frac{n_I+n_C}{n_I \cdot n_C} + \frac{g^2}{2(n_I+n_C-2)}} \cdot J$$

95% CI: $g \pm 1.96 \cdot SE(g)$

**Python function:** `pipeline.effect_sizes.compute_smd(mean_i, sd_i, n_i, mean_c, sd_c, n_c)`

**Returns:** `{smd, se, ci_lower, ci_upper}` — `smd` is Hedges' g.

**Interpretation:** SMD = 0.2 small, 0.5 medium, 0.8 large (Cohen's conventions). Use when outcomes are measured on different scales across studies.

---

## 3. Fixed-Effect Pooling (Inverse-Variance)

**Name:** Inverse-variance weighted pooling (fixed-effect model)

**Formula:**

$$w_i = \frac{1}{SE_i^2}$$

$$\hat{\theta}_{FE} = \frac{\sum_i w_i \hat{\theta}_i}{\sum_i w_i}$$

$$SE(\hat{\theta}_{FE}) = \sqrt{\frac{1}{\sum_i w_i}}$$

$$95\%\ \text{CI}: \hat{\theta}_{FE} \pm 1.96 \cdot SE(\hat{\theta}_{FE})$$

**Python function:** `pipeline.pooling.pool_fixed_effect_iv(effects, ses)`

**Returns:** `{pooled, se, ci_lower, ci_upper, p_value, weights}`

**Interpretation:** Assumes a single true effect shared by all studies. Gives more weight to larger (more precise) studies. Use only for comparison with DL random-effects; report DL as the primary result when heterogeneity is present.

---

## 4. Random-Effects Pooling (DerSimonian-Laird)

**Name:** DerSimonian-Laird random-effects pooling

**Step 1: Fixed-effect weights and Q statistic**

$$w_i^{FE} = \frac{1}{SE_i^2}, \quad \hat{\theta}_{FE} = \frac{\sum w_i^{FE}\hat{\theta}_i}{\sum w_i^{FE}}$$

$$Q = \sum_i w_i^{FE}(\hat{\theta}_i - \hat{\theta}_{FE})^2$$

**Step 2: Between-study variance (tau²)**

$$c = \sum w_i^{FE} - \frac{\sum (w_i^{FE})^2}{\sum w_i^{FE}}$$

$$\hat{\tau}^2 = \max\!\left(0,\; \frac{Q - (k-1)}{c}\right)$$

**Step 3: RE weights and pooled estimate**

$$w_i^{RE} = \frac{1}{SE_i^2 + \hat{\tau}^2}$$

$$\hat{\theta}_{RE} = \frac{\sum_i w_i^{RE} \hat{\theta}_i}{\sum_i w_i^{RE}}$$

$$SE(\hat{\theta}_{RE}) = \sqrt{\frac{1}{\sum_i w_i^{RE}}}$$

$$95\%\ \text{CI}: \hat{\theta}_{RE} \pm 1.96 \cdot SE(\hat{\theta}_{RE})$$

**Python function:** `pipeline.pooling.pool_random_effects_dl(effects, ses)`

**Returns:** `{pooled, se, ci_lower, ci_upper, p_value, tau_sq, q_stat, weights, prediction_interval}`

**Interpretation:** Default pooling method. Assumes studies estimate different but related true effects drawn from a distribution with mean $\mu$ and variance $\tau^2$. When $\tau^2 = 0$, reduces to fixed-effect. Use fixed-effect only for sensitivity comparison.

### 4.1 Prediction Interval

**Formula** (requires $k \ge 3$):

$$PI = \hat{\theta}_{RE} \pm t_{k-2,\,0.975} \cdot \sqrt{SE(\hat{\theta}_{RE})^2 + \hat{\tau}^2}$$

**Python function:** `pipeline.pooling.pool_random_effects_dl` (included in output dict); also standalone `pipeline.heterogeneity.prediction_interval(pooled, se_pooled, tau_sq, k)`

**Interpretation:** Range within which 95% of future single-study effects are expected to fall. Wider than the CI when $\tau^2 > 0$. A PI crossing the null despite a significant pooled estimate signals important heterogeneity.

---

## 5. Mantel-Haenszel Pooling

**Name:** Mantel-Haenszel (MH) pooling from raw 2×2 tables

### 5.1 MH Odds Ratio

$$\widehat{OR}_{MH} = \frac{\sum_i (a_i d_i / N_i)}{\sum_i (b_i c_i / N_i)}$$

**Robins-Breslow-Greenland (RBG) variance of $\log(\widehat{OR}_{MH})$:**

Let $R_i = a_i d_i / N_i$, $S_i = b_i c_i / N_i$, $P_i = (a_i+d_i)/N_i$, $Q_i = (b_i+c_i)/N_i$, $R = \sum R_i$, $S = \sum S_i$.

$$\text{Var}\!\left[\log\widehat{OR}_{MH}\right] = \frac{\sum P_i R_i}{2R^2} + \frac{\sum(P_i S_i + Q_i R_i)}{2RS} + \frac{\sum Q_i S_i}{2S^2}$$

### 5.2 MH Relative Risk

$$\widehat{RR}_{MH} = \frac{\sum_i a_i n_{C_i}/N_i}{\sum_i c_i n_{I_i}/N_i}$$

**Greenland-Robins variance of $\log(\widehat{RR}_{MH})$:**

$$\text{Var}\!\left[\log\widehat{RR}_{MH}\right] = \frac{\sum_i \frac{n_{I_i} n_{C_i}(a_i+c_i) - a_i c_i N_i}{N_i^2}}{\left(\sum_i \frac{a_i n_{C_i}}{N_i}\right)\!\left(\sum_i \frac{c_i n_{I_i}}{N_i}\right)}$$

**Python function:** `pipeline.pooling.pool_mantel_haenszel(tables, measure="OR")`

**Returns:** `{pooled, se, ci_lower, ci_upper, p_value, log_pooled}`

**Interpretation:** MH is preferred over IV when studies have sparse data (small event counts) because it does not require log-transformation of individual study estimates. Use as a sensitivity check alongside DL random-effects.

---

## 6. Heterogeneity Statistics

### 6.1 Cochran's Q

$$Q = \sum_i w_i^{FE}(\hat{\theta}_i - \hat{\theta}_{FE})^2$$

$Q$ follows a $\chi^2$ distribution with $k-1$ degrees of freedom under the null of homogeneity.

**Python function:** `pipeline.heterogeneity.cochrans_q(effects, ses)`

**Returns:** `{q, df, p_value}`

**Interpretation:** Low power for $k < 5$; high power for $k > 20$. Significant $Q$ ($p < 0.10$ by convention) suggests heterogeneity, but the p-value alone is insufficient — always also report $I^2$.

### 6.2 I²

$$I^2 = \max\!\left(0,\; \frac{Q - (k-1)}{Q} \times 100\right)$$

**Python function:** `pipeline.heterogeneity.i_squared(q, df)`

**Returns:** `{i_squared, interpretation}`

**Cochrane Handbook 10.10.2 thresholds:**

| I² range | Interpretation |
|---|---|
| 0–40% | low |
| 40–60% | moderate |
| 60–75% | substantial |
| ≥75% | considerable |

Note: these thresholds are approximate guides, not rigid rules. Context matters.

### 6.3 tau²

$$\hat{\tau}^2 = \max\!\left(0,\; \frac{Q-(k-1)}{c}\right), \quad c = \sum w_i - \frac{\sum w_i^2}{\sum w_i}$$

**Python function:** `pipeline.heterogeneity.tau_squared_dl(q, df, weights)`

**Returns:** `float` — between-study variance

**Interpretation:** Absolute scale heterogeneity. $\sqrt{\hat{\tau}^2}$ (tau) is the standard deviation of the distribution of true effects.

### 6.4 H²

$$H^2 = \frac{Q}{k-1}$$

**Python function:** `pipeline.heterogeneity.h_squared(q, df)`

**Returns:** `float`

**Interpretation:** $H^2 = 1$ indicates no heterogeneity; $H^2 > 1$ indicates between-study variation beyond sampling error.

---

## 7. Egger's Test for Publication Bias

**Name:** Egger's regression test for funnel asymmetry

**Regression model:**

$$\frac{\hat{\theta}_i}{SE_i} = \beta_0 + \beta_1 \cdot \frac{1}{SE_i} + \varepsilon_i$$

Fit by OLS. Test $H_0: \beta_0 = 0$ using a two-sided t-test.

**Python function:** `pipeline.publication_bias.eggers_test(effects, ses)`

**Returns:** `{intercept, se, p_value, skipped, reason}`

**Guard:** Skips (returns `skipped=True`) when $k < 10$.

**Interpretation:** A significant intercept ($p < 0.10$ by convention) suggests funnel plot asymmetry, which may indicate publication bias, small-study effects, or heterogeneity. Cannot distinguish between these causes. Apply only when $k \ge 10$ (Cochrane Handbook 10.4.3.1).

---

## 8. GRADE Imprecision: Optimal Information Size (OIS)

**Name:** Optimal information size for GRADE imprecision assessment

**Concept:** The OIS is the total sample size required to detect a clinically meaningful effect with adequate power (typically 80–85%) at a two-sided alpha of 0.05. It is analogous to the sample size of a single adequately powered RCT.

**Binary outcomes (simplified):**

$$OIS \approx \frac{(z_{1-\alpha/2} + z_{1-\beta})^2 \cdot [p_C(1-p_C) + p_I(1-p_I)]}{(p_C - p_I)^2}$$

where $z_{0.975} = 1.96$ and $z_{0.80} = 0.84$ for 80% power.

**Continuous outcomes:**

$$OIS \approx \frac{2(z_{1-\alpha/2} + z_{1-\beta})^2 \cdot \sigma^2}{\delta^2}$$

where $\delta$ is the minimum clinically important difference (MCID) and $\sigma$ is the pooled SD.

**Python function:** `pipeline.grade.assess_imprecision(ci_lower, ci_upper, null_value, ois, total_n)`

**Returns:** downgrade integer: `0`, `-1`, or `-2`

**GRADE imprecision downgrade rules:**
1. If the 95% CI crosses the null value → at least −1
2. If total N < OIS → at least −1
3. Both conditions met → −2

**Interpretation:** When the agent computes OIS, document the assumed event rate, MCID, and power. If OIS cannot be computed, fall back to checking whether the CI crosses the null only.

---

## 9. Summary of Python Module Imports

```python
# Effect sizes
from pipeline.effect_sizes import (
    compute_log_or, compute_log_rr, compute_rd,
    compute_md, compute_smd, zero_cell_correction
)

# Pooling
from pipeline.pooling import (
    pool_fixed_effect_iv, pool_random_effects_dl, pool_mantel_haenszel
)

# Heterogeneity
from pipeline.heterogeneity import (
    cochrans_q, i_squared, tau_squared_dl, h_squared, prediction_interval
)

# Sensitivity
from pipeline.sensitivity import (
    leave_one_out, exclude_high_rob, fixed_vs_random_comparison
)

# Publication bias
from pipeline.publication_bias import eggers_test, funnel_plot_data

# GRADE
from pipeline.grade import (
    assess_risk_of_bias, assess_inconsistency, assess_imprecision,
    assess_publication_bias, compute_grade, grade_summary_row
)

# Visualizations
from pipeline.visualizations import (
    forest_plot_svg, funnel_plot_svg, prisma_flow_svg, rob_traffic_light_svg
)

# Report
from pipeline.report import (
    assemble_report, format_characteristics_table, format_grade_sof_table
)
```
