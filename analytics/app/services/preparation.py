import pandas as pd


REGION_CANONICAL_VALUES = {
    "marmara": "Marmara",
    "ege": "Ege",
    "iç anadolu": "İç Anadolu",
    "akdeniz": "Akdeniz",
    "karadeniz": "Karadeniz",
}


def prepare_dataset(raw_dataframe: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    prepared = raw_dataframe.copy()

    rows_read = len(prepared)

    duplicates_removed = int(prepared.duplicated().sum())
    prepared = prepared.drop_duplicates().copy()

    whitespace_fixes = _count_whitespace_fixes(prepared)

    string_columns = prepared.select_dtypes(include=["str", "object"]).columns

    for column in string_columns:
        prepared[column] = prepared[column].apply(
            lambda value: value.strip()
            if isinstance(value, str)
            else value
        )

    categorical_values_normalized = 0

    if "Region" in prepared.columns:
        before = prepared["Region"].copy()

        prepared["Region"] = prepared["Region"].apply(
            _normalize_region
        )

        categorical_values_normalized = int(
            (before != prepared["Region"]).sum()
        )

    if "Campaign" in prepared.columns:
        prepared["Campaign"] = prepared["Campaign"].fillna("None")

    date_conversion_errors = 0

    if "Date" in prepared.columns:
        prepared["Date"] = pd.to_datetime(
            prepared["Date"],
            errors="coerce",
        )

        date_conversion_errors = int(
            prepared["Date"].isna().sum()
        )

    numeric_conversions = 0

    if "MarketingSpend" in prepared.columns:
        raw_marketing = prepared["MarketingSpend"].astype("string")

        numeric_conversions = int(
            raw_marketing.str.contains(",", regex=False, na=False).sum()
        )

        normalized_marketing = raw_marketing.str.replace(
            ",",
            ".",
            regex=False,
        )

        prepared["MarketingSpend"] = pd.to_numeric(
            normalized_marketing,
            errors="coerce",
        )

    missing_values_detected = _count_relevant_missing_values(
        prepared
    )

    report = {
        "rowsRead": rows_read,
        "rowsPrepared": len(prepared),
        "duplicatesRemoved": duplicates_removed,
        "missingValuesDetected": missing_values_detected,
        "categoricalValuesNormalized": categorical_values_normalized,
        "whitespaceFixes": whitespace_fixes,
        "dateConversionErrors": date_conversion_errors,
        "numericConversions": numeric_conversions,
    }

    return prepared, report


def _normalize_region(value):
    if not isinstance(value, str):
        return value

    cleaned = value.strip()

    canonical = REGION_CANONICAL_VALUES.get(
        cleaned.casefold()
    )

    return canonical if canonical is not None else cleaned


def _count_whitespace_fixes(dataframe: pd.DataFrame) -> int:
    fixes = 0

    string_columns = dataframe.select_dtypes(
        include=["str", "object"]
    ).columns

    for column in string_columns:
        series = dataframe[column]

        fixes += int(
            series.apply(
                lambda value: (
                    isinstance(value, str)
                    and value != value.strip()
                )
            ).sum()
        )

    return fixes


def _count_relevant_missing_values(
    dataframe: pd.DataFrame,
) -> int:
    excluded_columns = {"Campaign", "Date"}

    relevant_columns = [
        column
        for column in dataframe.columns
        if column not in excluded_columns
    ]

    return int(
        dataframe[relevant_columns]
        .isna()
        .sum()
        .sum()
    )