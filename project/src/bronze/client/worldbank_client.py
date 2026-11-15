from pathlib import Path
import httpx
import orjson
import datetime
import json


from src.common.config import settings
from src.common.logger import logger
from src.common.timer import timeit
from src.common.watermark import (
    read_watermark,
    write_watermark
)


class WorldBankBronzeClient:
    """Fetches yearly USA GDP macro-economic indicator data from World Bank API."""

    def __init__(self, country_code: str = "USA", indicator: str = "NY.GDP.MKTP.CD"):
        self.country_code = country_code.upper()
        self.indicator = indicator
        self.entity_tag = f"{self.country_code}_{self.indicator}"

        base_url = settings.WORLDBANK_API_URL
        self.endpoint = f"{base_url}/country/{self.country_code}/indicator/{self.indicator}"
        self.target_dir = Path(settings.WORLDBANK_RAW_TARGET_DIR)
        self.target_dir.mkdir(parents=True, exist_ok=True)
        self.watermark_path = self.target_dir / f"_wb_{self.entity_tag}_{settings.WORLDBANK_WATERMARK_FILENAME}"


    @timeit
    def run_incremental_ingestion(self, fallback_year: int) -> str:
        """
        Incrementally fetches yearly USA GDP records from the last watermarked year 
        up to the current calendar year, updating the watermark only for years with non-null values.
        """

        latest_year = read_watermark(
            self.watermark_path,
            key="last_ingested_year"
        )

        current_year = datetime.date.today().year

        if latest_year is not None:
            start_year = latest_year + 1
            logger.info(f"Found World Bank watermark. Last ingested year: {latest_year}")
        else:
            start_year = fallback_year
            logger.info(f"No World Bank watermark found. Cold starting from: {start_year}")

        if start_year >= current_year:
            logger.info("World Bank GDP data is completely up to date! No new years to ingest.")
            return ""

        params = {
            "format": "json",
            "date": f"{start_year}:{current_year}",
            "per_page": 100
        }
        filename = f"worldbank_{self.entity_tag}_{start_year}_to_{current_year}.json"
        output_path = self.target_dir / filename

        logger.info(f"Fetching {self.entity_tag} from World Bank for window: {start_year} to {current_year}")

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(self.endpoint, params=params)
                response.raise_for_status()

                raw_payload = response.json()
                if not isinstance(raw_payload, list) or len(raw_payload) < 2 or not raw_payload[1]:
                    logger.warning(f"No GDP records returned for {start_year}-{current_year}.")
                    return ""

                records = raw_payload[1]

                valid_years = [
                    int(rec["date"]) for rec in records
                    if rec.get("value") is not None and rec.get("date")
                ]

                if not valid_years:
                    logger.info(f"No published (non-null) GDP values available yet for {start_year}-{current_year}.")
                    return ""

                with open(output_path, "wb") as f:
                    f.write(orjson.dumps(raw_payload, option=orjson.OPT_INDENT_2))

                max_valid_year = max(valid_years)
                write_watermark(
                    self.watermark_path,
                    max_valid_year,
                    key="last_ingested_year"
                )

                logger.info(
                    f"Successfully landed World Bank GDP payload: {filename} "
                    f"(Latest published year: {max_valid_year})"
                )
                return str(output_path)
        except httpx.HTTPStatusError as err:
            logger.error(f"HTTP error fetching World Bank GDP: {err}")
            return ""
        except Exception as err:
            logger.error(f"Unexpected error fetching World Bank GDP: {err}")
            return ""


if __name__ == "__main__":
    client = WorldBankBronzeClient("USA", "NY.GDP.MKTP.CD")
    client.run_incremental_ingestion(2020)