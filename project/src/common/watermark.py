import datetime
import json
from pathlib import Path
from typing import Any
from src.common.logger import logger


def read_watermark(
    watermark_path: str | Path,
    key: str = "last_ingested_date",
    date_format: str | None = None
) -> Any | None:
    """
    Reads a watermark value from a JSON file.
    
    Args:
        watermark_path: Path to the JSON watermark file.
        key: JSON key storing the watermark value.
        date_format: Optional strptime format (e.g., '%Y-%m' or '%Y-%m-%d'). 
        If provided, parses the value into a datetime.date object.
        If None, returns the raw value (e.g., int year).
    """

    path = Path(watermark_path)
    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            raw_val = data.get(key)
            if raw_val is None:
                return None

            if date_format:
                return datetime.datetime.strptime(str(raw_val), date_format).date()
            return raw_val
    except Exception as err:
        logger.warning(f"Corrupted or unreadable watermark at {path}, ignoring: {err}")
        return None


def write_watermark(
        watermark_path: str | Path,
        value: Any,
        key: str = "last_ingested_date",
        date_format: str | None = None
 ) -> None:
    """
    Writes or updates a watermark JSON file atomically.
    
    Args:
        watermark_path: Path to the JSON watermark file.
        value: The watermark value (datetime.date, int, or str).
        key: JSON key to store the value under.
        date_format: Optional strftime format if value is a date/datetime object.
    """

    path = Path(watermark_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(value, (datetime.date, datetime.datetime)) and date_format:
        formated_value = value.strftime(date_format)
    else:
        formated_value = value

    payload = {
        key: formated_value,
        "updated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)