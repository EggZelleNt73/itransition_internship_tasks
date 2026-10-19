from src.types import StoreDataCollection
from src.pipeline.aggregations import (
    compute_daily_revenue,
    find_amount_of_unique_users,
    find_unique_sets_of_authors,
    find_most_popular_author,
    top_customer_by_spending
)
import pandas as pd
from src.utils import stream_all_store_files


AGGREGATION_ROUTER = {
    "compute_daily_revenue": compute_daily_revenue.compute_daily_revenue_func,
    "find_amount_of_unique_users": find_amount_of_unique_users.find_amount_of_unique_users_func,
    "find_unique_sets_of_authors": find_unique_sets_of_authors.find_unique_sets_of_authors_func,
    "most_popular_author": find_most_popular_author.find_most_popular_author_func,
    "top_customer_by_spending": top_customer_by_spending.top_customer_by_spending_func
}


def apply_aggregation(data_collection: StoreDataCollection, aggregation_method) -> dict[str, pd.DataFrame]:
    file_stream = stream_all_store_files(data_collection)
    aggregated_dfs = {}
    for store_name, dfs in file_stream:
        aggregated_dfs[store_name] = AGGREGATION_ROUTER.get(aggregation_method)(dfs)

    return aggregated_dfs
