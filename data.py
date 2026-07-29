from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st


DATA_PATH = Path(__file__).parent / "data" / "case_study_dataset.csv"

BOOL_COLUMNS = [
    "is_prequal_approved",
    "swap_in_approval",
    "submitted_full_application",
    "is_approved",
    "is_completed",
]

REQUIRED_COLUMNS = {
    "Application Number",
    "prequal_submit_dt",
    "prequal_submit_month",
    "merchant_id",
    "region",
    "prequalification_risk_grade",
    "final_risk_grade",
    "requested_financing_amount",
    "prequalification_risk_based_amount",
    "prequalification_actual_approval_amount",
    "final_approval_amount",
    "prequalification_risk_score",
    "final_risk_score",
    "credit_score",
    "is_prequal_approved",
    "swap_in_approval",
    "application_status",
    "submitted_full_application",
    "is_approved",
    "is_completed",
}

GRADE_ORDER = ["A", "B", "C", "D", "E", "F", "G"]
GRADE_RANK = {grade: idx for idx, grade in enumerate(GRADE_ORDER)}


def _to_bool(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .str.strip()
        .str.upper()
        .map({"TRUE": True, "FALSE": False, "1": True, "0": False})
        .fillna(False)
        .astype(bool)
    )


def _rate(numerator: float, denominator: float) -> float:
    if denominator in (0, None) or pd.isna(denominator):
        return np.nan
    return numerator / denominator


@st.cache_data(show_spinner="Loading case study dataset...")
def load_application_data() -> pd.DataFrame:
    data = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    missing = REQUIRED_COLUMNS.difference(data.columns)
    if missing:
        raise KeyError(f"Dataset is missing required columns: {sorted(missing)}")

    result = data.copy()
    result = result.rename(columns={"Application Number": "application_number"})

    result["prequal_submit_dt"] = pd.to_datetime(result["prequal_submit_dt"], errors="coerce")
    result["prequal_submit_month"] = pd.to_datetime(result["prequal_submit_month"], errors="coerce")

    for column in BOOL_COLUMNS:
        result[column] = _to_bool(result[column])

    numeric_columns = [
        "requested_financing_amount",
        "prequalification_risk_based_amount",
        "prequalification_actual_approval_amount",
        "final_approval_amount",
        "prequalification_risk_score",
        "final_risk_score",
        "credit_score",
    ]
    for column in numeric_columns:
        result[column] = pd.to_numeric(result[column], errors="coerce")

    result["estimated_funded_amount"] = np.where(
        result["is_completed"], result["final_approval_amount"].fillna(0), 0
    )
    result["underwriting_lift"] = (
        result["prequalification_actual_approval_amount"]
        - result["prequalification_risk_based_amount"]
    )
    result["hit_1500_floor"] = (
        (result["prequalification_risk_based_amount"] < 1500)
        & (result["prequalification_actual_approval_amount"] == 1500)
    )
    result["risk_score_improvement"] = (
        result["prequalification_risk_score"] - result["final_risk_score"]
    )
    result["approval_amount_change"] = (
        result["final_approval_amount"] - result["prequalification_actual_approval_amount"]
    )

    pre_rank = result["prequalification_risk_grade"].map(GRADE_RANK)
    final_rank = result["final_risk_grade"].map(GRADE_RANK)
    result["risk_grade_migration"] = np.select(
        [
            final_rank < pre_rank,
            final_rank == pre_rank,
            final_rank > pre_rank,
        ],
        ["Improved", "Same", "Worsened"],
        default="No final grade",
    )

    return result


def filter_data(
    data: pd.DataFrame,
    regions: list[str],
    merchants: list[int],
    grades: list[str],
    swap_values: list[bool],
    date_range: tuple[pd.Timestamp, pd.Timestamp],
) -> pd.DataFrame:
    start_date, end_date = date_range
    mask = (
        data["region"].isin(regions)
        & data["merchant_id"].isin(merchants)
        & data["prequalification_risk_grade"].isin(grades)
        & data["swap_in_approval"].isin(swap_values)
        & (data["prequal_submit_dt"] >= start_date)
        & (data["prequal_submit_dt"] <= end_date)
    )
    return data.loc[mask].copy()


def funnel_summary(data: pd.DataFrame) -> dict[str, float]:
    applications = len(data)
    prequal_approvals = float(data["is_prequal_approved"].sum())
    full_applications = float(data["submitted_full_application"].sum())
    final_approvals = float(data["is_approved"].sum())
    completions = float(data["is_completed"].sum())

    return {
        "applications": applications,
        "prequal_approvals": prequal_approvals,
        "full_applications": full_applications,
        "final_approvals": final_approvals,
        "completed_applications": completions,
        "prequal_approval_rate": _rate(prequal_approvals, applications),
        "continuation_rate": _rate(full_applications, prequal_approvals),
        "final_approval_rate": _rate(final_approvals, full_applications),
        "completion_after_approval_rate": _rate(completions, final_approvals),
        "end_to_end_completion_rate": _rate(completions, applications),
        "avg_requested_amount": data["requested_financing_amount"].mean(),
        "avg_prequal_approval": data["prequalification_actual_approval_amount"].mean(),
        "avg_final_approval": data["final_approval_amount"].mean(),
        "estimated_funded_amount": data["estimated_funded_amount"].sum(),
        "avg_prequal_risk_score": data["prequalification_risk_score"].mean(),
        "avg_final_risk_score": data["final_risk_score"].mean(),
    }


