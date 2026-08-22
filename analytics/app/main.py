from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from app.services.ingestion import (
    DatasetIngestionError,
    discover_schema,
    read_dataset,
)
from app.services.preparation import prepare_dataset


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

        prepared_schema = discover_schema(prepared_dataframe)

        return {
            "analysisId": analysis_id,
            "fileName": file.filename,
            "fileType": _get_file_type(file.filename or ""),
            "rawSchema": raw_schema,
            "preparedSchema": prepared_schema,
            "preparationReport": preparation_report,
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