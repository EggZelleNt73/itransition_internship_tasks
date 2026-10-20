import pandas as pd


def compute_daily_revenue_func(dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df_orders = dfs["orders"].copy()
    daily_revenue = df_orders.groupby("date")["paid_price"].sum().reset_index().sort_values("date")
    # top_five_days_df = daily_revenue.nlargest(5, "paid_price")
    # return top_five_days_df
    return daily_revenue