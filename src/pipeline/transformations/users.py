import pandas as pd
from src.utils import (
    replace_empty_data,
    fill_na_values
)

def transform(df: pd.DataFrame) -> pd.DataFrame:
    df = replace_empty_data(df)
    df = fill_na_values(df)
    return df