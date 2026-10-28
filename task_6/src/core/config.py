from pydantic_settings import BaseSettings
from src.core.enums import EnvVariableNames
import logging
import os
from pathlib import Path


class Settings(BaseSettings):
    database_url: str = (
        f"postgresql+asyncpg://{os.getenv(EnvVariableNames.DB_USER)}:"
        f"{os.getenv(EnvVariableNames.DB_PASSWORD)}@"
        f"{os.getenv(EnvVariableNames.DB_HOST)}:{os.getenv(EnvVariableNames.DB_PORT)}/"
        f"{os.getenv(EnvVariableNames.DB_NAME)}"
    )
    app_environment: str = os.getenv(EnvVariableNames.APP_ENVIRONMENT)
    logger_config: dict = {
        "level": getattr(logging, os.getenv(EnvVariableNames.LOGGER_LEVEL), logging.INFO),
        "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        "date_format": "%Y-%m-%d %H:%M:%S"
    }
    templates_path: Path = Path(__name__).resolve().parent / "templates"


settings = Settings()