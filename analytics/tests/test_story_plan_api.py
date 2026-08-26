from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
SAMPLE_DATA = (
    Path(__file__).resolve().parents[2]
    / "sample-data"
    / "sales_demo_clean.csv"
)


def test_prepare_endpoint_returns_complete_structured_story_plan():
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
    story_plan = response.json()["storyPlan"]

    assert story_plan["analysisId"] == analysis_id
    assert story_plan["plannerVersion"] == "day12-v1"
    assert story_plan["mainOutcome"]["insightId"]
    assert isinstance(story_plan["contributors"], list)
    assert isinstance(story_plan["counterSignals"], list)
    assert isinstance(story_plan["associatedSignals"], list)
    assert isinstance(story_plan["missingContext"], list)
    assert isinstance(story_plan["causalityConstraints"], list)
    assert [section["order"] for section in story_plan["outline"]] == sorted(
        section["order"] for section in story_plan["outline"]
    )
    assert isinstance(story_plan["interpretationLimited"], bool)
