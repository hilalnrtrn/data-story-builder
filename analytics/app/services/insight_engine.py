from typing import Any

import pandas as pd

from app.config.metadata_loader import load_dataset_metadata
from app.models.insight import Insight
from app.services.anomaly_detector import detect_anomaly
from app.services.change_detector import detect_change
from app.services.contrast_detector import (
    detect_top_bottom_contrast,
)
from app.services.contribution_detector import detect_contributions
from app.services.derived_metrics import build_return_rate_change_insight
from app.services.scoring import (
    apply_confidence_score,
    apply_importance_score,
)
from app.services.trend_detector import detect_trend


_SUPPORTED_AGGREGATIONS = {
    "SUM",
    "AVG",
}

_CONTRIBUTION_METRIC_TYPES = {
    "ADDITIVE",
    "ADDITIVE_UNDER_DEMO_ASSUMPTION",
}


def generate_insights(
    dataframe: pd.DataFrame,
    *,
    analysis_id: str,
    file_name: str,
    data_quality: dict[str, Any] | None = None,
) -> list[Insight]:
    metadata = load_dataset_metadata()

    insights: list[Insight] = []

    metric_metadata = _get_metric_metadata(
        metadata
    )
    dimension_metadata = _get_dimension_metadata(
        metadata
    )

    change_insights = _generate_change_insights(
        dataframe,
        analysis_id=analysis_id,
        file_name=file_name,
        metric_metadata=metric_metadata,
    )
    insights.extend(change_insights)

    discount_september_insight = (
        _generate_discount_september_change_insight(
            dataframe,
            analysis_id=analysis_id,
            file_name=file_name,
            metric_metadata=metric_metadata,
        )
    )
    if discount_september_insight is not None:
        insights.append(discount_september_insight)

    return_rate_insight = build_return_rate_change_insight(
        dataframe,
        analysis_id=analysis_id,
        file_name=file_name,
        previous_period="2025-08",
        current_period="2025-09",
    )
    if return_rate_insight is not None:
        insights.append(return_rate_insight)

    company_change_metrics = {
        insight.metric
        for insight in change_insights
        if insight.type == "CHANGE"
        and insight.dimension is None
        and insight.segment is None
    }

    insights.extend(
        _generate_product_trends(
            dataframe,
            analysis_id=analysis_id,
            file_name=file_name,
            metric_metadata=metric_metadata,
        )
    )

    insights.extend(
        _generate_product_anomalies(
            dataframe,
            analysis_id=analysis_id,
            file_name=file_name,
            metric_metadata=metric_metadata,
        )
    )

    insights.extend(
        _generate_contribution_insights(
            dataframe,
            analysis_id=analysis_id,
            file_name=file_name,
            metric_metadata=metric_metadata,
            dimension_metadata=dimension_metadata,
            company_change_metrics=company_change_metrics,
        )
    )

    insights.extend(
        _generate_contrast_insights(
            dataframe,
            analysis_id=analysis_id,
            file_name=file_name,
            metric_metadata=metric_metadata,
            dimension_metadata=dimension_metadata,
        )
    )

    if data_quality is not None:
        for insight in insights:
            apply_confidence_score(
                insight,
                data_quality=data_quality,
            )
            apply_importance_score(insight)

    return insights


