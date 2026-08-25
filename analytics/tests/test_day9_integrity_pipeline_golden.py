import json
import math
from collections import Counter
from pathlib import Path

from app.config.metadata_loader import load_dataset_metadata
from app.services.data_quality import calculate_data_quality
from app.services.ingestion import read_dataset
from app.services.insight_engine import generate_insights
from app.services.insight_integrity import analyze_insight_integrity
from app.services.integrity import validate_integrity
from app.services.preparation import prepare_dataset
from app.services.relationship_engine import generate_relationships


ROOT_DIR = Path(__file__).resolve().parents[2]
SAMPLE_DATA_PATH = ROOT_DIR / "sample-data" / "sales_demo_clean.csv"
GOLDEN_TRUTH_PATH = ROOT_DIR / "tests" / "golden" / "expected_results.json"
ANALYSIS_ID = "DAY9-INTEGRITY-PIPELINE-GOLDEN"


def test_real_pipeline_integrity_output_matches_golden_safety_contract() -> None:
    golden_bytes = GOLDEN_TRUTH_PATH.read_bytes()
    golden_truth = json.loads(golden_bytes.decode("utf-8"))

    dataframe = read_dataset(
        file_bytes=SAMPLE_DATA_PATH.read_bytes(),
        file_name=SAMPLE_DATA_PATH.name,
    )
    prepared_dataframe, _ = prepare_dataset(dataframe)
    data_integrity = validate_integrity(prepared_dataframe)
    data_quality = calculate_data_quality(
        prepared_dataframe,
        data_integrity,
    )
    insights = generate_insights(
        prepared_dataframe,
        analysis_id=ANALYSIS_ID,
        file_name=SAMPLE_DATA_PATH.name,
        data_quality=data_quality,
    )
    relationships = generate_relationships(insights)
    metadata = load_dataset_metadata()
    result = analyze_insight_integrity(
        insights,
        relationships,
        prepared_dataframe,
        metadata,
    )
    repeated_result = analyze_insight_integrity(
        insights,
        relationships,
        prepared_dataframe,
        metadata,
    )

    insight_ids = {insight.id for insight in insights}
    evaluation_ids = [evaluation.insight_id for evaluation in result.evaluations]
    assert len(result.evaluations) == len(insights)
    assert len(evaluation_ids) == len(set(evaluation_ids))
    assert set(evaluation_ids) == insight_ids
    assert evaluation_ids == sorted(insight_ids)
    assert result.model_dump(by_alias=True) == repeated_result.model_dump(
        by_alias=True
    )

    assert all(evaluation.status for evaluation in result.evaluations)
    assert all(
        isinstance(evaluation.story_eligible, bool)
        and isinstance(evaluation.requires_qualification, bool)
        for evaluation in result.evaluations
    )
    assert all(
        evaluation.integrity_score is not None
        and math.isfinite(evaluation.integrity_score)
        and 0.0 <= evaluation.integrity_score <= 1.0
        for evaluation in result.evaluations
    )

    evaluations_by_id = {
        evaluation.insight_id: evaluation
        for evaluation in result.evaluations
    }
    revenue_spec = next(
        expected
        for expected in golden_truth["requiredInsights"]
        if expected["metric"] == "Revenue"
        and expected["type"] == "CHANGE"
    )
    revenue = next(
        insight
        for insight in insights
        if insight.type == "CHANGE"
        and insight.metric == revenue_spec["metric"]
        and insight.dimension is None
        and insight.segment is None
        and insight.period.get("previous") == revenue_spec["previousPeriod"]
        and insight.period.get("current") == revenue_spec["currentPeriod"]
    )
    revenue_evaluation = evaluations_by_id[revenue.id]
    assert revenue_evaluation.status == "PASS_WITH_WARNINGS"
    assert revenue_evaluation.story_eligible is True
    assert revenue_evaluation.requires_qualification is True
    assert {
        item.metric for item in revenue_evaluation.counter_evidence
    } == {"Orders", "Customers"}
    assert revenue_evaluation.contradictions == []
    assert revenue_evaluation.consistency_checks
    assert all(
        check.status == "PASS"
        for check in revenue_evaluation.consistency_checks
    )
    assert revenue_evaluation.integrity_score is not None
    assert math.isfinite(revenue_evaluation.integrity_score)

    one_off_spec = next(
        expected
        for expected in golden_truth["expectedIntegrityFindings"]
        if expected["type"] == "ONE_OFF_EFFECT"
        and expected["segment"] == "Smart Watch"
    )
    smart_watch = next(
        insight
        for insight in insights
        if insight.type == "ANOMALY"
        and insight.metric == one_off_spec["metric"]
        and insight.dimension == one_off_spec["dimension"]
        and insight.segment == one_off_spec["segment"]
        and insight.period.get("current") == one_off_spec["eventPeriod"]
    )
    smart_watch_evaluation = evaluations_by_id[smart_watch.id]
    assert smart_watch_evaluation.one_off_check is not None
    assert smart_watch_evaluation.one_off_check.risk == (
        one_off_spec["expectedOneOffRisk"]
    )
    assert smart_watch_evaluation.status == "REVIEW_REQUIRED"
    assert smart_watch_evaluation.story_eligible is True
    assert smart_watch_evaluation.requires_qualification is True
    assert smart_watch_evaluation.integrity_score is not None
    assert math.isfinite(smart_watch_evaluation.integrity_score)
    assert "oneOffRobustness" in smart_watch_evaluation.integrity_breakdown

    contribution_spec = golden_truth["expectedContributions"][0]
    marmara = next(
        insight
        for insight in insights
        if insight.type == "CONTRIBUTION"
        and insight.metric == contribution_spec["metric"]
        and insight.dimension == contribution_spec["dimension"]
        and insight.segment == contribution_spec["segment"]
        and insight.period.get("previous")
        == contribution_spec["previousPeriod"]
        and insight.period.get("current") == contribution_spec["currentPeriod"]
    )
    marmara_evaluation = evaluations_by_id[marmara.id]
    contribution_checks = [
        check
        for check in marmara_evaluation.consistency_checks
        if check.code == "CONTRIBUTION_TOTAL_RECONCILIATION"
    ]
    assert len(contribution_checks) == 1
    assert contribution_checks[0].status == "PASS"
    assert marmara_evaluation.contradictions == []
    assert marmara_evaluation.integrity_score is not None
    assert math.isfinite(marmara_evaluation.integrity_score)

    outlier_spec = next(
        expected
        for expected in golden_truth["expectedIntegrityFindings"]
        if expected["type"] == "OUTLIER_DEPENDENCY"
        and expected["segment"] == "Bluetooth Speaker"
    )
    bluetooth_trends = [
        insight
        for insight in insights
        if insight.type == "TREND"
        and insight.metric == outlier_spec["metric"]
        and insight.dimension == outlier_spec["dimension"]
        and insight.segment == outlier_spec["segment"]
    ]
    assert bluetooth_trends == []
    bluetooth_anomalies = [
        insight
        for insight in insights
        if insight.type == "ANOMALY"
        and insight.metric == outlier_spec["metric"]
        and insight.dimension == outlier_spec["dimension"]
        and insight.segment == outlier_spec["segment"]
        and insight.period.get("current")
        == outlier_spec["expectedOutlierPeriod"]
    ]
    assert len(bluetooth_anomalies) == 1

    status_counts = Counter(
        evaluation.status for evaluation in result.evaluations
    )
    eligibility_counts = Counter(
        evaluation.story_eligible for evaluation in result.evaluations
    )
    qualification_counts = Counter(
        evaluation.requires_qualification for evaluation in result.evaluations
    )
    counter_evidence_count = sum(
        bool(evaluation.counter_evidence) for evaluation in result.evaluations
    )
    high_outlier_count = sum(
        evaluation.outlier_check is not None
        and evaluation.outlier_check.level == "HIGH"
        for evaluation in result.evaluations
    )
    high_one_off_count = sum(
        evaluation.one_off_check is not None
        and evaluation.one_off_check.risk == "HIGH"
        for evaluation in result.evaluations
    )
    failed_consistency_count = sum(
        any(check.status == "FAIL" for check in evaluation.consistency_checks)
        for evaluation in result.evaluations
    )
    contradiction_count = sum(
        bool(evaluation.contradictions) for evaluation in result.evaluations
    )
    unsafe_contradiction_count = sum(
        any(
            finding.type
            in {"DATA_CONTRADICTION", "SEMANTIC_CONTRADICTION"}
            for finding in evaluation.contradictions
        )
        for evaluation in result.evaluations
    )

    assert status_counts["FAIL"] == 0
    assert failed_consistency_count == 0
    assert unsafe_contradiction_count == 0
    assert GOLDEN_TRUTH_PATH.read_bytes() == golden_bytes

    print()
    print("DAY 9 REAL INTEGRITY PIPELINE REVIEW")
    print(f"totalInsights={len(insights)}")
    print(f"totalEvaluations={len(result.evaluations)}")
    print(
        "statusDistribution="
        f"PASS:{status_counts['PASS']},"
        f"PASS_WITH_WARNINGS:{status_counts['PASS_WITH_WARNINGS']},"
        f"REVIEW_REQUIRED:{status_counts['REVIEW_REQUIRED']},"
        f"FAIL:{status_counts['FAIL']}"
    )
    print(
        "eligibilityDistribution="
        f"true:{eligibility_counts[True]},false:{eligibility_counts[False]}"
    )
    print(
        "qualificationDistribution="
        f"true:{qualification_counts[True]},false:{qualification_counts[False]}"
    )
    print(f"evaluationsWithCounterEvidence={counter_evidence_count}")
    print(f"evaluationsWithHighOutlierRisk={high_outlier_count}")
    print(f"evaluationsWithHighOneOffRisk={high_one_off_count}")
    print(f"evaluationsWithFailedConsistency={failed_consistency_count}")
    print(f"evaluationsWithContradictions={contradiction_count}")
    print(
        "revenue="
        f"{revenue_evaluation.status},"
        f"eligible:{revenue_evaluation.story_eligible},"
        f"qualified:{revenue_evaluation.requires_qualification}"
    )
    print(
        "smartWatch="
        f"{smart_watch_evaluation.status},"
        f"oneOff:{smart_watch_evaluation.one_off_check.risk}"
    )
    print(
        "marmaraContribution="
        f"{contribution_checks[0].status}"
    )
    print(f"bluetoothSpeakerTrendExists={bool(bluetooth_trends)}")
