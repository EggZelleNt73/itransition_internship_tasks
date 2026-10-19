import pandas as pd
import os
from pathlib import Path
from src.config import load_configs
from src.enums import EnvVariables
from src.pipeline.extract import extract_raw_files
from src.pipeline.transformations import apply_transformation
from src.pipeline.aggregations import apply_aggregation


def main():
    load_configs()

    # stage 1: Extract raw files
    extracted_files = extract_raw_files(Path(os.getenv(EnvVariables.RAW_DATA_PATH)))
    # for store_name, df_dictionary in extracted_files.items():
    #     print(f"-- {store_name}")
    #     for file, df in df_dictionary.items():
    #         print(f"---{file}---: {df.info()}")

    # for store_name, df_dictionary in extracted_files.items():
    #     print(f"-- {store_name}")
    #     for file, df in df_dictionary.items():
    #         print(f"File name: {file} -> Number of rows: {df.count()}")
    #     print(f"\n")

    # print(extracted_files["STORE1"]["books"].count())
    # print(extracted_files["STORE1"]["orders"].info())
    
    apply_transformation(extracted_files)
    # dfs= extracted_files
    # for file, df in dfs.items():
    #     print(f"--{file}")
    #     print(df.info())
    # print()

    # for store_name, df_dictionary in extracted_files.items():
    #     print(f"-- {store_name}")
    #     for file, df in df_dictionary.items():
    #         print(f"---File name: {file}")
    #         print(df.info())
    #     print()
    

    # print(extracted_files["STORE1"]["books"].count())
    # print(extracted_files["STORE1"]["orders"].info())
    # df = extracted_files["STORE1"]["orders"]
    # print(df[["id", "date"]])

    df_daily_revenue = (apply_aggregation(extracted_files, "compute_daily_revenue"))
    df_amount_unique_users = (apply_aggregation(extracted_files, "find_amount_of_unique_users"))


    # for store, agg_df in df_amount_unique_users.items():
    #     print(f"--{store}")
    #     print(agg_df, end="\n")



if __name__ == "__main__":
    main()


