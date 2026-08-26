from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from app.config.metadata_loader import load_dataset_metadata
from app.services.ingestion import (
    DatasetIngestionError,
    discover_schema,
    read_dataset,
)
from app.services.business_relevance import analyze_business_relevance
from app.services.day10_analysis import analyze_causality_and_context
from app.services.insight_clustering import build_insight_clusters
from app.services.insight_integrity import analyze_insight_integrity
from app.services.preparation import prepare_dataset
from app.services.data_quality import calculate_data_quality
from app.services.integrity import validate_integrity
from app.services.profiler import profile_dataset
from app.services.relationship_engine import generate_relationships
from app.services.semantic_roles import detect_semantic_roles
from app.services.insight_engine import generate_insights
from app.services.story_planner import build_story_plan



app = FastAPI(
    title="Data Story Builder Analytics API",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/datasets/prepare")
async def prepare_uploaded_dataset(
    analysis_id: str = Form(...),
    file: UploadFile = File(...),
):
    try:
        file_bytes = await file.read()

        raw_dataframe = read_dataset(
            file_bytes=file_bytes,
            file_name=file.filename or "",
        )

        raw_schema = discover_schema(raw_dataframe)

        prepared_dataframe, preparation_report = prepare_dataset(
            raw_dataframe
        )

        dataset_profile = profile_dataset(
            prepared_dataframe
        )

        semantic_roles = detect_semantic_roles(
            prepared_dataframe
        )

        integrity = validate_integrity(
            prepared_dataframe
        )

        data_quality = calculate_data_quality(
            prepared_dataframe,
            integrity,
        )

        insights = generate_insights(
            prepared_dataframe,
            analysis_id=analysis_id,
            file_name=file.filename or "",
            data_quality=data_quality,
        )

        relationships = generate_relationships(insights)
        insight_clusters = build_insight_clusters(
            insights,
            relationships,
        )
        metadata = load_dataset_metadata()
        business_relevance = analyze_business_relevance(
            insights,
            relationships,
            metadata,
        )
        insight_integrity = analyze_insight_integrity(
            insights,
            relationships,
            prepared_dataframe,
            metadata,
        )
        (
            causality,
            missing_context,
            context_summaries,
        ) = analyze_causality_and_context(
            insights,
            relationships,
            metadata,
        )
        story_plan = build_story_plan(
            insights,
            relationships,
            insight_clusters,
            business_relevance.ranked_insights,
            insight_integrity.evaluations,
            causality.evaluations,
            missing_context.evaluations,
            context_summaries.summaries,
        )


        prepared_schema = discover_schema(prepared_dataframe)

        return {
           "analysisId": analysis_id,
           "fileName": file.filename,
           "fileType": _get_file_type(file.filename or ""),
           "rawSchema": raw_schema,
           "preparedSchema": prepared_schema,
           "preparationReport": preparation_report,
           "datasetProfile": dataset_profile,
           "semanticRoles": semantic_roles,
           "integrity": integrity,
           "dataQuality": data_quality,
           "insights": [
               insight.model_dump(by_alias=True)
               for insight in insights
            ],
           "relationships": [
               relationship.model_dump(by_alias=True)
               for relationship in relationships
            ],
           "insightClusters": [
               cluster.model_dump(by_alias=True)
               for cluster in insight_clusters
            ],
           "businessRelevance": [
               evaluation.model_dump(by_alias=True)
               for evaluation in business_relevance.business_evaluations
            ],
           "priorityEvaluations": [
               evaluation.model_dump(by_alias=True)
               for evaluation in business_relevance.priority_evaluations
            ],
           "rankedInsights": [
               ranked.model_dump(by_alias=True)
               for ranked in business_relevance.ranked_insights
            ],
           "topRankedInsights": [
               ranked.model_dump(by_alias=True)
               for ranked in business_relevance.top_ranked_insights
            ],
           "insightIntegrity": [
               evaluation.model_dump(by_alias=True)
               for evaluation in insight_integrity.evaluations
            ],
           "causalityEvaluations": [
               evaluation.model_dump(by_alias=True)
               for evaluation in causality.evaluations
            ],
           "missingContextEvaluations": [
               evaluation.model_dump(by_alias=True)
               for evaluation in missing_context.evaluations
            ],
           "contextSummaries": [
               summary.model_dump(by_alias=True)
               for summary in context_summaries.summaries
            ],
           "storyPlan": story_plan.model_dump(by_alias=True),
        }

    except DatasetIngestionError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


def _get_file_type(file_name: str) -> str:
    lowered = file_name.lower()

    if lowered.endswith(".csv"):
        return "csv"

    if lowered.endswith(".xlsx"):
        return "xlsx"

    return "unknown"
