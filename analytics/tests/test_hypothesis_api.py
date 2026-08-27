from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
SAMPLE_DATA = (
    Path(__file__).resolve().parents[2]
    / "sample-data"
    / "sales_demo_clean.csv"
)


def test_prepare_endpoint_returns_deterministic_hypothesis_contract():
    analysis_id = "11111111-1111-1111-1111-111111111111"

    with SAMPLE_DATA.open("rb") as file_stream:
        response = client.post(
            "/datasets/prepare",
            data={"analysis_id": analysis_id},
            files={
                "file": (
                    SAMPLE_DATA.name,
                    file_stream,
                    "text/csv",
                )
            },
        )

    assert response.status_code == 200
    hypotheses = response.json()["hypotheses"]
    assert hypotheses
    hypothesis = next(
        item
        for item in hypotheses
        if item["statement"]
        == (
            "The observed change in MarketingSpend may be associated with "
            "the observed change in Revenue."
        )
    )
    assert hypothesis["analysisId"] == analysis_id
    assert hypothesis["id"].startswith("HYPOTHESIS-")
    assert hypothesis["status"] == "OPEN"
    assert hypothesis["sourceInsightIds"]
    assert hypothesis["sourceRelationshipIds"]
    assert hypothesis["supportingEvidence"]
    assert isinstance(hypothesis["counterEvidence"], list)
    assert isinstance(hypothesis["missingContext"], list)
    assert hypothesis["causalityStatus"] == "CAUSALITY_NOT_ESTABLISHED"
    assert hypothesis["reasons"]
    assert hypothesis["trackerVersion"] == "day16-v1"
