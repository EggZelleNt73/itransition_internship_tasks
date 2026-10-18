import pandas as pd
from pathlib import Path
import yaml

    
def extract_yaml_file(file_path: Path) -> pd.DataFrame:
    with open(file_path, "r", encoding="utf-8") as f:
        raw_yaml_file = yaml.safe_load(f)

    df = pd.DataFrame(raw_yaml_file)
    return df


def extract_parquest_file(file_path: Path) -> pd.DataFrame:
    df = pd.read_parquet(file_path)
    return df


def extract_csv_file(file_path: Path) -> pd.DataFrame:
    df = pd.read_csv(file_path)
    return df


def extract_raw_files(directory_path: Path) -> dict[str, dict[str, pd.DataFrame]]:
    store_dfs = {}
    for item in directory_path.iterdir():
        if item.is_dir():
            store_name = item.name
            df_dictionary = {}

            for file_path in item.iterdir():
                if not file_path.is_file():
                    continue
                suffix = file_path.suffix.lower()
                df = None

                try:
                    if suffix in [".yaml", ".yml"]:
                        df = extract_yaml_file(file_path)
                    elif suffix == ".parquet":
                        df = extract_parquest_file(file_path)
                    elif suffix == ".csv":
                        df = extract_csv_file(file_path)

                    if (df is not None) and (not df.empty):
                        df_dictionary[file_path.name] = df
                except Exception as e:
                    print(f"Failed to read a file {file_path.name}: {e}")

            if df_dictionary:
                store_dfs[store_name] = df_dictionary
    return store_dfs
                