def monthly_funnel(data: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        data.groupby("prequal_submit_month", dropna=False)
        .agg(
            applications=("application_number", "count"),
            prequal_approvals=("is_prequal_approved", "sum"),
            full_applications=("submitted_full_application", "sum"),
            final_approvals=("is_approved", "sum"),
            completed_applications=("is_completed", "sum"),
            avg_requested_amount=("requested_financing_amount", "mean"),
            avg_prequal_approval=("prequalification_actual_approval_amount", "mean"),
            avg_final_approval=("final_approval_amount", "mean"),
            estimated_funded_amount=("estimated_funded_amount", "sum"),
        )
        .reset_index()
        .sort_values("prequal_submit_month")
    )
    grouped["prequal_approval_rate"] = grouped["prequal_approvals"] / grouped["applications"]
    grouped["continuation_rate"] = grouped["full_applications"] / grouped[
        "prequal_approvals"
    ].replace(0, np.nan)
    grouped["final_approval_rate"] = grouped["final_approvals"] / grouped[
        "full_applications"
    ].replace(0, np.nan)
    grouped["completion_after_approval_rate"] = grouped["completed_applications"] / grouped[
        "final_approvals"
    ].replace(0, np.nan)
    grouped["end_to_end_completion_rate"] = grouped["completed_applications"] / grouped[
        "applications"
    ]
    grouped["month"] = grouped["prequal_submit_month"].dt.strftime("%Y-%m")
    return grouped


def swap_summary(data: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        data.groupby("swap_in_approval")
        .agg(
            applications=("application_number", "count"),
            prequal_approvals=("is_prequal_approved", "sum"),
            full_applications=("submitted_full_application", "sum"),
            final_approvals=("is_approved", "sum"),
            completed_applications=("is_completed", "sum"),
            avg_prequal_risk_score=("prequalification_risk_score", "mean"),
            avg_final_risk_score=("final_risk_score", "mean"),
            avg_requested_amount=("requested_financing_amount", "mean"),
            avg_risk_based_amount=("prequalification_risk_based_amount", "mean"),
            avg_actual_prequal_approval=("prequalification_actual_approval_amount", "mean"),
            avg_final_approval=("final_approval_amount", "mean"),
            avg_underwriting_lift=("underwriting_lift", "mean"),
            floor_count=("hit_1500_floor", "sum"),
            estimated_funded_amount=("estimated_funded_amount", "sum"),
        )
        .reset_index()
    )
    grouped["segment"] = np.where(grouped["swap_in_approval"], "Swap-in", "Non-swap")
    grouped["prequal_approval_rate"] = grouped["prequal_approvals"] / grouped["applications"]
    grouped["continuation_rate"] = grouped["full_applications"] / grouped[
        "prequal_approvals"
    ].replace(0, np.nan)
    grouped["final_approval_rate"] = grouped["final_approvals"] / grouped[
        "full_applications"
    ].replace(0, np.nan)
    grouped["end_to_end_completion_rate"] = grouped["completed_applications"] / grouped[
        "applications"
    ]
    grouped["floor_share"] = grouped["floor_count"] / grouped["applications"]
    return grouped.sort_values("swap_in_approval")


def risk_grade_summary(data: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        data.groupby("prequalification_risk_grade", dropna=False)
        .agg(
            applications=("application_number", "count"),
            prequal_approvals=("is_prequal_approved", "sum"),
            full_applications=("submitted_full_application", "sum"),
            final_approvals=("is_approved", "sum"),
            completed_applications=("is_completed", "sum"),
            swap_in_applications=("swap_in_approval", "sum"),
            avg_prequal_risk_score=("prequalification_risk_score", "mean"),
            avg_actual_prequal_approval=("prequalification_actual_approval_amount", "mean"),
            avg_risk_based_amount=("prequalification_risk_based_amount", "mean"),
            estimated_funded_amount=("estimated_funded_amount", "sum"),
            floor_count=("hit_1500_floor", "sum"),
        )
        .reset_index()
    )
    grouped["grade_sort"] = grouped["prequalification_risk_grade"].map(GRADE_RANK).fillna(99)
    grouped = grouped.sort_values("grade_sort").drop(columns="grade_sort")
    grouped["prequal_approval_rate"] = grouped["prequal_approvals"] / grouped["applications"]
    grouped["continuation_rate"] = grouped["full_applications"] / grouped[
        "prequal_approvals"
    ].replace(0, np.nan)
    grouped["final_approval_rate"] = grouped["final_approvals"] / grouped[
        "full_applications"
    ].replace(0, np.nan)
    grouped["end_to_end_completion_rate"] = grouped["completed_applications"] / grouped[
        "applications"
    ]
    grouped["swap_in_share"] = grouped["swap_in_applications"] / grouped["applications"]
    grouped["floor_share"] = grouped["floor_count"] / grouped["applications"]
    grouped["avg_underwriting_lift"] = (
        grouped["avg_actual_prequal_approval"] - grouped["avg_risk_based_amount"]
    )
    return grouped


