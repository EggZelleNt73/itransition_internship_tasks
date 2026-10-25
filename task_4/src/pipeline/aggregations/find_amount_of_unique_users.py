import pandas as pd
from src.utils import reconciliation_construction


def find_amount_of_unique_users_func(dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df_users = dfs["users"].copy()
    id_to_master_map = reconciliation_construction(df_users, "id", ["name", "address", "phone", "email"])
    df_users["master_user_id"] = df_users["id"].map(id_to_master_map)
    df_users = df_users["master_user_id"].nunique()
    return df_users
