import pandas as pd
import networkx as nx
from src.constants import (
    UNKNOWN_STRING_VALUE
)


def find_amount_of_unique_users_func(dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df_users = dfs["users"]
    G = nx.Graph()

    G.add_nodes_from(df_users["id"])

    for column in ["name", "address", "phone", "email"]:
        groups = (df_users[df_users[column].notna() & (df_users[column] != UNKNOWN_STRING_VALUE)]\
                  .groupby(column)["id"]\
                  .apply(list)
                  )
        for id_list in groups:
            if len(id_list) > 1:
                base_id = id_list[0]
                for matching_id in id_list[1:]:
                    G.add_edge(base_id, matching_id)

    connected_components = list(nx.connected_components(G))

    id_to_master_map = {}
    for master_idx, component in enumerate(connected_components, start=1):
        master_id = f"MASTER_USER_{master_idx:03d}"
        for row_id in component:
            id_to_master_map[row_id] = master_id

    df_users["master_user_id"] = df_users["id"].map(id_to_master_map)
    df_users = df_users["master_user_id"].nunique()

    return df_users