def risk_migration_summary(data: pd.DataFrame) -> pd.DataFrame:
    full_apps = data[data["submitted_full_application"]].copy()
    migration = (
        full_apps.groupby("risk_grade_migration")
        .agg(applications=("application_number", "count"))
        .reset_index()
    )
    total_with_migration = migration["applications"].sum()
    migration["share"] = migration["applications"] / total_with_migration
    order = {"Improved": 0, "Same": 1, "Worsened": 2, "No final grade": 3}
    migration["sort"] = migration["risk_grade_migration"].map(order)
    return migration.sort_values("sort").drop(columns="sort")


def merchant_segments(data: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        data.groupby(["merchant_id", "region"], dropna=False)
        .agg(
            applications=("application_number", "count"),
            completed_applications=("is_completed", "sum"),
            estimated_funded_amount=("estimated_funded_amount", "sum"),
            avg_prequal_risk_score=("prequalification_risk_score", "mean"),
            avg_final_risk_score=("final_risk_score", "mean"),
            swap_in_applications=("swap_in_approval", "sum"),
            floor_count=("hit_1500_floor", "sum"),
        )
        .reset_index()
    )
    grouped["end_to_end_completion_rate"] = grouped["completed_applications"] / grouped[
        "applications"
    ]
    grouped["swap_in_share"] = grouped["swap_in_applications"] / grouped["applications"]
    grouped["floor_share"] = grouped["floor_count"] / grouped["applications"]
    return grouped.sort_values("estimated_funded_amount", ascending=False)


def recommendation_segments(data: pd.DataFrame, min_applications: int = 5) -> pd.DataFrame:
    grouped = (
        data.groupby(
            ["region", "merchant_id", "prequalification_risk_grade", "swap_in_approval"],
            dropna=False,
        )
        .agg(
            applications=("application_number", "count"),
            completed_accounts=("is_completed", "sum"),
            avg_completed_ticket_size=(
                "final_approval_amount",
                lambda s: s[data.loc[s.index, "is_completed"]].mean(),
            ),
            estimated_funded_amount=("estimated_funded_amount", "sum"),
            avg_prequal_risk_score=("prequalification_risk_score", "mean"),
            avg_final_risk_score=("final_risk_score", "mean"),
            full_applications=("submitted_full_application", "sum"),
            final_approvals=("is_approved", "sum"),
            floor_count=("hit_1500_floor", "sum"),
        )
        .reset_index()
    )
    grouped = grouped[grouped["applications"] >= min_applications].copy()
    grouped["swap_in_status"] = np.where(grouped["swap_in_approval"], "Swap-in", "Non-swap")
    grouped["full_application_rate"] = grouped["full_applications"] / grouped["applications"]
    grouped["final_approval_rate"] = grouped["final_approvals"] / grouped["applications"]
    grouped["completion_rate"] = grouped["completed_accounts"] / grouped["applications"]
    grouped["floor_share"] = grouped["floor_count"] / grouped["applications"]

    median_conversion = grouped["completion_rate"].median()
    median_risk = grouped["avg_prequal_risk_score"].median()
    grouped["management_read"] = np.select(
        [
            (grouped["estimated_funded_amount"] > 0)
            & (grouped["completion_rate"] >= median_conversion)
            & (grouped["avg_prequal_risk_score"] <= median_risk),
            (grouped["estimated_funded_amount"] > 0)
            & (grouped["completion_rate"] >= median_conversion)
            & (grouped["avg_prequal_risk_score"] > median_risk),
            (grouped["completion_rate"] < median_conversion)
            | (grouped["completed_accounts"] == 0),
        ],
        ["Expand selectively", "Monitor risk", "Tighten or diagnose"],
        default="Needs more volume",
    )
    return grouped.sort_values("estimated_funded_amount", ascending=False)


def source_metadata(data: pd.DataFrame) -> dict[str, str]:
    return {
        "date_start": data["prequal_submit_dt"].min().strftime("%Y-%m-%d"),
        "date_end": data["prequal_submit_dt"].max().strftime("%Y-%m-%d"),
        "rows": f"{len(data):,}",
        "merchants": f"{data['merchant_id'].nunique():,}",
        "regions": f"{data['region'].nunique():,}",
    }
