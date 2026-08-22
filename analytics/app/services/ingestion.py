from io import BytesIO
from pathlib import Path

import pandas as pd


SUPPORTED_EXTENSIONS = {".csv", ".xlsx"}


class DatasetIngestionError(Exception):
    """Raised when an uploaded dataset cannot be read."""


def read_dataset(file_bytes: bytes, file_name: str) -> pd.DataFrame:
    if not file_name or not file_name.strip():
        raise DatasetIngestionError("File name is required.")

    if not file_bytes:
        raise DatasetIngestionError("The uploaded file is empty.")

    extension = Path(file_name).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise DatasetIngestionError(
            "Unsupported file type. Only CSV and XLSX files are supported."
        )

    try:
        buffer = BytesIO(file_bytes)

        if extension == ".csv":
            return pd.read_csv(buffer)

        return pd.read_excel(
            buffer,
            engine="openpyxl",
        )

    except Exception as exc:
        raise DatasetIngestionError(
            f"Unable to parse {extension.removeprefix('.').upper()} file."
        ) from exc

def discover_schema(dataframe: pd.DataFrame) -> dict:
    columns = [
        {
            "name": str(column),
            "dataType": str(dataframe[column].dtype),
        }
        for column in dataframe.columns
    ]

    return {
        "rowCount": len(dataframe),
        "columnCount": len(dataframe.columns),
        "columns": columns,
    }