"""
report.py — Report assembly module for meta-analysis outputs.

Three public functions:
  format_characteristics_table — Markdown table of included studies
  format_grade_sof_table        — GRADE Summary of Findings Markdown table
  assemble_report               — Full report dict {"markdown": str, "json": dict}

The assemble_report function imports visualizations to embed SVG diagrams
directly into the Markdown body.
"""

import datetime

from pipeline.visualizations import (
    forest_plot_svg,
    funnel_plot_svg,
    prisma_flow_svg,
    rob_traffic_light_svg,
)


# ---------------------------------------------------------------------------
# 1. Characteristics of Included Studies Table
# ---------------------------------------------------------------------------

def format_characteristics_table(studies):
    """
    Build a Markdown characteristics-of-included-studies table.

    Parameters
    ----------
    studies : list of dicts with keys:
        first_author, year, n_intervention, n_control,
        intervention_description, comparator_description,
        followup_duration, rob_overall

    Returns
    -------
    str — Markdown table
    """
    headers = [
        "Study",
        "N (I / C)",
        "Intervention",
        "Comparator",
        "Follow-up",
        "RoB",
    ]

    def row(s):
        study_id = f"{s.get('first_author', '')} {s.get('year', '')}"
        n_col    = f"{s.get('n_intervention', '')} / {s.get('n_control', '')}"
        return [
            study_id.strip(),
            n_col,
            str(s.get("intervention_description", "")),
            str(s.get("comparator_description", "")),
            str(s.get("followup_duration", "")),
            str(s.get("rob_overall", "")),
        ]

    rows = [row(s) for s in studies]

    # Build table
    header_line    = "| " + " | ".join(headers) + " |"
    separator_line = "| " + " | ".join("---" for _ in headers) + " |"
    data_lines     = [
        "| " + " | ".join(cells) + " |"
        for cells in rows
    ]

    return "\n".join([header_line, separator_line] + data_lines)


# ---------------------------------------------------------------------------
# 2. GRADE Summary of Findings Table
# ---------------------------------------------------------------------------

def format_grade_sof_table(outcomes):
    """
    Build a GRADE Summary of Findings Markdown table.

    Parameters
    ----------
    outcomes : list of dicts with keys:
        name, n_studies, total_n, pooled_effect, ci_lower, ci_upper,
        certainty, certainty_symbols, downgrade_reasons

    Returns
    -------
    str — Markdown table
    """
    headers = [
        "Outcome",
        "Studies (N)",
        "Total participants",
        "Pooled effect (95% CI)",
        "Certainty",
        "Downgrade reasons",
    ]

    def row(o):
        effect_txt = (
            f"{o.get('pooled_effect', ''):.2f} "
            f"({o.get('ci_lower', ''):.2f} to {o.get('ci_upper', ''):.2f})"
        )
        certainty_txt = (
            f"{o.get('certainty_symbols', '')} "
            f"{o.get('certainty', '')}"
        ).strip()
        return [
            str(o.get("name", "")),
            str(o.get("n_studies", "")),
            str(o.get("total_n", "")),
            effect_txt,
            certainty_txt,
            str(o.get("downgrade_reasons", "")),
        ]

    rows = [row(o) for o in outcomes]

    header_line    = "| " + " | ".join(headers) + " |"
    separator_line = "| " + " | ".join("---" for _ in headers) + " |"
    data_lines     = [
        "| " + " | ".join(cells) + " |"
        for cells in rows
    ]

    return "\n".join([header_line, separator_line] + data_lines)


# ---------------------------------------------------------------------------
# 3. Full Report Assembly
# ---------------------------------------------------------------------------

