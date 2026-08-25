from pathlib import Path

from app.services.ingestion import read_dataset
from app.services.insight_engine import generate_insights
from app.services.insight_integrity import build_insight_contradictions
from app.services.preparation import prepare_dataset
from app.services.relationship_engine import generate_relationships


ROOT_DIR = Path(__file__).resolve().parents[2]
SAMPLE_DATA_PATH = ROOT_DIR / "sample-data" / "sales_demo_clean.csv"
ANALYSIS_ID = "DAY9-CONTRADICTION-GOLDEN"
CHANGE_PERIOD = {"previous": "2025-05", "current": "2025-06"}


def test_revenue_counter_signals_are_not_insight_contradictions() -> None:
    dataframe = read_dataset(
        file_bytes=SAMPLE_DATA_PATH.read_bytes(),
        file_name=SAMPLE_DATA_PATH.name,
    )
    prepared_dataframe, _ = prepare_dataset(dataframe)
    insights = generate_insights(
        prepared_dataframe,
        analysis_id=ANALYSIS_ID,
        file_name=SAMPLE_DATA_PATH.name,
    )
    relationships = generate_relationships(insights)

    changes = {
        insight.metric: insight
        for insight in insights
        if insight.type == "CHANGE"
        and insight.dimension is None
        and insight.segment is None
        and insight.period == CHANGE_PERIOD
    }
    revenue = changes["Revenue"]
    insights_by_id = {insight.id: insight for insight in insights}
    revenue_counter_relationships = [
        relationship
        for relationship in relationships
        if relationship.type == "COUNTER_SIGNAL"
        and revenue.id
        in {
            relationship.source_insight_id,
            relationship.target_insight_id,
        }
    ]
    counter_metrics = {
        insights_by_id[
            relationship.target_insight_id
            if relationship.source_insight_id == revenue.id
            else relationship.source_insight_id
        ].metric
        for relationship in revenue_counter_relationships
    }

    assert counter_metrics == {"Orders", "Customers"}
    assert build_insight_contradictions(
        revenue,
        [changes["Orders"], changes["Customers"]],
    ) == []
