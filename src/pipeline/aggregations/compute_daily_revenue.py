import pandas as pd


def compute_daily_revenue_func(dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df_orders = dfs["orders"].copy()
    daily_revenue = df_orders.groupby("date")["paid_price"].sum().reset_index().sort_values("date")
    daily_revenue["date"] = daily_revenue["date"].dt.strftime("%Y-%m-%d")
    return daily_revenue