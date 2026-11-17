import datetime
import json
from pathlib import Path
import httpx

from src.common.config import settings
from src.common.logger import logger
from src.common.timer import timeit
from src.common.watermark import (
    read_watermark,
    write_watermark
)


class ECBBronzeClient:
    """Incrementally ingests daily USD/EUR spot exchange rates from the ECB API."""

    def __init__(self, base_currency: str = "USD", quote_currency: str = "EUR"):
        self.base_currency = base_currency.upper()
        self.quote_currency = quote_currency.upper()
        self.pair_tag = f"{self.base_currency}_{self.quote_currency}"

        base_url = settings.ECB_FX_URL
        self.endpoint = f"{base_url}/D.{self.base_currency}.{self.quote_currency}.SP00.A"
        self.target_dir = Path(settings.ECB_FX_RAW_TARGET_DIR)
        self.target_dir.mkdir(parents=True, exist_ok=True)
        self.watermark_path = self.target_dir / f"_ecb_{self.pair_tag}_{settings.ECB_FX_WATERMARK_FILENAME}"


    @timeit
    def run_incremental_ingestion(self, fallback_start_date: str) -> str:
        """
        Fetches daily USD/EUR FX CSV records from the last watermark up to yesterday.
        """

        latest_date = read_watermark(
            self.watermark_path,
            key="last_ingested_date",
            date_format="%Y-%m-%d"
        )
        end_date = datetime.date.today() - datetime.timedelta(days=1)

        if latest_date:
            start_date = latest_date + datetime.timedelta(days=1)
            logger.info(f"Found ECB watermark. Last ingested date: {latest_date.isoformat()}")
        else:
            start_date = datetime.date.fromisoformat(fallback_start_date)
            logger.info(f"No ECB watermark found. Cold starting from: {start_date.isoformat()}")

        if start_date > end_date:
            logger.info("ECB FX rates are completely up to date! No new dates to ingest.")
            return ""

        params = {
            "format": "csvdata",
            "startPeriod": start_date.isoformat(),
            "endPeriod": end_date.isoformat()
        }

        filename = f"ecb_{self.pair_tag}_{start_date.isoformat()}_to_{end_date.isoformat()}.csv"
        output_path = self.target_dir / filename

        logger.info(f"Requesting ECB {self.pair_tag} rates for window: {start_date} to {end_date}")

        try:
            transport = httpx.HTTPTransport(local_address="0.0.0.0", retries=3)
            headers = {"User-Agent": "Mozilla/5.0 (DataEngineeringPipeline/1.0)"}
            with httpx.Client(transport=transport, headers=headers, timeout=60.0) as client:
                response = client.get(self.endpoint, params=params)

                if response.status_code == 404 or not response.text.strip():
                    logger.info(f"No ECB FX trading data published between {start_date} and {end_date}.")
                    write_watermark(
                        self.watermark_path,
                        end_date,
                        key="last_ingested_date",
                        date_format="%Y-%m-%d"
                        )
                    return ""

                response.raise_for_status()

                with open(output_path, "w", encoding="utf-8", newline="") as f:
                    f.write(response.text)

                write_watermark(
                    self.watermark_path,
                    end_date,
                    key="last_ingested_date",
                    date_format="%Y-%m-%d"
                    )
                logger.info(f"Successfully landed ECB FX CSV payload: {filename}")
                return str(output_path)
        except httpx.HTTPStatusError as err:
            logger.error(f"HTTP error fetching ECB FX data: {err}")
            return ""
        except Exception as err:
            logger.error(f"Unexpected error fetching ECB FX data: {err}")
            return ""


if __name__ == "__main__":
    client = ECBBronzeClient("USD", "EUR")
    client.run_incremental_ingestion((datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y-%m-%d"))
        