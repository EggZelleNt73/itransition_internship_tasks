from src.enums import EnvVariables
import os
import logging

LOGGER_CONFIG = {
    "level": getattr(logging, os.getenv(EnvVariables.LOGGER_LEVEL), logging.INFO),
    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S"
}


PAGE_CONFIG = {
    "page_title" : "Weyland-Yutani Mining Analytics",
    "title": "WEYLAND-YUTANI CORPORATION",
    "background": "#121416",
    "card": "#1a1d20",
    "accent": "#f39c12",
    "anomaly": "#e74c3c",
    "text": "#ffffff",
    "muted": "#8a9199"
}