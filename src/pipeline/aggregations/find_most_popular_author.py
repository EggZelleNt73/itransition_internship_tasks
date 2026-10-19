import pandas as pd


def find_most_popular_author_func(dfs: dict[str, pd.DataFrame]) -> str:
    df_books = dfs["books"].copy()
    df_orders = dfs["orders"].copy()
    top_book_id = df_orders.groupby("book_id")["quantity"].sum().idxmax()
    top_author = df_books.loc[df_books["id"] == top_book_id, "author"].values[0]

    return top_author
