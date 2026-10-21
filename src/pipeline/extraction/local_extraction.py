import pandas as pd
from pathlib import Path
import yaml
from src.types import StoreDataCollection
from src.domain.interfaces import FileExtractionStrategy


class LocalFileExtraction(FileExtractionStrategy):
    def __init__(self, directory_path: Path):
        self.directory_path = directory_path

    
    def _extract_yaml_file(self, file_path: Path) -> pd.DataFrame:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_yaml_file = yaml.safe_load(f)
        df = pd.DataFrame(raw_yaml_file)
        return df


    def _extract_parquest_file(self, file_path: Path) -> pd.DataFrame:
        df = pd.read_parquet(file_path)
        return df


    def _extract_csv_file(self, file_path: Path) -> pd.DataFrame:
        df = pd.read_csv(file_path)
        return df


    def extract_raw_files(self) -> StoreDataCollection:
        store_dfs = {}
        if not self.directory_path.exists():
            return store_dfs
        
        for item in self.directory_path.iterdir():
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
                            df = self._extract_yaml_file(file_path)
                        elif suffix == ".parquet":
                            df = self._extract_parquest_file(file_path)
                        elif suffix == ".csv":
                            df = self._extract_csv_file(file_path)

                        if (df is not None) and (not df.empty):
                            df = df.drop_duplicates()
                            df_dictionary[file_path.stem] = df
                    except Exception as e:
                        print(f"Failed to read a file {file_path.name}: {e}")

                if df_dictionary:
                    store_dfs[store_name] = df_dictionary
        return store_dfs
                


