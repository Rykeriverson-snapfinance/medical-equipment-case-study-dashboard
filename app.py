from __future__ import annotations

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from data import (
    filter_data,
    funnel_summary,
    joined_repayment_data,
    load_application_data,
    load_repayment_data,
    monthly_funnel,
    repayment_by_grade,
    repayment_by_region,
    repayment_by_swap,
    repayment_status_summary,
    repayment_summary,
    risk_grade_summary,
    risk_migration_summary,
    source_metadata,
    swap_summary,
)


st.set_page_config(
    page_title="Medical Equipment Program Case Study",
    page_icon="bar_chart",
    layout="wide",
)


SNAP_BLUE = "#003767"
SNAP_BLUE_MED = "#335AAF"
SNAP_BLUE_LIGHT = "#5BC2E7"
SNAP_GREEN_DARK = "#006737"
SNAP_GREEN = "#8DC63F"
SNAP_ORANGE = "#FF7214"
SNAP_YELLOW = "#FFCB05"
SNAP_PURPLE = "#8651A1"
SNAP_GREY = "#696969"
SNAP_GREY_LIGHT = "#CCCCCC"
BACKGROUND = "#F8F8F8"
COLOR_SEQUENCE = [SNAP_BLUE, SNAP_BLUE_LIGHT, SNAP_GREEN, SNAP_YELLOW, SNAP_PURPLE]


def register_snap_theme() -> None:
    alt.themes.register(
        "snap",
        lambda: {
            "config": {
                "background": "#FFFFFF",
                "view": {"stroke": None},
                "axis": {
                    "labelColor": SNAP_GREY,
                    "titleColor": SNAP_GREY,
                    "gridColor": SNAP_GREY_LIGHT,
                    "domainColor": SNAP_GREY_LIGHT,
                    "labelFont": "Inter, Arial, sans-serif",
                    "titleFont": "Inter, Arial, sans-serif",
                },
                "legend": {
                    "labelColor": SNAP_GREY,
                    "titleColor": SNAP_GREY,
                    "labelFont": "Inter, Arial, sans-serif",
                    "titleFont": "Inter, Arial, sans-serif",
                },
                "title": {
                    "anchor": "start",
                    "color": SNAP_BLUE,
                    "font": "Inter, Arial, sans-serif",
                    "fontSize": 18,
                    "fontWeight": 700,
                },
                "range": {"category": COLOR_SEQUENCE},
            }
        },
    )
    alt.themes.enable("snap")


register_snap_theme()

