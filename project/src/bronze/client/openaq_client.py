import json
import datetime
from pathlib import Path
from openaq import OpenAQ
from openaq.core.exceptions import APIError
import orjson

from src.common.config import settings
from src.common.logger import logger
from src.common.constants import (
    NYC_LATITUDE,
    NYC_LONGITUDE
)


class OpenAQBronzeClient:
    """API Client to ingest raw air quality payloads from OpenAQ."""

    def __init__(self):
        if not settings.OPENAQ_API_KEY:
            logger.error("OpenAQ API Key missing in environment variables")
            raise ValueError("OPENAQ_API_KEY must be populated")

        self.client = OpenAQ(api_key=settings.OPENAQ_API_KEY)
        self.target_dir = Path(settings.OPENAQ_RAW_TARGET_DIR)
        self.target_dir.mkdir(parents=True, exist_ok=True)


    def fetch_nyc_daily_measurements(self, target_date: datetime.date) -> str:
        """
        Queries OpenAQ for all sensor readings within the NYC region 
        for a specific date and dumps the verbatim JSON response.
        """

        date_str = target_date.strftime("%Y-%m-%d")
        filename = f"openaq_nyc_{date_str}.json"
        output_path = self.target_dir / filename

        if output_path.exists() and output_path.stat().st_size > 0:
            logger.info(f"File already cached locally: {filename}")
            return str(output_path)

        date_from = f"{date_str}T00:00:00Z"
        date_to = f"{date_str}T23:59:59Z"

        logger.info(f"Identifying active NYC locations for date: {date_str}")

        try:
            locations_response = self.client.locations.list(
                coordinates=(NYC_LATITUDE, NYC_LONGITUDE),
                radius=25_000,
                limit=100
            )

            locations = locations_response.results
            if not locations:
                logger.warning(f"No operational OpenAQ locations discovered near NYC coordinates.")
                return ""

            all_raw_strings = []

            for location in locations:
                logger.info(f"Fetching sensor metrics for location ID {location.id}: {location.name}")

                sensors_response = self.client.locations.sensors(location.id)
                sensors = sensors_response.results

                for sensor in sensors:
                    page = 1
                    limit = 1000
                    while True:
                        measurements_response = self.client.measurements.list(
                            sensor.id,
                            "measurements",
                            datetime_from=date_from,
                            datetime_to=date_to,
                            limit=limit,
                            page=page
                        )

                        measurements = measurements_response.results
                        if not measurements:
                            break

                        batch_json_str = measurements_response.json(encoder=orjson)
                        all_raw_strings.append(batch_json_str)

                        if len(measurements) < limit:
                            break
                        page += 1

            if not all_raw_strings:
                logger.warning(f"No metrics or measurements recorded on {date_str} across NYC sensors.")
                return ""

            consolidated_records = []
            for json_str in all_raw_strings:
                data_chunk = orjson.loads(json_str)
                if isinstance(data_chunk, list):
                    consolidated_records.extend(data_chunk)
                elif isinstance(data_chunk, dict) and "results" in data_chunk:
                    consolidated_records.extend(data_chunk["results"])

            with open(output_path, "wb") as f:
                f.write(orjson.dumps(consolidated_records, option=orjson.OPT_INDENT_2))

            logger.info(f"Successfully landed raw bronze payload: {filename} ({len(consolidated_records)} records)")
            return str(output_path)
        except APIError as api_err:
            logger.error(f"OpenAQ API Exception encountered on {date_str}: {api_err}")
            return ""
        except Exception as err:
            logger.error(f"Unexpected processing system breakdown on {date_str}: {err}")
            return ""


if __name__ == "__main__":
    import datetime
    ingest_worker = OpenAQBronzeClient()
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    ingest_worker.fetch_nyc_daily_measurements(yesterday)