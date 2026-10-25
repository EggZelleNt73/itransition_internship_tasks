import pandas as pd
import numpy as np
import re
from src.constants import EXCHANGE_RATE_EUR_TO_USD
from src.utils import (
    replace_empty_data,
    fill_na_values
)
from src.constants import (
    UNKNOWN_STRING_VALUE,
)


def transform(df: pd.DataFrame) -> pd.DataFrame:
    df = replace_empty_data(df)
    currency_pattern = r"(\$|USD|€|¢|EUR|usd|eur)"
    df["currency"] = df["unit_price"].str.extract(currency_pattern, flags=re.IGNORECASE)
    inline_currency_regex = r"(\d+)(?:\$|USD|€|¢|EUR|usd|eur)(\d+)"
    df["unit_price"] = df["unit_price"].str.replace(inline_currency_regex, r"\1.\2", regex=True, flags=re.IGNORECASE)
    df["unit_price"] = df["unit_price"].str.replace(r"[^\d\.]", "", regex=True)
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    

    eur_mask = df["currency"].isin(["EUR", "€"])
    df.loc[eur_mask, "unit_price"] = df.loc[eur_mask, "unit_price"] * EXCHANGE_RATE_EUR_TO_USD
    df["unit_price"] = df["unit_price"].round(2)


    df["timestamp"] = df["timestamp"].str.replace(r"([AP])\.M\.", r"\1M", regex=True)\
                                    .str.replace(",", " ", regex=False)
    df["timestamp"]= pd.to_datetime(df["timestamp"], format="mixed", errors="coerce", utc=True)

    df = fill_na_values(df)

    df["currency"] = np.where(df["currency"] == UNKNOWN_STRING_VALUE, df["currency"], "USD")

    df["paid_price"] = df["quantity"] * df["unit_price"]

    df["date"] = df["timestamp"].dt.normalize()

    return df