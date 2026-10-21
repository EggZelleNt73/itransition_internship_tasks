import os
from pathlib import Path
from src.enums import EnvVariables
from src.domain.interfaces import FileExtractionStrategy
from src.pipeline.extraction.local_extraction import LocalFileExtraction
from src.pipeline.extraction.azure_blob_storage_extraction import AzureBlobExtraction


def get_extraction_strategy() -> FileExtractionStrategy:
    environment = os.getenv(EnvVariables.APP_ENVIRONMENT, "LOCAL")

    if (environment == "PRODUCTION") or (environment == "AZURE"):
        conn_str = os.getenv(EnvVariables.AZURE_STORAGE_CONNECTION_STRING)
        container = os.getenv(EnvVariables.AZURE_STORAGE_CONTAINER_NAME)

        if (not conn_str) or (not container):
            raise ValueError("Cloud storage environment variables are missing on Azure host.")

        return AzureBlobExtraction(connection_string=conn_str, container_name=container)

    local_path = Path(os.getenv(EnvVariables.RAW_DATA_PATH))
    return LocalFileExtraction(directory_path=local_path)