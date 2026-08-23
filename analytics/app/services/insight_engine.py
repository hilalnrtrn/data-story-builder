from typing import Any

import pandas as pd

from app.config.metadata_loader import load_dataset_metadata
from app.models.insight import Insight
from app.services.anomaly_detector import detect_anomaly
from app.services.change_detector import detect_change
from app.services.trend_detector import detect_trend


_SUPPORTED_AGGREGATIONS = {
    "SUM",
    "AVG",
}


def generate_insights(
    dataframe: pd.DataFrame,
    *,
    analysis_id: str,
    file_name: str,
) -> list[Insight]:
    metadata = load_dataset_metadata()

    insights: list[Insight] = []

    metric_metadata = _get_metric_metadata(
        metadata
    )

    insights.extend(
        _generate_change_insights(
            dataframe,
            analysis_id=analysis_id,
            file_name=file_name,
            metric_metadata=metric_metadata,
        )
    )

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