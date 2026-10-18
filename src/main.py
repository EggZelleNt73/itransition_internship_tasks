import pandas as pd
import os
from pathlib import Path
from src.config import load_configs
from src.enums import EnvVariables
from src.pipeline.extract import extract_raw_files


def main():
    load_configs()

    # stage 1: Extract raw files
    extracted_files = extract_raw_files(Path(os.getenv(EnvVariables.RAW_DATA_PATH)))
    for store_name, df_dictionary in extracted_files.items():
        print(f"-- {store_name}")
        for file, df in df_dictionary.items():
            print(f"{file}: {df.head()}")


if __name__ == "__main__":
    main()


