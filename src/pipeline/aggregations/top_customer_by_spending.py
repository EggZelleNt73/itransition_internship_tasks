import pandas as pd
from src.constants import UNKNOWN_STRING_VALUE
from src.utils import reconciliation_construction


def top_customer_by_spending_func(dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df_users = dfs["users"].copy()
    df_orders = dfs["orders"].copy()

    id_to_master_map = reconciliation_construction(df_users, "id", ["name", "address", "phone", "email"])
    df_users["master_user_id"] = df_users["id"].map(id_to_master_map)
    df_orders["master_user_id"] = df_orders["user_id"].map(id_to_master_map)


    def distinct_values(values: pd.Series) -> list:
        valid_values = values.dropna()
        valid_values = valid_values[valid_values != UNKNOWN_STRING_VALUE]
        return sorted(valid_values.unique())

    customer_details = (
        df_users.groupby("master_user_id")
        .agg(
            user_ids=("id", distinct_values),
            user_names=("name", distinct_values),
            user_addresses=("address", distinct_values),
            user_phones=("phone", distinct_values),
            user_emails=("email", distinct_values),
        )
    )

    customer_spending = (
        df_orders.groupby("master_user_id")
        .agg(total_spending=("paid_price", "sum"))
        .reset_index()
    )
    rounded_spending = customer_spending["total_spending"].round(2)
    top_spending_customer = rounded_spending.max()

    customer_spending = customer_spending.loc[rounded_spending == top_spending_customer].reset_index(drop=True)
    customer_spending = customer_spending.merge(customer_details, how="left", on="master_user_id")

    return customer_spending