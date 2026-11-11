import os
from dotenv import load_dotenv, find_dotenv


load_dotenv(find_dotenv())


class Config:
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "LOCAL")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    NYC_TAXI_BASE_URL: str = os.getenv("NYC_TAXI_BASE_URL", "https://cloudfront.net")
    NYC_FILE_PREFIX: str = os.getenv("NYC_FILE_PREFIX", "yellow_tripdata")
    FALLBACK_OLDEST_TAXI_DATA_DATE: int = 2009
    NYC_TAXI_RAW_TARGET_DIR: str = os.getenv("NYC_TAXI_RAW_TARGET_DIR", "data/raw/taxi")

    OPENAQ_API_URL: str = os.getenv("OPENAQ_API_URL", "https://openaq.org")
    OPENAQ_API_KEY: str = os.getenv("OPENAQ_API_KEY", "")
    OPENAQ_RAW_TARGET_DIR = os.getenv("OPENAQ_RAW_TARGET_DIR", "data/raw/air_quality")
    
    WORLDBANK_API_URL: str = os.getenv("WORLDBANK_API_URL", "https://worldbank.org")
    ECB_FX_URL: str = os.getenv("ECB_FX_URL", "https://europa.eu")


settings = Config()