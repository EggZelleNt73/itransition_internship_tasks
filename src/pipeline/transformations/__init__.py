import pandas as pd
from src.utils import stream_store_files
from src.types import StoreDataCollection
from src.pipeline.transformations import books, orders, users


TRANSFORM_ROUTER = {
    "books": books.transform,
    "orders": orders.transform,
    "users": users.transform
}


def apply_transformation(data_collection: StoreDataCollection) -> None:
    file_stream = stream_store_files(data_collection)

    for store_name, file_name, df in file_stream:
        transform_func = TRANSFORM_ROUTER.get(file_name)

        if transform_func:
            transformed_df = transform_func(df)
            data_collection[store_name][file_name] = transformed_df

        