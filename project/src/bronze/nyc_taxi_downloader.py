import os
import re
import datetime
from pathlib import Path
import httpx
from tqdm import tqdm
import json

from src.common.config import settings
from src.common.logger import logger
from src.common.watermark import (
    read_watermark,
    write_watermark
)


def calculate_safe_end_date() -> datetime.date:
    """
    Calculates the maximum available dataset month based on the TLC 
    standard 2-month publication lag.
    """

    today = datetime.date.today()
    first_of_this_month = today.replace(day=1)
    last_month = first_of_this_month - datetime.timedelta(days=1)
    safe_month = last_month.replace(day=1) - datetime.timedelta(days=1)
    return safe_month


def download_monthly_taxi_data(year: int, month: int, target_dir: Path) -> str:
    """
    Streams a single monthly NYC Yellow Taxi Parquet file from CloudFront 
    safely into the target directory with progress metrics.
    """

    formatted_month = f"{month:02d}"
    filename = f"{settings.NYC_FILE_PREFIX}_{year}-{formatted_month}.parquet"
    target_path = Path(target_dir) / filename
    url = f"{settings.NYC_TAXI_BASE_URL}/{filename}"

    target_path.parent.mkdir(parents=True, exist_ok=True)

    if target_path.exists() and target_path.stat().st_size > 0:
        logger.info(f"File already cached locally: {filename}")
        return str(target_path)

    logger.info(f"Streaming from TLC endpoint: {url}")

    try:
        with httpx.Client(timeout=60.0) as client:
            with client.stream("GET", url) as response:
                if response.status_code == 404:
                    logger.warning(f"Month {year}-{formatted_month} not published yet (404). Skipping.")
                    return ""
                response.raise_for_status()

                total_bytes = int(response.headers.get("content-length", 0))
                with open(target_path, "wb") as f, tqdm(
                    total=total_bytes, unit="iB", unit_scale=True, desc=filename, disable=(settings.ENVIRONMENT != "LOCAL")
                ) as progress_bar:
                    for chunk in response.iter_bytes(chunk_size=1024 * 64):
                        f.write(chunk)
                        if settings.ENVIRONMENT == "LOCAL":
                            progress_bar.update(len(chunk))

        logger.info(f"Successfully ingested file: {filename}")
        return str(target_path)
    except httpx.HTTPStatusError as err:
        if target_path.exists():
            os.remove(target_path)
        logger.error(f"HTTP error during ingestion for {filename}: {err}")
    except Exception as err:
        if target_path.exists():
            os.remove(target_path)
        logger.error(f"Unexpected error handling {filename}: {err}")
        return ""


def run_incremental_taxi_ingestion(fallback_year: int = settings.FALLBACK_OLDEST_TAXI_DATA_DATE, fallback_month: int = 1):
    """
    Automatically detects state context and incrementally syncs historical data chunks 
    up to the current safe calendar boundaries.
    """

    target_dir = Path(settings.NYC_TAXI_RAW_TARGET_DIR)
    latest_date = read_watermark(
        target_dir / settings.NYC_WATERMARK_FILENAME,
        key="last_ingested_date",
        date_format="%Y-%m"
    )
    end_date = calculate_safe_end_date()

    if latest_date:
        if latest_date.month == 12:
            current_date = datetime.date(latest_date.year + 1, 1, 1)
        else:
            current_date = datetime.date(latest_date.year, latest_date.month + 1, 1)
        logger.info(f"Found existing checkpoint state. Last ingested month: {latest_date.strftime('%Y-%m')}")
    else:
        current_date = datetime.date(fallback_year, fallback_month, 1)
        logger.info(f"No previous state found. Initializing cold start from: {current_date.strftime('%Y-%m')}")

    if current_date > end_date:
        logger.info("Everything is up to date! No new monthly blocks available for processing.")
        return
    
    logger.info(f"Executing incremental sync window: {current_date.strftime('%Y-%m')} to {end_date.strftime('%Y-%m')}")
    while current_date <= end_date:
        saved_path = download_monthly_taxi_data(current_date.year, current_date.month, target_dir)

        if saved_path:
            write_watermark(
                target_dir / settings.NYC_WATERMARK_FILENAME, 
                current_date,
                key="last_ingested_date",
                date_format="%Y-%m"
                )

        if current_date.month == 12:
            current_date = datetime.date(current_date.year + 1, 1, 1)
        else:
            current_date = datetime.date(current_date.year, current_date.month + 1, 1)

    logger.info("Incremental NYC Taxi ingestion cycle finalized.")


if __name__ == "__main__":
    run_incremental_taxi_ingestion(fallback_year=datetime.date.today().year, fallback_month=datetime.date.today().month - 3)