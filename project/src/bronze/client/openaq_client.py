import json
import datetime
from pathlib import Path
from openaq import OpenAQ
from openaq.core.exceptions import APIError
import orjson
import time

from src.common.config import settings
from src.common.logger import logger
from src.common.constants import (
    NYC_LATITUDE,
    NYC_LONGITUDE
)
from src.common.timer import timeit


class OpenAQBronzeClient:
    """API Client to ingest raw air quality payloads from OpenAQ."""

    def __init__(self):
        if not settings.OPENAQ_API_KEY:
            logger.error("OpenAQ API Key missing in environment variables")
            raise ValueError("OPENAQ_API_KEY must be populated")

        self.client = OpenAQ(api_key=settings.OPENAQ_API_KEY)
        self.target_dir = Path(settings.OPENAQ_RAW_TARGET_DIR)
        self.target_dir.mkdir(parents=True, exist_ok=True)
        self.target_parameters = {"pm25", "no2", "o3"}

    
    @timeit
    def fetch_nyc_measurements_range(self, start_date: datetime.date, end_date: datetime.date) -> str:
        """
        Fetches a multi-day window of NYC air quality logs, filtering strictly 
        for core target pollutants (PM2.5, NO2, O3) to minimize API calls.
        """

        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        filename = f"openaq_nyc_{start_str}_to_{end_str}.jsonl"
        output_path = self.target_dir / filename

        if output_path.exists() and output_path.stat().st_size > 0:
            logger.info(f"File already cached locally: {filename}")
            return str(output_path)

        logger.info(f"Identifying active NYC locations for window: {start_str} to {end_str}")
        
        try:
            locations_response = self.client.locations.list(
                coordinates=(NYC_LATITUDE, NYC_LONGITUDE),
                radius=25000,
                limit=100
            )
            
            locations = locations_response.results
            if not locations:
                logger.warning("No operational OpenAQ locations discovered near NYC coordinates.")
                return ""

            records_written = 0
            with open(output_path, "wb") as f:
                for location in locations:
                    sensors_response = self.client.locations.sensors(location.id)
                    sensors = sensors_response.results
                    
                    for sensor in sensors:
                        param_name = getattr(sensor.parameter, "name", "").lower()
                        if param_name not in self.target_parameters:
                            continue

                        logger.info(f"Pulling {param_name.upper()} from location {location.id} (Sensor {sensor.id})")
                        page = 1
                        limit = 1000
                        
                        while True:
                            measurements_response = self.client.measurements.list(
                                sensor.id,
                                "measurements",
                                datetime_from=start_str,
                                datetime_to=end_str,
                                limit=limit,
                                page=page
                            )
                            
                            measurements = measurements_response.results
                            if not measurements:
                                break
                            
                            batch_data = orjson.loads(measurements_response.json(encoder=orjson))
                            items = batch_data.get("results", []) if isinstance(batch_data, dict) else batch_data
                            
                            for item in items:
                                f.write(orjson.dumps(item) + b"\n")
                                records_written += 1
                            
                            if len(measurements) < limit:
                                break
                            page += 1

            if records_written == 0:
                if output_path.exists():
                    output_path.unlink()
                logger.warning(f"No target pollutant measurements recorded between {start_str} and {end_str}.")
                return ""
            
            logger.info(f"Successfully landed raw bronze payload: {filename} ({records_written} records)")
            return str(output_path)

        except APIError as api_err:
            logger.error(f"OpenAQ API Exception encountered: {api_err}")
            return ""
        except Exception as err:
            logger.error(f"Unexpected processing system breakdown: {err}")
            return ""


if __name__ == "__main__":
    import datetime
    ingest_worker = OpenAQBronzeClient()
    start_date = datetime.date.today() - datetime.timedelta(days=30)
    end_date = datetime.date.today() - datetime.timedelta(days=1)
    ingest_worker.fetch_nyc_measurements_range(start_date, end_date)