import pandas as pd
from src.types import StoreDataCollection
from src.constants import (
    UNKNOWN_STRING_VALUE,
)


def stream_store_files(collect: StoreDataCollection):
    for store_name, dfs in collect.items():
        for file, df in dfs.items():
            yield store_name, file, df


def replace_empty_data(df: pd.DataFrame) -> pd.DataFrame:
    EMPTY_STRING_VALUES = ["", "nan", "None", "NULL"]
    EMPTY_NUMERIC_VALUES = [0]
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            continue
        elif pd.api.types.is_string_dtype(df[col]):
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace(EMPTY_STRING_VALUES, pd.NA)
        elif df[col].dtype == "object":
            cleaned_series = df[col].astype(str).str.strip()
            converted = pd.to_numeric(cleaned_series, errors="coerce")
            if not converted.isna().all():
                df[col] = converted
        elif pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].replace(EMPTY_NUMERIC_VALUES, pd.NA)
            if df[col].dtype == "int64":
                df[col] = df[col].astype("Int64")
            elif df[col].dtype == "float64":
                df[col] = df[col].astype("Float64")

    return df


def fill_na_values(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]):
            df[col] = df[col].fillna(UNKNOWN_STRING_VALUE)

    return df
