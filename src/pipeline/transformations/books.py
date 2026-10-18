import pandas as pd
import re


def transform(df: pd.DataFrame) -> pd.DataFrame:
    transformed_df = df.rename(columns=lambda col: re.sub(r"^:", "", col))
    transformed_df["year"] = pd.to_datetime(transformed_df["year"], format="%Y", errors="coerce")
    return transformed_df