def _get_metric_metadata(
    metadata: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    columns = metadata.get(
        "columns",
        {},
    )

    return {
        column_name: column_metadata
        for column_name, column_metadata
        in columns.items()
        if column_metadata.get("role") == "METRIC"
    }


def _get_dimension_metadata(
    metadata: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    columns = metadata.get(
        "columns",
        {},
    )

    return {
        column_name: column_metadata
        for column_name, column_metadata
        in columns.items()
        if column_metadata.get("role") == "DIMENSION"
    }


def _get_supported_aggregation(
    metric_metadata: dict[str, Any],
) -> str | None:
    aggregation = str(
        metric_metadata.get(
            "aggregation",
            "",
        )
    ).upper()

    if aggregation not in _SUPPORTED_AGGREGATIONS:
        return None

    return aggregation


def _generate_change_insights(
    dataframe: pd.DataFrame,
    *,
    analysis_id: str,
    file_name: str,
    metric_metadata: dict[str, dict[str, Any]],
) -> list[Insight]:
    insights: list[Insight] = []

    for metric, metadata in metric_metadata.items():
        aggregation = _get_supported_aggregation(
            metadata
        )

        if aggregation is None:
            continue

        insight = detect_change(
            dataframe,
            analysis_id=analysis_id,
            file_name=file_name,
            metric=metric,
            aggregation=aggregation,
            previous_period="2025-05",
            current_period="2025-06",
        )

        if insight is not None:
            insights.append(insight)

    return insights


def _generate_discount_september_change_insight(
    dataframe: pd.DataFrame,
    *,
    analysis_id: str,
    file_name: str,
    metric_metadata: dict[str, dict[str, Any]],
) -> Insight | None:
    discount_metadata = metric_metadata.get("Discount")
    if discount_metadata is None:
        return None

    aggregation = _get_supported_aggregation(discount_metadata)
    if aggregation is None:
        return None

    return detect_change(
        dataframe,
        analysis_id=analysis_id,
        file_name=file_name,
        metric="Discount",
        aggregation=aggregation,
        previous_period="2025-08",
        current_period="2025-09",
    )


def _generate_product_trends(
    dataframe: pd.DataFrame,
    *,
    analysis_id: str,
    file_name: str,
    metric_metadata: dict[str, dict[str, Any]],
) -> list[Insight]:
    revenue_metadata = metric_metadata.get(
        "Revenue"
    )

    if revenue_metadata is None:
        return []

    aggregation = _get_supported_aggregation(
        revenue_metadata
    )

    if aggregation is None:
        return []

    if "Product" not in dataframe.columns:
        return []

    insights: list[Insight] = []

    products = sorted(
        dataframe["Product"]
        .dropna()
        .astype(str)
        .unique()
    )

    for product in products:
        insight = detect_trend(
            dataframe,
            analysis_id=analysis_id,
            file_name=file_name,
            metric="Revenue",
            dimension="Product",
            segment=product,
            aggregation=aggregation,
            period_start="2025-01",
            period_end="2025-12",
        )

        if insight is not None:
            insights.append(insight)

    return insights


def _generate_product_anomalies(
    dataframe: pd.DataFrame,
    *,
    analysis_id: str,
    file_name: str,
    metric_metadata: dict[str, dict[str, Any]],
) -> list[Insight]:
    revenue_metadata = metric_metadata.get(
        "Revenue"
    )

    if revenue_metadata is None:
        return []

    aggregation = _get_supported_aggregation(
        revenue_metadata
    )

    if aggregation is None:
        return []

    if "Product" not in dataframe.columns:
        return []

    if "Date" not in dataframe.columns:
        return []

    insights: list[Insight] = []

    products = sorted(
        dataframe["Product"]
        .dropna()
        .astype(str)
        .unique()
    )

    valid_dates = dataframe["Date"].dropna()

    periods = sorted(
        valid_dates
        .dt.to_period("M")
        .astype(str)
        .unique()
    )

    for product in products:
        for period in periods:
            insight = detect_anomaly(
                dataframe,
                analysis_id=analysis_id,
                file_name=file_name,
                metric="Revenue",
                dimension="Product",
                segment=product,
                aggregation=aggregation,
                period=period,
                history_start="2025-01",
                history_end="2025-12",
            )

            if insight is not None:
                insights.append(insight)

    return insights


def _generate_contribution_insights(
    dataframe: pd.DataFrame,
    *,
    analysis_id: str,
    file_name: str,
    metric_metadata: dict[str, dict[str, Any]],
    dimension_metadata: dict[str, dict[str, Any]],
    company_change_metrics: set[str],
) -> list[Insight]:
    insights: list[Insight] = []

    for metric, metadata in metric_metadata.items():
        aggregation = str(
            metadata.get("aggregation", "")
        ).upper()
        metric_type = str(
            metadata.get("metricType", "")
        ).upper()

        if aggregation != "SUM":
            continue

        if metric_type not in _CONTRIBUTION_METRIC_TYPES:
            continue

        if metric not in company_change_metrics:
            continue

        for dimension in dimension_metadata:
            insights.extend(
                detect_contributions(
                    dataframe,
                    analysis_id=analysis_id,
                    file_name=file_name,
                    metric=metric,
                    dimension=dimension,
                    aggregation=aggregation,
                    previous_period="2025-05",
                    current_period="2025-06",
                )
            )

    return insights


def _generate_contrast_insights(
    dataframe: pd.DataFrame,
    *,
    analysis_id: str,
    file_name: str,
    metric_metadata: dict[str, dict[str, Any]],
    dimension_metadata: dict[str, dict[str, Any]],
) -> list[Insight]:
    insights: list[Insight] = []

    for metric, metadata in metric_metadata.items():
        aggregation = _get_supported_aggregation(
            metadata
        )

        if aggregation is None:
            continue

        for dimension in dimension_metadata:
            insight = detect_top_bottom_contrast(
                dataframe,
                analysis_id=analysis_id,
                file_name=file_name,
                metric=metric,
                dimension=dimension,
                aggregation=aggregation,
                previous_period="2025-05",
                current_period="2025-06",
            )

            if insight is not None:
                insights.append(insight)

    return insights
