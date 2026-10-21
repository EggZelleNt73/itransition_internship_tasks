import os
import io
import yaml
import pandas as pd
from pathlib import Path
from azure.storage.blob import BlobServiceClient
from src.types import StoreDataCollection
from src.domain.interfaces import FileExtractionStrategy


class AzureBlobExtraction(FileExtractionStrategy):
    def __init__(self, connection_string: str, container_name: str):
        self.connection_string = connection_string
        self.container_name = container_name


    def _extract_yaml_from_steam(self, file_bytes: io.BytesIO) -> pd.DataFrame:
        text_steam = io.TextIOWrapper(file_bytes, encoding="8-utf")
        raw_yaml_file = yaml.safe_load(text_steam)
        return pd.DataFrame(raw_yaml_file)


    def _extract_parquet_from_steam(self, file_bytes: io.BytesIO) -> pd.DataFrame:
        return pd.read_parquet(file_bytes)


    def _extract_csv_from_stream(self, file_bytes: io.BytesIO) -> pd.DataFrame:
        return pd.read_csv(file_bytes)


    def extract_raw_files(self) -> StoreDataCollection:
        blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
        container_client = blob_service_client.get_container_client(self.container_name)
        stores_dfs: StoreDataCollection = {}

        try:
            blob_list = container_client.list_blobs()
            for blob in blob_list:
                blob_name = blob.name
                path_parts = blob_name.split("/")

                if len(path_parts) < 2:
                    continue

                store_name = path_parts[0]
                file_name = path_parts[-1]
                path_obj = Path(file_name)
                suffix = path_obj.suffix.lower()
                file_stem = path_obj.stem.lower().strip()
                df = None

                try:
                    blob_client = container_client.get_blob_client(blob_name)
                    stream = blob_client.download_blob()
                    file_bytes = io.BytesIO(stream.readall())

                    if suffix in [".yaml", ".yml"]:
                        df = self._extract_yaml_from_stream(file_bytes)
                    elif suffix == ".parquet":
                        df = self._extract_parquet_from_stream(file_bytes)
                    elif suffix == ".csv":
                        df = self._extract_csv_from_stream(file_bytes)

                    if (df is not None) and (not df.empty):
                        df = df.drop_duplicates()
                        if store_name not in stores_dfs:
                            stores_dfs[store_name] = {}
                        stores_dfs[store_name][file_stem] = df
                except Exception as e:
                    print(f"Failed to read blob file {file_name}: {e}")
        except Exception as container_err:
            print (f"Failed to access blob container: {container_err}")
            raise container_err
        
        return stores_dfs

