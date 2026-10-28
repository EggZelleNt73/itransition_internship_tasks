from enum import StrEnum


class EnvVariableNames(StrEnum):
    DB_NAME = "DB_NAME"
    DB_USER = "DB_USER"
    DB_PASSWORD = "DB_PASSWORD"
    DB_HOST = "DB_HOST"
    DB_PORT = "DB_PORT"
    APP_ENVIRONMENT = "APP_ENVIRONMENT"
    LOGGER_LEVEL = "LOGGER_LEVEL"