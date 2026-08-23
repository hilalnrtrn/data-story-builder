from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from app.services.ingestion import (
    DatasetIngestionError,
    discover_schema,
    read_dataset,
)
from app.services.preparation import prepare_dataset
from app.services.data_quality import calculate_data_quality
from app.services.integrity import validate_integrity
from app.services.profiler import profile_dataset
from app.services.semantic_roles import detect_semantic_roles
from app.services.insight_engine import generate_insights



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