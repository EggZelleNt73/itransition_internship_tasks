import pandas as pd
import os
from pathlib import Path
from src.config import load_configs
from src.enums import EnvVariables
from src.pipeline.extract import extract_raw_files
from src.pipeline.transformations import apply_transformation


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
    
    apply_transformation(extracted_files)
    dfs= extracted_files["STORE1"]
    for file, df in dfs.items():
        print(f"--{file}")
        print(df.info())
    print()    


if __name__ == "__main__":
    main()


