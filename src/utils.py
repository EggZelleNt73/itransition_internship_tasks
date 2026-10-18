import pandas as pd
from src.types import StoreDataCollection


def stream_store_files(collect: StoreDataCollection):
    for store_name, dfs in collect.items():
        for file, df in dfs.items():
            yield store_name, file, df