def assemble_report(
    pico,
    search,
    prisma_counts,
    characteristics_table,
    rob_summary,
    outcomes,
    sensitivity,
    publication_bias,
    prisma_svg=None,
    rob_svg=None,
):
    """
    Assemble a full meta-analysis report.

    Parameters
    ----------
    pico                 : dict — {population, intervention, comparator,
                                   outcome, question}
    search               : dict — {query, date_range, databases}
    prisma_counts        : dict — counts for PRISMA flow diagram
    characteristics_table: str  — pre-built Markdown table
    rob_summary          : str  — narrative or Markdown RoB summary
    outcomes             : list of dicts — see below
    sensitivity          : dict — {outcome_name: {leave_one_out, ...}}
    publication_bias     : dict — {outcome_name: {egger_p, note}}
    prisma_svg           : str or None — pre-built SVG; if None, auto-generated
    rob_svg              : str or None — pre-built RoB SVG

    Each outcome dict in `outcomes` must contain:
        name, pooling, heterogeneity, studies, effects_for_funnel,
        ses_for_funnel, grade, sensitivity (optional), publication_bias (optional)

    Returns
    -------
    dict with keys:
        "markdown" : str
        "json"     : dict
    """
    today = datetime.date.today().isoformat()
    question = pico.get("question", "")
    db_list  = ", ".join(search.get("databases",
                ["PubMed", "Cochrane CENTRAL", "ClinicalTrials.gov"]))

    # ------------------------------------------------------------------ #
    # Generate PRISMA SVG if not provided
    # ------------------------------------------------------------------ #
    if prisma_svg is None:
        prisma_svg = prisma_flow_svg(prisma_counts)

    # ------------------------------------------------------------------ #
    # Build Markdown sections
    # ------------------------------------------------------------------ #
    sections = []

    # Title + metadata
    sections.append(f"# Meta-Analysis Report: {question}\n")
    sections.append(f"**Date:** {today}  \n**Search databases:** {db_list}\n")
    sections.append("---\n")

    # PRISMA
    sections.append("## PRISMA Flow Diagram\n")
    sections.append(prisma_svg + "\n")

    # Search Strategy
    sections.append("## Search Strategy\n")
    query = search.get("query", "")
    date_range = search.get("date_range", "")
    sections.append(f"**Query:** `{query}`\n")
    if date_range:
        sections.append(f"**Date range:** {date_range}\n")

    # Characteristics
    sections.append("## Characteristics of Included Studies\n")
    sections.append(characteristics_table + "\n")

    # Risk of Bias
    sections.append("## Risk of Bias Summary\n")
    if rob_svg:
        sections.append(rob_svg + "\n")
    sections.append(rob_summary + "\n")

    # Results — one subsection per outcome
    sections.append("## Results\n")
    for outcome in outcomes:
        name     = outcome.get("name", "Outcome")
        pooling  = outcome.get("pooling", {})
        het      = outcome.get("heterogeneity", {})
        studies_ = outcome.get("studies", [])
        efx      = outcome.get("effects_for_funnel", [])
        ses_     = outcome.get("ses_for_funnel", [])

        sections.append(f"### {name}\n")

        # Forest plot
        pooled_for_fp = {
            "pooled":   pooling.get("pooled", 0),
            "ci_lower": pooling.get("ci_lower", 0),
            "ci_upper": pooling.get("ci_upper", 0),
        }
        if studies_:
            fp_svg = forest_plot_svg(studies_, pooled_for_fp, title=name)
            sections.append(fp_svg + "\n")

        # Pooled estimate
        p_val = pooling.get("p_value", None)
        p_str = f"{p_val:.3f}" if p_val is not None else "N/A"
        sections.append(
            f"**Pooled estimate:** {pooling.get('pooled', 'N/A'):.2f} "
            f"(95% CI: {pooling.get('ci_lower', 'N/A'):.2f} to "
            f"{pooling.get('ci_upper', 'N/A'):.2f}), p = {p_str}  \n"
        )

        # Heterogeneity
        i2  = het.get("i2", "N/A")
        q   = het.get("q", "N/A")
        q_p = het.get("q_p_value", "N/A")
        i2_str = f"{i2:.1f}" if isinstance(i2, (int, float)) else str(i2)
        q_str  = f"{q:.2f}"  if isinstance(q,  (int, float)) else str(q)
        qp_str = f"{q_p:.3f}" if isinstance(q_p,(int, float)) else str(q_p)
        sections.append(
            f"**Heterogeneity:** I² = {i2_str}%, Q = {q_str}, p = {qp_str}  \n"
        )

        # Prediction interval
        pi_lo = het.get("prediction_lower", "N/A")
        pi_hi = het.get("prediction_upper", "N/A")
        pi_lo_str = f"{pi_lo:.2f}" if isinstance(pi_lo, float) else str(pi_lo)
        pi_hi_str = f"{pi_hi:.2f}" if isinstance(pi_hi, float) else str(pi_hi)
        sections.append(
            f"**Prediction interval:** {pi_lo_str} to {pi_hi_str}\n"
        )

    # Sensitivity Analyses
    sections.append("## Sensitivity Analyses\n")
    for outcome_name, sens in sensitivity.items():
        sections.append(f"### {outcome_name}\n")

        # Leave-one-out
        loo = sens.get("leave_one_out", [])
        if loo:
            sections.append("**Leave-one-out:**\n")
            rows = ["| Removed study | Pooled estimate |",
                    "|---|---|"]
            for entry in loo:
                rows.append(
                    f"| {entry.get('removed', '')} "
                    f"| {entry.get('pooled', ''):.2f} |"
                )
            sections.append("\n".join(rows) + "\n")

        # Fixed vs random
        fvr = sens.get("fixed_vs_random", {})
        if fvr:
            sections.append(
                f"**Fixed vs random-effects:** fixed = {fvr.get('fixed', 'N/A')}, "
                f"random = {fvr.get('random', 'N/A')}\n"
            )

        # High RoB excluded
        hrob = sens.get("high_rob_excluded", {})
        if hrob:
            sections.append(
                f"**High-RoB studies excluded** (n = {hrob.get('n_removed', '?')} removed): "
                f"pooled = {hrob.get('pooled', 'N/A')}\n"
            )

    # Publication Bias
    sections.append("## Publication Bias\n")
    for outcome_name, pb in publication_bias.items():
        sections.append(f"### {outcome_name}\n")

        # Funnel plot — look for matching outcome in outcomes list
        matching = next((o for o in outcomes if o.get("name") == outcome_name), None)
        if matching:
            efx = matching.get("effects_for_funnel", [])
            ses_ = matching.get("ses_for_funnel", [])
            pooled_val = matching.get("pooling", {}).get("pooled", 0.0)
            if efx and ses_:
                fn_svg = funnel_plot_svg(efx, ses_, pooled_val)
                sections.append(fn_svg + "\n")

        egger_p = pb.get("egger_p", None)
        note    = pb.get("note", "")
        if egger_p is not None:
            sections.append(f"**Egger's test:** p = {egger_p:.3f}  \n")
        if note:
            sections.append(f"{note}\n")

    # GRADE Summary of Findings
    sections.append("## GRADE Summary of Findings\n")
    grade_rows = []
    for o in outcomes:
        g = o.get("grade", {})
        p = o.get("pooling", {})
        h = o.get("heterogeneity", {})
        grade_rows.append({
            "name":               o.get("name", ""),
            "n_studies":          len(o.get("studies", [])),
            "total_n":            sum(
                s.get("weight_pct", 0) for s in o.get("studies", [])
            ),  # weight_pct used as proxy; real usage would have actual N
            "pooled_effect":      p.get("pooled", 0),
            "ci_lower":           p.get("ci_lower", 0),
            "ci_upper":           p.get("ci_upper", 0),
            "certainty":          g.get("certainty", ""),
            "certainty_symbols":  g.get("certainty_symbols", ""),
            "downgrade_reasons":  g.get("downgrade_reasons", ""),
        })
    sections.append(format_grade_sof_table(grade_rows) + "\n")

    # Summary placeholder
    sections.append("## Summary\n")
    sections.append(
        "Narrative summary to be generated by agent.\n"
    )

    sections.append("---\n")
    sections.append(
        "⚠️ **Disclaimer:** This meta-analysis was generated by an AI agent "
        "skill. Results should be verified by qualified researchers before "
        "use in clinical decision-making.\n"
    )

    markdown = "\n".join(sections)

    # ------------------------------------------------------------------ #
    # JSON export
    # ------------------------------------------------------------------ #
    json_outcomes = []
    for o in outcomes:
        json_outcomes.append({
            "name":          o.get("name", ""),
            "pooling":       o.get("pooling", {}),
            "heterogeneity": o.get("heterogeneity", {}),
            "sensitivity":   o.get("sensitivity", {}),
            "grade":         o.get("grade", {}),
        })

    json_export = {
        "pico":             pico,
        "search":           search,
        "prisma":           prisma_counts,
        "studies":          [
            s
            for o in outcomes
            for s in o.get("studies", [])
        ],
        "outcomes":         json_outcomes,
        "grade_summary":    [
            {
                "outcome":    o.get("name", ""),
                "certainty":  o.get("grade", {}).get("certainty", ""),
                "symbols":    o.get("grade", {}).get("certainty_symbols", ""),
            }
            for o in outcomes
        ],
        "publication_bias": publication_bias,
    }

    return {"markdown": markdown, "json": json_export}
