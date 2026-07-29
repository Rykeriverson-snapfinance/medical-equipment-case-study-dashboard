from __future__ import annotations

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from data import (
    filter_data,
    funnel_summary,
    load_application_data,
    merchant_segments,
    monthly_funnel,
    recommendation_segments,
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


def format_table(frame: pd.DataFrame, money_cols=None, pct_cols=None, int_cols=None) -> pd.DataFrame:
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


def render_answer_cards() -> None:
    st.markdown(
        """
        <div class="snap-callout">
          <strong>Management answer:</strong> Continue the program selectively, but do not expand broadly
          until repayment and profitability data are available. The funnel shows real demand and strong final
          approval once customers complete the full application. The risk tradeoff is concentrated in swap-in
          and F-grade applications, where the $1,500 floor is doing most of the underwriting work.
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            """
            <div class="snap-card">
              <strong>What looks positive</strong>
              <ul>
                <li>Demand exists across regions and merchants.</li>
                <li>Prequal approval is high and final approval is very strong after full application.</li>
                <li>Most applicants with full-app data show improved or unchanged risk grade.</li>
                <li>Swap-in logic appears to preserve incremental volume from advocate stores.</li>
              </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
            <div class="snap-card">
              <strong>What needs caution</strong>
              <ul>
                <li>The biggest leak is continuation from prequal approval to full application.</li>
                <li>Swap-in applicants are riskier and more dependent on the $1,500 floor.</li>
                <li>Grade F has large volume but weaker conversion.</li>
                <li>The current file cannot prove repayment performance or profitability.</li>
              </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_source_banner(data: pd.DataFrame) -> None:
    metadata = source_metadata(data)
    st.caption(
        "Data source: local case study CSV | "
        f"Date basis: prequalification submit date, {metadata['date_start']} to {metadata['date_end']} | "
        f"Rows: {metadata['rows']} | Merchants: {metadata['merchants']} | Regions: {metadata['regions']}"
    )


data = load_application_data()
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

    min_segment_volume = st.slider(
        "Minimum Applications For Segment Tables",
        min_value=1,
        max_value=25,
        value=5,
        step=1,
    )

    st.divider()
    st.caption("Use filters to stress-test whether the recommendation changes by region, merchant, grade, or swap-in status.")

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
monthly = monthly_funnel(filtered)
swap = swap_summary(filtered)
grade = risk_grade_summary(filtered)
migration = risk_migration_summary(filtered)
merchants = merchant_segments(filtered)
segments = recommendation_segments(filtered, min_applications=min_segment_volume)

st.title("Medical Equipment Financing Program Case Study")
st.markdown(
    "Management Dashboard For Evaluating Snap's Prequalification-Based Financing Program, Special Underwriting Logic, And Recommended Next Steps."
)
render_source_banner(data)

tabs = st.tabs(
    [
        "Executive Answer",
        "Funnel",
        "Special Underwriting",
        "Risk Profile",
        "Recommendation Detail",
        "Data Gaps",
        "Appendix",
    ]
)

with tabs[0]:
    render_metric_row(summary)
    render_answer_cards()
    st.altair_chart(funnel_chart(summary), use_container_width=True)

with tabs[1]:
    st.subheader("Program Funnel")
    st.markdown(
        "The strongest funnel point is final approval after a customer submits the full application. The main opportunity is earlier: moving more prequalified customers into full applications."
    )
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
        "Swap-in applications have higher completion but higher risk. The $1,500 floor is the clearest measurable effect of the special underwriting logic in this dataset."
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
          <strong>Interpretation:</strong> swap-in logic should be treated as incremental growth with a guardrail,
          not as proof that looser underwriting is profitable. The application data shows higher completion, but
          repayment data is required before calling the economics positive.
        </div>
        """,
        unsafe_allow_html=True,
    )

with tabs[3]:
    st.subheader("Applicant Risk Profile")
    c1, c2 = st.columns([1, 1])
    with c1:
        st.altair_chart(risk_migration_chart(migration), use_container_width=True)
    with c2:
        st.altair_chart(grade_chart(grade), use_container_width=True)

    grade_table = grade[
        [
            "prequalification_risk_grade",
            "applications",
            "prequal_approval_rate",
            "continuation_rate",
            "final_approval_rate",
            "end_to_end_completion_rate",
            "swap_in_share",
            "floor_share",
            "avg_prequal_risk_score",
            "avg_underwriting_lift",
            "estimated_funded_amount",
        ]
    ].rename(
        columns={
            "prequalification_risk_grade": "Prequal Grade",
            "applications": "Applications",
            "prequal_approval_rate": "Prequal Approval Rate",
            "continuation_rate": "Continuation Rate",
            "final_approval_rate": "Final Approval Rate",
            "end_to_end_completion_rate": "End-To-End Completion",
            "swap_in_share": "Swap-In Share",
            "floor_share": "$1,500 Floor Share",
            "avg_prequal_risk_score": "Avg Prequal Risk Score",
            "avg_underwriting_lift": "Avg Underwriting Lift",
            "estimated_funded_amount": "Estimated Funded Amount",
        }
    )
    st.dataframe(
        format_table(
            grade_table,
            money_cols=["Avg Underwriting Lift", "Estimated Funded Amount"],
            pct_cols=[
                "Prequal Approval Rate",
                "Continuation Rate",
                "Final Approval Rate",
                "End-To-End Completion",
                "Swap-In Share",
                "$1,500 Floor Share",
            ],
            int_cols=["Applications"],
        ),
        hide_index=True,
        use_container_width=True,
    )

with tabs[4]:
    st.subheader("Segment Recommendation Detail")
    st.markdown(
        "Segments are grouped by region, merchant, prequalification risk grade, and swap-in status. Because repayment and profitability fields are unavailable, the recommendation uses estimated funded volume, conversion, and risk as proxies."
    )

    if segments.empty:
        st.info("No segment has enough applications for the selected minimum volume.")
    else:
        st.altair_chart(recommendation_chart(segments), use_container_width=True)

        recommendation_table = segments[
            [
                "management_read",
                "region",
                "merchant_id",
                "prequalification_risk_grade",
                "swap_in_status",
                "applications",
                "completed_accounts",
                "completion_rate",
                "estimated_funded_amount",
                "avg_completed_ticket_size",
                "avg_prequal_risk_score",
                "avg_final_risk_score",
                "floor_share",
            ]
        ].rename(
            columns={
                "management_read": "Management Read",
                "region": "Region",
                "merchant_id": "Merchant ID",
                "prequalification_risk_grade": "Prequal Grade",
                "swap_in_status": "Swap-In Status",
                "applications": "Applications",
                "completed_accounts": "Completed Accounts",
                "completion_rate": "Completion Rate",
                "estimated_funded_amount": "Estimated Funded Amount",
                "avg_completed_ticket_size": "Avg Completed Ticket Size",
                "avg_prequal_risk_score": "Avg Prequal Risk Score",
                "avg_final_risk_score": "Avg Final Risk Score",
                "floor_share": "$1,500 Floor Share",
            }
        )
        st.dataframe(
            format_table(
                recommendation_table,
                money_cols=["Estimated Funded Amount", "Avg Completed Ticket Size"],
                pct_cols=["Completion Rate", "$1,500 Floor Share"],
                int_cols=["Applications", "Completed Accounts"],
            ),
            hide_index=True,
            use_container_width=True,
            height=520,
        )

        st.download_button(
            "Download Recommendation Segments",
            data=segments.to_csv(index=False),
            file_name="case_study_recommendation_segments.csv",
            mime="text/csv",
        )

    st.subheader("Top Merchants By Estimated Funded Amount")
    top_merchants = merchants.head(15).rename(
        columns={
            "merchant_id": "Merchant ID",
            "region": "Region",
            "applications": "Applications",
            "completed_applications": "Completed Applications",
            "estimated_funded_amount": "Estimated Funded Amount",
            "avg_prequal_risk_score": "Avg Prequal Risk Score",
            "avg_final_risk_score": "Avg Final Risk Score",
            "end_to_end_completion_rate": "End-To-End Completion",
            "swap_in_share": "Swap-In Share",
            "floor_share": "$1,500 Floor Share",
        }
    )
    st.dataframe(
        format_table(
            top_merchants,
            money_cols=["Estimated Funded Amount"],
            pct_cols=["End-To-End Completion", "Swap-In Share", "$1,500 Floor Share"],
            int_cols=["Applications", "Completed Applications"],
        ),
        hide_index=True,
        use_container_width=True,
    )

with tabs[5]:
    st.subheader("Questions The Current Data Does Not Answer")
    st.markdown(
        """
        <div class="snap-warning">
          <strong>Key caveat:</strong> this dashboard uses application and approval data only. It cannot validate
          repayment performance or profitability because the file does not include repayment outcomes.
        </div>
        """,
        unsafe_allow_html=True,
    )
    unanswered = pd.DataFrame(
        [
            {
                "Instruction Area": "Repayment metrics",
                "Status": "Not answered",
                "Reason": "No missed payment, no-payment, past-due, early payoff, charge-off, or account status fields are present.",
            },
            {
                "Instruction Area": "Profitability",
                "Status": "Not answered",
                "Reason": "No net funded amount, projected amount paid, revenue, loss, cost, or margin fields are present.",
            },
            {
                "Instruction Area": "True ticket size",
                "Status": "Partially answered",
                "Reason": "Final approval amount is used as an estimated funded amount, but actual funded amount is unavailable.",
            },
            {
                "Instruction Area": "Approval amount increase at full application",
                "Status": "Not supported by this file",
                "Reason": "For full applications, final approval amount equals prequalification actual approval amount in the raw data.",
            },
            {
                "Instruction Area": "Cohort performance maturity",
                "Status": "Not answered",
                "Reason": "No funded date or repayment window fields are present to season 30, 60, or 120 day performance metrics.",
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

    st.subheader("Recommended Follow-Up Data Request")
    st.markdown(
        """
        Request account-level repayment outcomes for completed applications, joined by application number:

        - Actual net funded amount and funded date
        - Projected amount paid or realized revenue
        - Charge-off status and charge-off amount
        - Missed payment or first-payment-default flags at 30, 45, and 60 days
        - Past-due status and dollars at 120 days
        - Early payoff or same-as-cash outcome
        - Standard-policy approval amount or decision counterfactual
        """
    )

with tabs[6]:
    st.subheader("Appendix")
    st.markdown(
        f"""
        **Report:** Medical Equipment Financing Program Case Study  
        **Prepared for:** Snap Finance management case study review  
        **As of:** source extract in package; date range {metadata['date_start']} to {metadata['date_end']}  
        **Data source:** `data/case_study_dataset.csv`  
        **Refresh cadence:** Ad hoc case study extract  
        **Row grain:** One prequalification application record

        **Metric definitions:** Prequal approval rate is prequal approvals divided by applications.
        Continuation rate is full applications divided by prequal approvals. Final approval rate is final
        approvals divided by full applications. End-to-end completion is completed applications divided by
        applications. Estimated funded amount uses final approval amount for completed applications only.
        """
    )

    query_path = Path(__file__).parent / "queries" / "case_study_reference.sql"
    if query_path.exists():
        with st.expander("Reference SQL Outline"):
            st.code(query_path.read_text(), language="sql")

    with st.expander("Raw Data Preview"):
        st.dataframe(filtered.head(200), hide_index=True, use_container_width=True)

    st.download_button(
        "Download Filtered Raw Data",
        data=filtered.to_csv(index=False),
        file_name="case_study_filtered_raw_data.csv",
        mime="text/csv",
    )
