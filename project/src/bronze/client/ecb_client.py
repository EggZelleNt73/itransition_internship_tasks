import datetime
import json
from pathlib import Path
import httpx

from src.common.config import settings
from src.common.logger import logger
from src.common.timer import timeit


class ECBBronzeClient:
    """Incrementally ingests daily USD/EUR spot exchange rates from the ECB API."""

    def __init__(self):
        self.base_url = settings.ECB_FX_URL
        self.target_dir = Path(settings.ECB_FX_RAW_TARGET_DIR)
        self.target_dir.mkdir(parents=True, exist_ok=True)
        self.watermark_path = self.target_dir / settings.ECB_FX_WATERMARK_FILENAME


    def _get_latest_ingested_date(self) -> datetime.date | None:
        if self.watermark_path.exists():
            try:
                with open(self.watermark_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return datetime.date.fromisoformat(data["last_ingested_date"])
            except Exception as err:
                logger.warning(f"Corrupted ECB watermark detected, ignoring: {err}")
        return None


    def _update_watermark(self, ingested_date: datetime.date) -> None:
        """Updates _watermark.json with the latest successfully processed date."""

        payload = {"last_ingested_date": ingested_date.strftime("%Y-%m-%d")}
        with open(self.watermark_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)


    @timeit
    def run_incremental_ingestion(self, fallback_start_date: str) -> str:
        """
        Fetches daily USD/EUR FX CSV records from the last watermark up to yesterday.
        """

        latest_date = self._get_latest_ingested_date()
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

        filename = f"ecb_usd_eur_{start_date.isoformat()}_to_{end_date.isoformat()}.csv"
        output_path = self.target_dir / filename

        logger.info(f"Requesting ECB FX rates for window: {start_date} to {end_date}")

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(self.base_url, params=params)

                if response.status_code == 404 or not response.text.strip():
                    logger.info(f"No ECB FX trading data published between {start_date} and {end_date}.")
                    self._update_watermark(end_date)
                    return ""

                response.raise_for_status()

                with open(output_path, "w", encoding="utf-8", newline="") as f:
                    f.write(response.text)

                self._update_watermark(end_date)
                logger.info(f"Successfully landed ECB FX CSV payload: {filename}")
                return str(output_path)
        except httpx.HTTPStatusError as err:
            logger.error(f"HTTP error fetching ECB FX data: {err}")
            return ""
        except Exception as err:
            logger.error(f"Unexpected error fetching ECB FX data: {err}")
            return ""


if __name__ == "__main__":
    client = ECBBronzeClient()
    client.run_incremental_ingestion((datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y-%m-%d"))
        