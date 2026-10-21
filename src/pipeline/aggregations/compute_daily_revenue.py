import pandas as pd


def compute_daily_revenue_func(dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    if "orders" not in dfs:
        print("Warning: 'orders' dataset missing from store data allocation mapping.")
        return pd.DataFrame(columns=["date", "paid_price"])
    df_orders = dfs["orders"].copy()
    daily_revenue = df_orders.groupby("date")["paid_price"].sum().reset_index().sort_values("date")
    daily_revenue["date"] = daily_revenue["date"].dt.strftime("%Y-%m-%d")
    return daily_revenue