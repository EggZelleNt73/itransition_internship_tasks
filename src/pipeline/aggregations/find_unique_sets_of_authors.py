import pandas as pd
from src.constants import UNKNOWN_STRING_VALUE


def find_unique_sets_of_authors_func(dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df_books = dfs["books"]
    author_series = df_books[(df_books["author"] != UNKNOWN_STRING_VALUE)]

    def standardize_author_set(author_string: str) -> str:
        names = [name.strip() for name in author_string.split(",")]
        names.sort()
        return ", ".join(names)

    standardized_sets = author_series["author"].apply(standardize_author_set)
    unique_sets_count = standardized_sets.nunique()
    return unique_sets_count