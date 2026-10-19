import pandas as pd
import re
from src.utils import (
    replace_empty_data,
    fill_na_values
)

def transform(df: pd.DataFrame) -> pd.DataFrame:
    df = replace_empty_data(df)
    df = df.rename(columns=lambda col: re.sub(r"^:", "", col))
    df["year"] = pd.to_datetime(df["year"], format="%Y", errors="coerce")
    df = fill_na_values(df)
    return df