st.markdown(
    f"""
    <style>
      .stApp {{ background: {BACKGROUND}; color: {SNAP_GREY}; font-family: Inter, Arial, sans-serif; }}
      .block-container {{ padding-top: 1.4rem; max-width: 1360px; }}
      h1, h2, h3 {{ color: {SNAP_BLUE}; letter-spacing: 0; }}
      h1 {{ font-size: 2rem; }}
      section[data-testid="stSidebar"] {{ background: #FFFFFF; border-right: 1px solid {SNAP_GREY_LIGHT}; }}
      div[data-testid="stMetric"] {{
        background: #FFFFFF;
        border: 1px solid {SNAP_GREY_LIGHT};
        border-left: 4px solid {SNAP_BLUE};
        border-radius: 5px;
        padding: 0.85rem 0.95rem;
        min-height: 94px;
      }}
      div[data-testid="stMetricValue"] {{ color: {SNAP_BLUE}; font-weight: 800; }}
      .snap-card {{
        background: #FFFFFF;
        border: 1px solid {SNAP_GREY_LIGHT};
        border-radius: 5px;
        padding: 1rem 1.1rem;
        margin-bottom: 1rem;
      }}
      .snap-callout {{
        background: #FFFFFF;
        border-left: 5px solid {SNAP_GREEN};
        border-radius: 5px;
        padding: 1rem 1.1rem;
        margin: 0.5rem 0 1rem 0;
      }}
      .snap-warning {{
        background: #FFFFFF;
        border-left: 5px solid {SNAP_ORANGE};
        border-radius: 5px;
        padding: 1rem 1.1rem;
        margin: 0.5rem 0 1rem 0;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)


def fmt_int(value: float) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{value:,.0f}"


def fmt_pct(value: float) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{value:.1%}"


def fmt_money(value: float) -> str:
    if pd.isna(value):
        return "N/A"
    return f"${value:,.0f}"


def fmt_multiple(value: float) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{value:.2f}x"


def format_table(
    frame: pd.DataFrame,
    money_cols=None,
    pct_cols=None,
    int_cols=None,
    multiple_cols=None,
) -> pd.DataFrame:
    result = frame.copy()
    for col in money_cols or []:
        if col in result:
            result[col] = result[col].map(fmt_money)
    for col in pct_cols or []:
        if col in result:
            result[col] = result[col].map(fmt_pct)
    for col in int_cols or []:
        if col in result:
            result[col] = result[col].map(fmt_int)
    for col in multiple_cols or []:
        if col in result:
            result[col] = result[col].map(fmt_multiple)
    return result


def funnel_chart(summary: dict[str, float]) -> alt.Chart:
    chart_data = pd.DataFrame(
        {
            "Step": [
                "Prequal applications",
                "Prequal approvals",
                "Full applications",
                "Final approvals",
                "Completed applications",
            ],
            "Applications": [
                summary["applications"],
                summary["prequal_approvals"],
                summary["full_applications"],
                summary["final_approvals"],
                summary["completed_applications"],
            ],
            "Color": [SNAP_BLUE, SNAP_BLUE_MED, SNAP_BLUE_LIGHT, SNAP_GREEN, SNAP_GREEN_DARK],
        }
    )
    bars = (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X("Step:N", sort=chart_data["Step"].tolist(), title=""),
            y=alt.Y("Applications:Q", title="Application count"),
            color=alt.Color("Step:N", scale=alt.Scale(range=chart_data["Color"].tolist()), legend=None),
            tooltip=["Step", alt.Tooltip("Applications:Q", format=",.0f")],
        )
        .properties(title="The Largest Funnel Leak Is Between Prequal Approval And Full Application", height=330)
    )
    labels = bars.mark_text(dy=-8, color=SNAP_GREY).encode(text=alt.Text("Applications:Q", format=",.0f"))
    return bars + labels


def monthly_chart(monthly: pd.DataFrame) -> alt.LayerChart:
    view = monthly.copy()
    view["Completion Rate"] = view["end_to_end_completion_rate"]
    bars = (
        alt.Chart(view)
        .mark_bar(color=SNAP_BLUE_LIGHT)
        .encode(
            x=alt.X("month:N", title="Prequal month"),
            y=alt.Y("applications:Q", title="Applications"),
            tooltip=[
                alt.Tooltip("month:N", title="Month"),
                alt.Tooltip("applications:Q", title="Applications", format=",.0f"),
                alt.Tooltip("Completion Rate:Q", title="Completion rate", format=".1%"),
            ],
        )
    )
    line = (
        alt.Chart(view)
        .mark_line(point=True, color=SNAP_ORANGE, strokeWidth=3)
        .encode(
            x=alt.X("month:N"),
            y=alt.Y("Completion Rate:Q", title="Completion rate", axis=alt.Axis(format="%")),
            tooltip=[
                alt.Tooltip("month:N", title="Month"),
                alt.Tooltip("Completion Rate:Q", title="Completion rate", format=".1%"),
            ],
        )
    )
    return (
        alt.layer(bars, line)
        .resolve_scale(y="independent")
        .properties(title="Application Demand Persisted, While Conversion Varied By Month", height=330)
    )


def swap_chart(swap: pd.DataFrame) -> alt.Chart:
    long = swap.melt(
        id_vars=["segment"],
        value_vars=[
            "continuation_rate",
            "final_approval_rate",
            "end_to_end_completion_rate",
            "floor_share",
        ],
        var_name="metric",
        value_name="rate",
    )
    long["metric"] = long["metric"].map(
        {
            "continuation_rate": "Continuation",
            "final_approval_rate": "Final approval",
            "end_to_end_completion_rate": "End-to-end completion",
            "floor_share": "$1,500 floor share",
        }
    )
    return (
        alt.Chart(long)
        .mark_bar()
        .encode(
            x=alt.X("metric:N", title=""),
            xOffset="segment:N",
            y=alt.Y("rate:Q", title="Rate", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])),
            color=alt.Color(
                "segment:N",
                title="Segment",
                scale=alt.Scale(domain=["Non-swap", "Swap-in"], range=[SNAP_BLUE, SNAP_ORANGE]),
            ),
            tooltip=[
                alt.Tooltip("metric:N", title="Metric"),
                alt.Tooltip("segment:N", title="Segment"),
                alt.Tooltip("rate:Q", title="Rate", format=".1%"),
            ],
        )
        .properties(title="Swap-In Applications Convert Better But Rely Heavily On The $1,500 Floor", height=330)
    )


def risk_migration_chart(migration: pd.DataFrame) -> alt.Chart:
    colors = {
        "Improved": SNAP_GREEN_DARK,
        "Same": SNAP_BLUE_LIGHT,
        "Worsened": SNAP_ORANGE,
        "No final grade": SNAP_GREY_LIGHT,
    }
    chart = (
        alt.Chart(migration)
        .mark_bar()
        .encode(
            x=alt.X("risk_grade_migration:N", title="Final vs prequal grade movement"),
            y=alt.Y("applications:Q", title="Full applications"),
            color=alt.Color(
                "risk_grade_migration:N",
                scale=alt.Scale(domain=list(colors.keys()), range=list(colors.values())),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("risk_grade_migration:N", title="Migration"),
                alt.Tooltip("applications:Q", title="Applications", format=",.0f"),
                alt.Tooltip("share:Q", title="Share", format=".1%"),
            ],
        )
        .properties(title="Most Full Applicants Looked The Same Or Less Risky After Full Application", height=330)
    )
    labels = chart.mark_text(dy=-8, color=SNAP_GREY).encode(text=alt.Text("share:Q", format=".1%"))
    return chart + labels


def grade_chart(grade: pd.DataFrame) -> alt.LayerChart:
    bars = (
        alt.Chart(grade)
        .mark_bar(color=SNAP_BLUE_LIGHT)
        .encode(
            x=alt.X("prequalification_risk_grade:N", title="Prequalification Risk Grade"),
            y=alt.Y("applications:Q", title="Applications"),
            tooltip=[
                alt.Tooltip("prequalification_risk_grade:N", title="Grade"),
                alt.Tooltip("applications:Q", title="Applications", format=",.0f"),
                alt.Tooltip("end_to_end_completion_rate:Q", title="Completion rate", format=".1%"),
            ],
        )
    )
    line = (
        alt.Chart(grade)
        .mark_line(point=True, color=SNAP_ORANGE, strokeWidth=3)
        .encode(
            x=alt.X("prequalification_risk_grade:N"),
            y=alt.Y(
                "end_to_end_completion_rate:Q",
                title="Completion rate",
                axis=alt.Axis(format="%"),
                scale=alt.Scale(domain=[0, 0.45]),
            ),
            tooltip=[
                alt.Tooltip("prequalification_risk_grade:N", title="Grade"),
                alt.Tooltip("end_to_end_completion_rate:Q", title="Completion rate", format=".1%"),
            ],
        )
    )
    return (
        alt.layer(bars, line)
        .resolve_scale(y="independent")
        .properties(title="Risk Grade F Carries The Most Volume But Lowest Conversion", height=330)
    )


def recommendation_chart(segments: pd.DataFrame) -> alt.Chart:
    colors = {
        "Expand selectively": SNAP_GREEN_DARK,
        "Monitor risk": SNAP_ORANGE,
        "Tighten or diagnose": SNAP_BLUE_MED,
        "Needs more volume": SNAP_GREY,
    }
    return (
        alt.Chart(segments)
        .mark_circle(opacity=0.82)
        .encode(
            x=alt.X("avg_prequal_risk_score:Q", title="Average prequal risk score"),
            y=alt.Y("completion_rate:Q", title="Completion rate", axis=alt.Axis(format="%")),
            size=alt.Size(
                "estimated_funded_amount:Q",
                title="Estimated funded amount",
                scale=alt.Scale(range=[80, 1100]),
            ),
            color=alt.Color(
                "management_read:N",
                title="Management read",
                scale=alt.Scale(domain=list(colors.keys()), range=list(colors.values())),
            ),
            tooltip=[
                alt.Tooltip("region:N", title="Region"),
                alt.Tooltip("merchant_id:N", title="Merchant ID"),
                alt.Tooltip("prequalification_risk_grade:N", title="Prequal grade"),
                alt.Tooltip("swap_in_status:N", title="Swap-in status"),
                alt.Tooltip("applications:Q", title="Applications", format=",.0f"),
                alt.Tooltip("estimated_funded_amount:Q", title="Estimated funded amount", format="$,.0f"),
                alt.Tooltip("avg_prequal_risk_score:Q", title="Avg prequal risk score", format=".3f"),
                alt.Tooltip("completion_rate:Q", title="Completion rate", format=".1%"),
                alt.Tooltip("management_read:N", title="Management read"),
            ],
        )
        .properties(title="Best Candidates Combine Volume, Conversion, And Lower Risk", height=420)
    )


def repayment_outcome_chart(repayment_swap: pd.DataFrame) -> alt.Chart:
    long = repayment_swap.melt(
        id_vars=["segment"],
        value_vars=[
            "missed_payment_day_45_rate",
            "no_payments_first_day_60_rate",
            "past_due_30_plus_day_120_rate",
            "charge_off_rate",
            "early_payoff_day_120_rate",
        ],
        var_name="metric",
        value_name="rate",
    )
    long["metric"] = long["metric"].map(
        {
            "missed_payment_day_45_rate": "Missed payment day 45",
            "no_payments_first_day_60_rate": "No payments day 60",
            "past_due_30_plus_day_120_rate": "30+ past due day 120",
            "charge_off_rate": "Charge-off",
            "early_payoff_day_120_rate": "Early payoff day 120",
        }
    )
    return (
        alt.Chart(long)
        .mark_bar()
        .encode(
            x=alt.X("metric:N", title="", axis=alt.Axis(labelAngle=-25)),
            xOffset="segment:N",
            y=alt.Y("rate:Q", title="Rate", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])),
            color=alt.Color(
                "segment:N",
                title="Segment",
                scale=alt.Scale(domain=["Non-swap", "Swap-in"], range=[SNAP_BLUE, SNAP_ORANGE]),
            ),
            tooltip=[
                alt.Tooltip("metric:N", title="Metric"),
                alt.Tooltip("segment:N", title="Segment"),
                alt.Tooltip("rate:Q", title="Rate", format=".1%"),
            ],
        )
        .properties(title="Repayment Outcome Rates By Swap-In Status", height=360)
    )


def repayment_payback_grade_chart(repayment_grade: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(repayment_grade)
        .mark_bar(color=SNAP_GREEN_DARK)
        .encode(
            x=alt.X("prequalification_risk_grade:N", title="Prequalification Risk Grade"),
            y=alt.Y("projected_payback_multiple:Q", title="Projected payback multiple"),
            tooltip=[
                alt.Tooltip("prequalification_risk_grade:N", title="Grade"),
                alt.Tooltip("accounts:Q", title="Accounts", format=",.0f"),
                alt.Tooltip("total_net_funded:Q", title="Net funded", format="$,.0f"),
                alt.Tooltip("projected_payback_multiple:Q", title="Payback multiple", format=".2f"),
                alt.Tooltip("charge_off_rate:Q", title="Charge-off rate", format=".1%"),
            ],
        )
        .properties(title="Projected Payback Multiple By Prequal Grade", height=360)
    )


def account_status_chart(status: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(status)
        .mark_bar(color=SNAP_BLUE_LIGHT)
        .encode(
            x=alt.X("account_status:N", title="Account status", sort="-y"),
            y=alt.Y("accounts:Q", title="Accounts"),
            tooltip=[
                alt.Tooltip("account_status:N", title="Status"),
                alt.Tooltip("accounts:Q", title="Accounts", format=",.0f"),
                alt.Tooltip("share:Q", title="Share", format=".1%"),
            ],
        )
        .properties(title="Repayment Account Status Mix", height=280)
    )


def repayment_region_chart(region: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(region)
        .mark_bar(color=SNAP_BLUE_LIGHT)
        .encode(
            x=alt.X("region:N", title="Region", sort="-y"),
            y=alt.Y("profit_proxy:Q", title="Profit proxy"),
            tooltip=[
                alt.Tooltip("region:N", title="Region"),
                alt.Tooltip("accounts:Q", title="Accounts", format=",.0f"),
                alt.Tooltip("profit_proxy:Q", title="Profit proxy", format="$,.0f"),
                alt.Tooltip("projected_payback_multiple:Q", title="Payback multiple", format=".2f"),
                alt.Tooltip("missed_payment_day_45_rate:Q", title="Missed payment day 45", format=".1%"),
                alt.Tooltip("charge_off_rate:Q", title="Charge-off rate", format=".1%"),
            ],
        )
        .properties(title="Repayment Profit Proxy By Region", height=300)
    )


def repayment_profit_grade_chart(repayment_grade: pd.DataFrame) -> alt.LayerChart:
    bars = (
        alt.Chart(repayment_grade)
        .mark_bar(color=SNAP_GREEN_DARK)
        .encode(
            x=alt.X("prequalification_risk_grade:N", title="Prequalification Risk Grade"),
            y=alt.Y("profit_proxy:Q", title="Profit proxy"),
            tooltip=[
                alt.Tooltip("prequalification_risk_grade:N", title="Grade"),
                alt.Tooltip("accounts:Q", title="Accounts", format=",.0f"),
                alt.Tooltip("profit_proxy:Q", title="Profit proxy", format="$,.0f"),
                alt.Tooltip("profit_proxy_per_account:Q", title="Profit per account", format="$,.0f"),
            ],
        )
    )
    line = (
        alt.Chart(repayment_grade)
        .mark_line(point=True, color=SNAP_ORANGE, strokeWidth=3)
        .encode(
            x=alt.X("prequalification_risk_grade:N"),
            y=alt.Y("charge_off_rate:Q", title="Charge-off rate", axis=alt.Axis(format="%")),
            tooltip=[
                alt.Tooltip("prequalification_risk_grade:N", title="Grade"),
                alt.Tooltip("charge_off_rate:Q", title="Charge-off rate", format=".1%"),
            ],
        )
    )
    return (
        alt.layer(bars, line)
        .resolve_scale(y="independent")
        .properties(title="Profit Proxy And Charge-Off Rate By Risk Grade", height=360)
    )


def risk_floor_chart(grade: pd.DataFrame) -> alt.LayerChart:
    view = grade.copy()
    view["$1,500 Floor Share"] = view["floor_share"]
    bars = (
        alt.Chart(view)
        .mark_bar(color=SNAP_BLUE_LIGHT)
        .encode(
            x=alt.X("prequalification_risk_grade:N", title="Prequalification Risk Grade"),
            y=alt.Y("applications:Q", title="Applications"),
            tooltip=[
                alt.Tooltip("prequalification_risk_grade:N", title="Grade"),
                alt.Tooltip("applications:Q", title="Applications", format=",.0f"),
                alt.Tooltip("floor_share:Q", title="$1,500 floor share", format=".1%"),
                alt.Tooltip("end_to_end_completion_rate:Q", title="Completion rate", format=".1%"),
            ],
        )
    )
    line = (
        alt.Chart(view)
        .mark_line(point=True, color=SNAP_ORANGE, strokeWidth=3)
        .encode(
            x=alt.X("prequalification_risk_grade:N"),
            y=alt.Y("$1,500 Floor Share:Q", title="$1,500 floor share", axis=alt.Axis(format="%")),
            tooltip=[
                alt.Tooltip("prequalification_risk_grade:N", title="Grade"),
                alt.Tooltip("$1,500 Floor Share:Q", title="$1,500 floor share", format=".1%"),
            ],
        )
    )
    return (
        alt.layer(bars, line)
        .resolve_scale(y="independent")
        .properties(title="Application Volume And Floor Usage By Risk Grade", height=360)
    )


def risk_outcome_grade_chart(risk_repayment: pd.DataFrame) -> alt.Chart:
    long = risk_repayment.melt(
        id_vars=["prequalification_risk_grade"],
        value_vars=[
            "end_to_end_completion_rate",
            "missed_payment_day_45_rate",
            "charge_off_rate",
        ],
        var_name="metric",
        value_name="rate",
    )
    long["metric"] = long["metric"].map(
        {
            "end_to_end_completion_rate": "Completion",
            "missed_payment_day_45_rate": "Missed pay day 45",
            "charge_off_rate": "Charge-off",
        }
    )
    return (
        alt.Chart(long)
        .mark_bar()
        .encode(
            x=alt.X("prequalification_risk_grade:N", title="Prequalification Risk Grade"),
            xOffset="metric:N",
            y=alt.Y("rate:Q", title="Rate", axis=alt.Axis(format="%")),
            color=alt.Color(
                "metric:N",
                title="Metric",
                scale=alt.Scale(
                    domain=["Completion", "Missed pay day 45", "Charge-off"],
                    range=[SNAP_GREEN_DARK, SNAP_ORANGE, SNAP_BLUE_MED],
                ),
            ),
            tooltip=[
                alt.Tooltip("prequalification_risk_grade:N", title="Grade"),
                alt.Tooltip("metric:N", title="Metric"),
                alt.Tooltip("rate:Q", title="Rate", format=".1%"),
            ],
        )
        .properties(title="Completion And Repayment Stress By Risk Grade", height=360)
    )


def render_metric_row(summary: dict[str, float]) -> None:
    cols = st.columns(5)
    cols[0].metric("Prequal applications", fmt_int(summary["applications"]))
    cols[1].metric("Prequal approval rate", fmt_pct(summary["prequal_approval_rate"]))
    cols[2].metric("Continuation rate", fmt_pct(summary["continuation_rate"]))
    cols[3].metric("Final approval rate", fmt_pct(summary["final_approval_rate"]))
    cols[4].metric("End-to-end completion", fmt_pct(summary["end_to_end_completion_rate"]))

    cols = st.columns(5)
    cols[0].metric("Completed applications", fmt_int(summary["completed_applications"]))
    cols[1].metric("Estimated funded amount", fmt_money(summary["estimated_funded_amount"]))
    cols[2].metric("Avg requested amount", fmt_money(summary["avg_requested_amount"]))
    cols[3].metric("Avg prequal approval", fmt_money(summary["avg_prequal_approval"]))
    cols[4].metric("Avg prequal risk score", f"{summary['avg_prequal_risk_score']:.3f}")


def render_funnel_overview_kpis(summary: dict[str, float]) -> None:
    avg_completed_ticket = (
        summary["estimated_funded_amount"] / summary["completed_applications"]
        if summary["completed_applications"]
        else pd.NA
    )

    cols = st.columns(4)
    cols[0].metric("Volume", fmt_int(summary["applications"]))
    cols[1].metric("Approval rate", fmt_pct(summary["prequal_approval_rate"]))
    cols[2].metric("Completion rate", fmt_pct(summary["end_to_end_completion_rate"]))
    cols[3].metric("Ticket size", fmt_money(avg_completed_ticket))


def render_repayment_metric_row(summary: dict[str, float]) -> None:
    cols = st.columns(5)
    cols[0].metric("Repayment accounts", fmt_int(summary["repayment_accounts"]))
    cols[1].metric("Repayment coverage", fmt_pct(summary["repayment_coverage_rate"]))
    cols[2].metric("Net funded", fmt_money(summary["total_net_funded"]))
    cols[3].metric("Projected paid", fmt_money(summary["total_projected_paid"]))
    cols[4].metric("Payback multiple", fmt_multiple(summary["projected_payback_multiple"]))

    cols = st.columns(5)
    cols[0].metric("Profit proxy", fmt_money(summary["profit_proxy"]))
    cols[1].metric("Missed pay day 45", fmt_pct(summary["missed_payment_day_45_rate"]))
    cols[2].metric("No payments day 60", fmt_pct(summary["no_payments_first_day_60_rate"]))
    cols[3].metric("30+ past due day 120", fmt_pct(summary["past_due_30_plus_day_120_rate"]))
    cols[4].metric("Charge-off rate", fmt_pct(summary["charge_off_rate"]))


def render_executive_kpis(
    summary: dict[str, float],
    repayment_metrics: dict[str, float] | None = None,
) -> None:
    cols = st.columns(3)
    cols[0].metric("Applications", fmt_int(summary["applications"]))
    cols[1].metric("Continuation rate", fmt_pct(summary["continuation_rate"]))
    cols[2].metric("Completed applications", fmt_int(summary["completed_applications"]))

    cols = st.columns(3)
    if repayment_metrics:
        cols[0].metric("Payback multiple", fmt_multiple(repayment_metrics["projected_payback_multiple"]))
        cols[1].metric("Profit proxy", fmt_money(repayment_metrics["profit_proxy"]))
        cols[2].metric("Charge-off rate", fmt_pct(repayment_metrics["charge_off_rate"]))
    else:
        cols[0].metric("Estimated funded amount", fmt_money(summary["estimated_funded_amount"]))
        cols[1].metric("Final approval rate", fmt_pct(summary["final_approval_rate"]))
        cols[2].metric("Avg prequal risk score", f"{summary['avg_prequal_risk_score']:.3f}")


def render_answer_cards() -> None:
    st.markdown(
        """
        <div class="snap-callout">
          <strong>Management answer:</strong> Keep the program, but keep it controlled. I would not shut it down,
          because the repayment read is positive and customers who finish the full application are usually approved.
          I also would not open it up everywhere yet, because the risk is concentrated in a few places that need
          tighter guardrails.
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            """
            <div class="snap-card">
              <strong>Why it is worth keeping</strong>
              <ul>
                <li>There is real application volume across the program.</li>
                <li>Once customers submit the full application, approvals are strong.</li>
                <li>Repayment records cover most completed accounts and show positive projected payback.</li>
                <li>Full-application data usually confirms or improves the risk read.</li>
              </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
            <div class="snap-card">
              <strong>Why I would not go broad yet</strong>
              <ul>
                <li>The biggest leak is still getting prequalified customers to continue.</li>
                <li>Swap-in accounts show more early repayment stress.</li>
                <li>Grade F brings volume, but it is also where the risk stacks up.</li>
                <li>The profit metric is still a proxy, not fully loaded margin.</li>
              </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_major_findings(
    summary: dict[str, float],
    repayment_metrics: dict[str, float],
    swap: pd.DataFrame,
    grade: pd.DataFrame,
    repayment_swap: pd.DataFrame,
    repayment_grade: pd.DataFrame,
) -> None:
    swap_in = swap[swap["segment"].eq("Swap-in")]
    non_swap = swap[swap["segment"].eq("Non-swap")]
    grade_f = grade[grade["prequalification_risk_grade"].eq("F")]
    repayment_f = repayment_grade[repayment_grade["prequalification_risk_grade"].eq("F")]
    repayment_swap_in = repayment_swap[repayment_swap["segment"].eq("Swap-in")]
    repayment_non_swap = repayment_swap[repayment_swap["segment"].eq("Non-swap")]

    swap_completion = swap_in["end_to_end_completion_rate"].iloc[0] if not swap_in.empty else pd.NA
    non_swap_completion = non_swap["end_to_end_completion_rate"].iloc[0] if not non_swap.empty else pd.NA
    grade_f_volume = grade_f["applications"].iloc[0] if not grade_f.empty else pd.NA
    grade_f_floor = grade_f["floor_share"].iloc[0] if not grade_f.empty else pd.NA
    grade_f_chargeoff = repayment_f["charge_off_rate"].iloc[0] if not repayment_f.empty else pd.NA
    swap_chargeoff = repayment_swap_in["charge_off_rate"].iloc[0] if not repayment_swap_in.empty else pd.NA
    non_swap_chargeoff = repayment_non_swap["charge_off_rate"].iloc[0] if not repayment_non_swap.empty else pd.NA

    st.markdown(
        f"""
        <div class="snap-card">
          <strong>The short version</strong>
          <ul>
            <li><strong>The demand is there:</strong> prequal approval is {fmt_pct(summary["prequal_approval_rate"])}, but only {fmt_pct(summary["continuation_rate"])} of approved customers move into a full application.</li>
            <li><strong>The economics look workable:</strong> matched repayment accounts show {fmt_money(repayment_metrics["total_net_funded"])} net funded and a {fmt_multiple(repayment_metrics["projected_payback_multiple"])} projected payback multiple.</li>
            <li><strong>The caution is specific:</strong> swap-in completes better than non-swap ({fmt_pct(swap_completion)} vs. {fmt_pct(non_swap_completion)}), but charge-off is higher ({fmt_pct(swap_chargeoff)} vs. {fmt_pct(non_swap_chargeoff)}).</li>
            <li><strong>The biggest risk pocket is grade F:</strong> it has {fmt_int(grade_f_volume)} applications, {fmt_pct(grade_f_floor)} floor usage, and {fmt_pct(grade_f_chargeoff)} charge-off in matched repayment accounts.</li>
          </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_management_recommendation(
    summary: dict[str, float],
    repayment_metrics: dict[str, float],
    swap: pd.DataFrame,
    grade: pd.DataFrame,
    repayment_swap: pd.DataFrame,
    repayment_grade: pd.DataFrame,
) -> None:
    swap_in = swap[swap["segment"].eq("Swap-in")]
    non_swap = swap[swap["segment"].eq("Non-swap")]
    repayment_swap_in = repayment_swap[repayment_swap["segment"].eq("Swap-in")]
    repayment_non_swap = repayment_swap[repayment_swap["segment"].eq("Non-swap")]
    grade_f = grade[grade["prequalification_risk_grade"].eq("F")]
    repayment_f = repayment_grade[repayment_grade["prequalification_risk_grade"].eq("F")]
    grade_e = repayment_grade[repayment_grade["prequalification_risk_grade"].eq("E")]

    swap_completion = swap_in["end_to_end_completion_rate"].iloc[0] if not swap_in.empty else pd.NA
    non_swap_completion = non_swap["end_to_end_completion_rate"].iloc[0] if not non_swap.empty else pd.NA
    swap_chargeoff = (
        repayment_swap_in["charge_off_rate"].iloc[0] if not repayment_swap_in.empty else pd.NA
    )
    non_swap_chargeoff = (
        repayment_non_swap["charge_off_rate"].iloc[0] if not repayment_non_swap.empty else pd.NA
    )
    grade_f_applications = grade_f["applications"].iloc[0] if not grade_f.empty else pd.NA
    grade_f_floor = grade_f["floor_share"].iloc[0] if not grade_f.empty else pd.NA
    grade_f_chargeoff = repayment_f["charge_off_rate"].iloc[0] if not repayment_f.empty else pd.NA
    grade_e_payback = grade_e["projected_payback_multiple"].iloc[0] if not grade_e.empty else pd.NA

    st.subheader("Overall Recommendation To Management")
    st.markdown(
        f"""
        <div class="snap-callout">
          <strong>Clear answer:</strong> continue the program, but do it selectively. The data does not argue
          for shutting it down: repayment shows a {fmt_multiple(repayment_metrics["projected_payback_multiple"])}
          projected payback multiple and {fmt_money(repayment_metrics["profit_proxy"])} profit proxy. It also
          does not support a wide-open rollout yet, because continuation is only {fmt_pct(summary["continuation_rate"])}
          and the risk is concentrated in swap-in and lower-grade applicants.
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f"""
            <div class="snap-card">
              <strong>Decision</strong>
              <p>Keep going, but scale in lanes where conversion and repayment both look healthy.</p>
              <p><strong>Do not</strong> treat this as a blanket policy expansion yet.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="snap-card">
              <strong>Why that is the middle answer</strong>
              <p>The program has demand and positive payback, but the weak point is customer follow-through:
              {fmt_pct(summary["continuation_rate"])} continuation after prequal approval.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
            <div class="snap-card">
              <strong>Main guardrail</strong>
              <p>Watch swap-in and grade F closely. Swap-in charge-off is {fmt_pct(swap_chargeoff)} vs.
              {fmt_pct(non_swap_chargeoff)} for non-swap, and grade F charge-off is {fmt_pct(grade_f_chargeoff)}.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    c1, c2 = st.columns([1, 1])
    with c1:
        st.altair_chart(funnel_chart(summary), use_container_width=True)
    with c2:
        st.altair_chart(repayment_profit_grade_chart(repayment_grade), use_container_width=True)

    c1, c2 = st.columns([1, 1])
    with c1:
        st.altair_chart(repayment_outcome_chart(repayment_swap), use_container_width=True)
    with c2:
        st.altair_chart(swap_chart(swap), use_container_width=True)

    action_plan = pd.DataFrame(
        [
            {
                "Management Area": "Program decision",
                "What I would do": "Continue, but expand selectively",
                "Why": f"Payback is {fmt_multiple(repayment_metrics['projected_payback_multiple'])}, but risk is not even across the book.",
            },
            {
                "Management Area": "Growth",
                "What I would do": "Fix continuation before chasing more top-of-funnel volume",
                "Why": f"Only {fmt_pct(summary['continuation_rate'])} of prequal-approved customers continue to full application.",
            },
            {
                "Management Area": "Underwriting",
                "What I would do": "Keep swap-in as an exception lane with tighter monitoring",
                "Why": f"Swap-in completes at {fmt_pct(swap_completion)} vs. {fmt_pct(non_swap_completion)} for non-swap, but charge-off is higher.",
            },
            {
                "Management Area": "Risk policy",
                "What I would do": "Review grade F and floor-heavy approvals before broad rollout",
                "Why": f"Grade F has {fmt_int(grade_f_applications)} applications, {fmt_pct(grade_f_floor)} floor usage, and {fmt_pct(grade_f_chargeoff)} charge-off.",
            },
            {
                "Management Area": "Profitability",
                "What I would do": "Move from profit proxy to fully loaded margin before a final scale decision",
                "Why": f"Grade E payback is only {fmt_multiple(grade_e_payback)}, and current profit excludes servicing cost, cost of capital, and realized losses.",
            },
        ]
    )
    st.dataframe(action_plan, hide_index=True, use_container_width=True)


def render_repayment_profitability_answer(
    repayment_metrics: dict[str, float],
    repayment_grade: pd.DataFrame,
    repayment_swap: pd.DataFrame,
    repayment_region: pd.DataFrame,
    repayment_status: pd.DataFrame,
) -> None:
    paid_active_share = repayment_status[
        repayment_status["account_status"].isin(["ACTIVE", "PAID"])
    ]["share"].sum()
    grade_e = repayment_grade[repayment_grade["prequalification_risk_grade"].eq("E")]
    grade_f = repayment_grade[repayment_grade["prequalification_risk_grade"].eq("F")]
    swap_in = repayment_swap[repayment_swap["segment"].eq("Swap-in")]
    non_swap = repayment_swap[repayment_swap["segment"].eq("Non-swap")]

    grade_e_payback = grade_e["projected_payback_multiple"].iloc[0] if not grade_e.empty else pd.NA
    grade_e_profit = grade_e["profit_proxy_per_account"].iloc[0] if not grade_e.empty else pd.NA
    grade_f_chargeoff = grade_f["charge_off_rate"].iloc[0] if not grade_f.empty else pd.NA
    swap_missed = swap_in["missed_payment_day_45_rate"].iloc[0] if not swap_in.empty else pd.NA
    non_swap_missed = non_swap["missed_payment_day_45_rate"].iloc[0] if not non_swap.empty else pd.NA
    swap_chargeoff = swap_in["charge_off_rate"].iloc[0] if not swap_in.empty else pd.NA
    non_swap_chargeoff = non_swap["charge_off_rate"].iloc[0] if not non_swap.empty else pd.NA

    st.subheader("Repayment Metrics And Profitability")
    st.markdown(
        f"""
        <div class="snap-callout">
          <strong>Simple answer:</strong> repayment looks good enough to keep testing, but not good enough
          to remove the guardrails. Matched accounts show {fmt_money(repayment_metrics["total_net_funded"])}
          net funded, {fmt_money(repayment_metrics["total_projected_paid"])} projected paid, and a
          {fmt_multiple(repayment_metrics["projected_payback_multiple"])} payback multiple. That leaves
          {fmt_money(repayment_metrics["profit_proxy"])} of profit proxy before fully loaded costs.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="snap-card">
          <strong>What I take from the repayment data</strong>
          <ul>
            <li>{fmt_pct(paid_active_share)} of matched accounts are active or paid, while charge-offs are {fmt_pct(repayment_metrics["charge_off_rate"])}.</li>
            <li>Swap-in does not look broken, but it is noisier early: missed payment at day 45 is {fmt_pct(swap_missed)} vs. {fmt_pct(non_swap_missed)} for non-swap, and charge-off is {fmt_pct(swap_chargeoff)} vs. {fmt_pct(non_swap_chargeoff)}.</li>
            <li>Grade E is the weakest profitability pocket, with {fmt_multiple(grade_e_payback)} payback and {fmt_money(grade_e_profit)} profit proxy per account.</li>
            <li>Grade F still matters because it has volume, but it is also carrying the highest charge-off pressure at {fmt_pct(grade_f_chargeoff)}.</li>
          </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        st.altair_chart(repayment_profit_grade_chart(repayment_grade), use_container_width=True)
    with c2:
        st.altair_chart(repayment_outcome_chart(repayment_swap), use_container_width=True)

    c1, c2 = st.columns([1, 1])
    with c1:
        st.altair_chart(repayment_region_chart(repayment_region), use_container_width=True)
    with c2:
        st.altair_chart(account_status_chart(repayment_status), use_container_width=True)

    grade_profit_table = repayment_grade[
        [
            "prequalification_risk_grade",
            "accounts",
            "total_net_funded",
            "projected_payback_multiple",
            "profit_proxy",
            "profit_proxy_per_account",
            "missed_payment_day_45_rate",
            "charge_off_rate",
        ]
    ].rename(
        columns={
            "prequalification_risk_grade": "Prequal Grade",
            "accounts": "Accounts",
            "total_net_funded": "Net Funded",
            "projected_payback_multiple": "Payback Multiple",
            "profit_proxy": "Profit Proxy",
            "profit_proxy_per_account": "Profit Proxy Per Account",
            "missed_payment_day_45_rate": "Missed Payment Day 45",
            "charge_off_rate": "Charge-Off Rate",
        }
    )
    st.dataframe(
        format_table(
            grade_profit_table,
            money_cols=["Net Funded", "Profit Proxy", "Profit Proxy Per Account"],
            multiple_cols=["Payback Multiple"],
            pct_cols=["Missed Payment Day 45", "Charge-Off Rate"],
            int_cols=["Accounts"],
        ),
        hide_index=True,
        use_container_width=True,
    )


def render_risk_profile_answer(
    grade: pd.DataFrame,
    repayment_grade: pd.DataFrame,
    migration: pd.DataFrame,
    swap: pd.DataFrame,
    repayment_swap: pd.DataFrame,
) -> None:
    risk_repayment = grade.merge(
        repayment_grade[
            [
                "prequalification_risk_grade",
                "accounts",
                "missed_payment_day_45_rate",
                "charge_off_rate",
                "projected_payback_multiple",
                "profit_proxy_per_account",
            ]
        ],
        on="prequalification_risk_grade",
        how="left",
    )
    grade_f = risk_repayment[risk_repayment["prequalification_risk_grade"].eq("F")]
    improved = migration[migration["risk_grade_migration"].eq("Improved")]
    same = migration[migration["risk_grade_migration"].eq("Same")]
    worsened = migration[migration["risk_grade_migration"].eq("Worsened")]
    swap_in = swap[swap["segment"].eq("Swap-in")]
    repayment_swap_in = repayment_swap[repayment_swap["segment"].eq("Swap-in")]

    grade_f_applications = grade_f["applications"].iloc[0] if not grade_f.empty else pd.NA
    grade_f_completion = grade_f["end_to_end_completion_rate"].iloc[0] if not grade_f.empty else pd.NA
    grade_f_floor = grade_f["floor_share"].iloc[0] if not grade_f.empty else pd.NA
    grade_f_chargeoff = grade_f["charge_off_rate"].iloc[0] if not grade_f.empty else pd.NA
    improved_share = improved["share"].iloc[0] if not improved.empty else pd.NA
    same_share = same["share"].iloc[0] if not same.empty else pd.NA
    worsened_share = worsened["share"].iloc[0] if not worsened.empty else pd.NA
    swap_floor = swap_in["floor_share"].iloc[0] if not swap_in.empty else pd.NA
    swap_chargeoff = repayment_swap_in["charge_off_rate"].iloc[0] if not repayment_swap_in.empty else pd.NA

    st.subheader("Risk Profile Of Applicants")
    st.markdown(
        f"""
        <div class="snap-callout">
          <strong>Simple answer:</strong> this is not a uniformly risky program. The risk is clustered.
          Grade F is the clearest pressure point: {fmt_int(grade_f_applications)} applications,
          {fmt_pct(grade_f_floor)} using the $1,500 floor, {fmt_pct(grade_f_completion)} end-to-end completion,
          and {fmt_pct(grade_f_chargeoff)} charge-off among matched repayment accounts.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="snap-card">
          <strong>What changes after the full application?</strong>
          <ul>
            <li>For applicants who reached the full application, risk usually looked better: {fmt_pct(improved_share)} improved and {fmt_pct(same_share)} stayed the same.</li>
            <li>Only {fmt_pct(worsened_share)} worsened, which suggests the full application is helping sharpen the risk read.</li>
            <li>Swap-in should stay as a monitored exception lane. It has {fmt_pct(swap_floor)} floor usage and {fmt_pct(swap_chargeoff)} charge-off.</li>
          </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        st.altair_chart(risk_floor_chart(grade), use_container_width=True)
    with c2:
        st.altair_chart(risk_outcome_grade_chart(risk_repayment), use_container_width=True)

    c1, c2 = st.columns([1, 1])
    with c1:
        st.altair_chart(risk_migration_chart(migration), use_container_width=True)
    with c2:
        st.altair_chart(swap_chart(swap), use_container_width=True)

    risk_table = risk_repayment[
        [
            "prequalification_risk_grade",
            "applications",
            "prequal_approval_rate",
            "end_to_end_completion_rate",
            "floor_share",
            "avg_underwriting_lift",
            "missed_payment_day_45_rate",
            "charge_off_rate",
            "projected_payback_multiple",
        ]
    ].rename(
        columns={
            "prequalification_risk_grade": "Prequal Grade",
            "applications": "Applications",
            "prequal_approval_rate": "Prequal Approval Rate",
            "end_to_end_completion_rate": "Completion Rate",
            "floor_share": "$1,500 Floor Share",
            "avg_underwriting_lift": "Avg Underwriting Lift",
            "missed_payment_day_45_rate": "Missed Payment Day 45",
            "charge_off_rate": "Charge-Off Rate",
            "projected_payback_multiple": "Payback Multiple",
        }
    )
    st.dataframe(
        format_table(
            risk_table,
            money_cols=["Avg Underwriting Lift"],
            multiple_cols=["Payback Multiple"],
            pct_cols=[
                "Prequal Approval Rate",
                "Completion Rate",
                "$1,500 Floor Share",
                "Missed Payment Day 45",
                "Charge-Off Rate",
            ],
            int_cols=["Applications"],
        ),
        hide_index=True,
        use_container_width=True,
    )


def render_source_banner(data: pd.DataFrame) -> None:
    metadata = source_metadata(data)
    st.caption(
        "Data source: local application and repayment CSVs | "
        f"Date basis: prequalification submit date, {metadata['date_start']} to {metadata['date_end']} | "
        f"Rows: {metadata['rows']} | Merchants: {metadata['merchants']} | Regions: {metadata['regions']}"
    )


data = load_application_data()
repayment = load_repayment_data()
metadata = source_metadata(data)

with st.sidebar:
    st.header("Filters")
    min_date = data["prequal_submit_dt"].min().date()
    max_date = data["prequal_submit_dt"].max().date()
    selected_dates = st.date_input(
        "Prequal Submit Date",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if len(selected_dates) != 2:
        st.warning("Select a start and end date.")
        st.stop()

    region_options = sorted(data["region"].dropna().unique().tolist())
    selected_regions = st.multiselect("Region", region_options, default=region_options)

    grade_options = [
        grade
        for grade in ["A", "B", "C", "D", "E", "F", "G"]
        if grade in set(data["prequalification_risk_grade"])
    ]
    selected_grades = st.multiselect("Prequalification Risk Grade", grade_options, default=grade_options)

    swap_label_to_value = {"Non-swap": False, "Swap-in": True}
    selected_swap_labels = st.multiselect(
        "Swap-In Approval",
        list(swap_label_to_value.keys()),
        default=list(swap_label_to_value.keys()),
    )
    selected_swap_values = [swap_label_to_value[label] for label in selected_swap_labels]

    merchant_options = sorted(data["merchant_id"].dropna().astype(int).unique().tolist())
    selected_merchants = st.multiselect("Merchant ID", merchant_options, default=merchant_options)

    st.divider()
    st.caption("Use filters to see whether the recommendation changes by region, merchant, grade, or swap-in status.")

filtered = filter_data(
    data,
    selected_regions,
    selected_merchants,
    selected_grades,
    selected_swap_values,
    (pd.Timestamp(selected_dates[0]), pd.Timestamp(selected_dates[1])),
)

if filtered.empty:
    st.title("Medical Equipment Financing Program Case Study")
    render_source_banner(data)
    st.info("No records match the selected filters.")
    st.stop()

summary = funnel_summary(filtered)
repayment_filtered = joined_repayment_data(filtered, repayment)
repayment_metrics = repayment_summary(repayment_filtered, int(summary["completed_applications"]))
repayment_swap = repayment_by_swap(repayment_filtered) if not repayment_filtered.empty else pd.DataFrame()
repayment_grade = repayment_by_grade(repayment_filtered) if not repayment_filtered.empty else pd.DataFrame()
repayment_region = repayment_by_region(repayment_filtered) if not repayment_filtered.empty else pd.DataFrame()
repayment_status = repayment_status_summary(repayment_filtered) if not repayment_filtered.empty else pd.DataFrame()
monthly = monthly_funnel(filtered)
swap = swap_summary(filtered)
grade = risk_grade_summary(filtered)
migration = risk_migration_summary(filtered)

st.title("Medical Equipment Financing Program Case Study")
st.markdown(
    "A management read on whether this financing program is worth continuing, where it is working, and where it needs guardrails."
)
render_source_banner(data)

tabs = st.tabs(
    [
        "Executive Answer",
        "Funnel",
        "Special Underwriting",
        "Risk Deep Dive",
        "Repayment & Profitability",
        "Management Recommendation",
        "Remaining Caveats",
        "Appendix",
    ]
)

with tabs[0]:
    render_executive_kpis(summary, repayment_metrics if not repayment_filtered.empty else None)
    if not repayment_filtered.empty:
        render_major_findings(summary, repayment_metrics, swap, grade, repayment_swap, repayment_grade)
    render_answer_cards()
    st.altair_chart(funnel_chart(summary), use_container_width=True)

with tabs[1]:
    st.subheader("Program Funnel")
    st.markdown(
        "The funnel is strongest after a customer submits the full application. The bigger opportunity is earlier: getting more prequalified customers to keep going."
    )
    render_funnel_overview_kpis(summary)
    col1, col2 = st.columns([1, 1])
    with col1:
        st.altair_chart(funnel_chart(summary), use_container_width=True)
    with col2:
        st.altair_chart(monthly_chart(monthly), use_container_width=True)

    funnel_table = monthly[
        [
            "month",
            "applications",
            "prequal_approval_rate",
            "continuation_rate",
            "final_approval_rate",
            "completion_after_approval_rate",
            "end_to_end_completion_rate",
            "avg_requested_amount",
            "avg_prequal_approval",
            "avg_final_approval",
        ]
    ].rename(
        columns={
            "month": "Month",
            "applications": "Applications",
            "prequal_approval_rate": "Prequal Approval Rate",
            "continuation_rate": "Continuation Rate",
            "final_approval_rate": "Final Approval Rate",
            "completion_after_approval_rate": "Completion After Approval",
            "end_to_end_completion_rate": "End-To-End Completion",
            "avg_requested_amount": "Avg Requested Amount",
            "avg_prequal_approval": "Avg Prequal Approval",
            "avg_final_approval": "Avg Final Approval",
        }
    )
    st.dataframe(
        format_table(
            funnel_table,
            money_cols=["Avg Requested Amount", "Avg Prequal Approval", "Avg Final Approval"],
            pct_cols=[
                "Prequal Approval Rate",
                "Continuation Rate",
                "Final Approval Rate",
                "Completion After Approval",
                "End-To-End Completion",
            ],
            int_cols=["Applications"],
        ),
        hide_index=True,
        use_container_width=True,
    )

with tabs[2]:
    st.subheader("Swap-In And Special Underwriting Logic")
    st.markdown(
        "Swap-in helps more customers get through the process, but it also brings more risk. The $1,500 floor is the clearest place where that tradeoff shows up."
    )
    c1, c2 = st.columns([1, 1])
    with c1:
        st.altair_chart(swap_chart(swap), use_container_width=True)
    with c2:
        risk_amount = swap[
            [
                "segment",
                "avg_prequal_risk_score",
                "avg_final_risk_score",
                "avg_actual_prequal_approval",
                "avg_underwriting_lift",
                "estimated_funded_amount",
            ]
        ].rename(
            columns={
                "segment": "Segment",
                "avg_prequal_risk_score": "Avg Prequal Risk Score",
                "avg_final_risk_score": "Avg Final Risk Score",
                "avg_actual_prequal_approval": "Avg Prequal Approval",
                "avg_underwriting_lift": "Avg Underwriting Lift",
                "estimated_funded_amount": "Estimated Funded Amount",
            }
        )
        st.dataframe(
            format_table(
                risk_amount,
                money_cols=["Avg Prequal Approval", "Avg Underwriting Lift", "Estimated Funded Amount"],
            ),
            hide_index=True,
            use_container_width=True,
        )

    st.markdown(
        """
        <div class="snap-warning">
          <strong>Management read:</strong> use swap-in as a controlled growth lever, not as standard policy.
          The repayment tab adds the account outcome view, but projected paid amount is still a proxy rather
          than fully loaded profitability.
        </div>
        """,
        unsafe_allow_html=True,
    )

with tabs[3]:
    if repayment_filtered.empty:
        st.subheader("Risk Profile Of Applicants")
        st.info("No repayment records match the selected filters, so the risk profile cannot be tied to repayment outcomes yet.")
    else:
        render_risk_profile_answer(grade, repayment_grade, migration, swap, repayment_swap)

with tabs[4]:
    if repayment_filtered.empty:
        st.subheader("Repayment Metrics And Profitability")
        st.info("No repayment records match the selected filters.")
    else:
        render_repayment_profitability_answer(
            repayment_metrics,
            repayment_grade,
            repayment_swap,
            repayment_region,
            repayment_status,
        )

        st.download_button(
            "Download Filtered Repayment Data",
            data=repayment_filtered.to_csv(index=False),
            file_name="case_study_filtered_repayment_data.csv",
            mime="text/csv",
        )

with tabs[5]:
    if repayment_filtered.empty:
        st.subheader("Overall Recommendation To Management")
        st.info("No repayment records match the selected filters, so the recommendation cannot include account outcomes yet.")
    else:
        render_management_recommendation(
            summary,
            repayment_metrics,
            swap,
            grade,
            repayment_swap,
            repayment_grade,
        )

with tabs[6]:
    st.subheader("What We Still Need To Know")
    st.markdown(
        """
        <div class="snap-warning">
          <strong>Main caveat:</strong> the repayment file makes the recommendation much stronger, but profit
          proxy is still not the same as final margin. It does not include cost of capital, servicing expense,
          loss timing, recoveries, or a clean standard-policy comparison.
        </div>
        """,
        unsafe_allow_html=True,
    )
    unanswered = pd.DataFrame(
        [
            {
                "Instruction Area": "Repayment metrics",
                "Status": "Answered for matched accounts",
                "Reason": "Repayment data now includes missed payment, no-payment, past-due, early payoff, charge-off, and account status fields.",
            },
            {
                "Instruction Area": "Profitability",
                "Status": "Partially answered",
                "Reason": "Projected amount paid less net funded amount is a useful proxy, but not fully loaded margin.",
            },
            {
                "Instruction Area": "True ticket size",
                "Status": "Answered for matched accounts",
                "Reason": "Repayment records include net funded amount for completed applications with repayment coverage.",
            },
            {
                "Instruction Area": "Approval amount increase at full application",
                "Status": "Not supported by this file",
                "Reason": "For full applications, final approval amount equals prequalification actual approval amount in the raw data.",
            },
            {
                "Instruction Area": "Cohort performance maturity",
                "Status": "Partially answered",
                "Reason": "Repayment fields include fixed day-45, day-60, day-90, day-120, and day-180 observations, but no funded date for vintage seasoning.",
            },
            {
                "Instruction Area": "Comparison to replacement financier",
                "Status": "Not answered",
                "Reason": "The dataset only contains Snap application records and has no control or competitor performance data.",
            },
            {
                "Instruction Area": "Exact counterfactual of standard underwriting",
                "Status": "Partially answered",
                "Reason": "Risk-based amount versus actual approval amount estimates floor impact, but there is no full standard-policy simulation.",
            },
        ]
    )
    st.dataframe(unanswered, hide_index=True, use_container_width=True)

    st.subheader("Best Follow-Up Data To Ask For")
    st.markdown(
        """
        To turn this from a strong directional recommendation into a full scale/no-scale decision, ask for:

        - Funded date and contractual first-payment date
        - Realized amount paid, revenue, fees, loss amount, recoveries, and servicing cost
        - Charge-off date and charge-off amount
        - Missed payment or first-payment-default flags at 30, 45, and 60 days
        - Past-due dollars at 90, 120, and 180 days
        - Standard-policy approval amount or decision counterfactual
        """
    )

with tabs[7]:
    st.subheader("Appendix")
    st.markdown(
        f"""
        **Report:** Medical Equipment Financing Program Case Study  
        **Prepared for:** Snap Finance management case study review  
        **As of:** source extract in package; date range {metadata['date_start']} to {metadata['date_end']}  
        **Data sources:** `data/case_study_dataset.csv`; `data/repayment_results.csv`  
        **Refresh cadence:** Ad hoc case study extract  
        **Row grain:** One prequalification application record; one repayment record per funded account in the repayment extract

        **Metric definitions:** Prequal approval rate is prequal approvals divided by applications.
        Continuation rate is full applications divided by prequal approvals. Final approval rate is final
        approvals divided by full applications. End-to-end completion is completed applications divided by
        applications. Repayment coverage is matched repayment accounts divided by completed applications.
        Profit proxy is projected amount paid minus net funded amount. Projected payback multiple is projected
        amount paid divided by net funded amount.
        """
    )

    query_path = Path(__file__).parent / "queries" / "case_study_reference.sql"
    if query_path.exists():
        with st.expander("Reference SQL Outline"):
            st.code(query_path.read_text(), language="sql")

    with st.expander("Raw Data Preview"):
        st.dataframe(filtered.head(200), hide_index=True, use_container_width=True)

    with st.expander("Repayment Data Preview"):
        st.dataframe(repayment_filtered.head(200), hide_index=True, use_container_width=True)

    st.download_button(
        "Download Filtered Raw Data",
        data=filtered.to_csv(index=False),
        file_name="case_study_filtered_raw_data.csv",
        mime="text/csv",
    )
