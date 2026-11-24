import argparse
import datetime

from src.common.logger import logger
from src.common.timer import track_execution_time
from src.common.constants import (
    NYC_LATITUDE,
    NYC_LONGITUDE
)

from src.bronze.nyc_taxi_downloader import run_incremental_taxi_ingestion
from src.bronze.client.openaq_client import OpenAQBronzeClient
from src.bronze.client.worldbank_client import WorldBankBronzeClient
from src.bronze.client.ecb_client import ECBBronzeClient


def run_taxi_pipeline(fallback_year: int = 2009, fallback_month: int = 1) -> None:
    try:
        run_incremental_taxi_ingestion(fallback_year=fallback_year, fallback_month=fallback_month)
    except Exception as err:
        logger.error(f"NYC Taxi ingestion failed: {err}")


def run_openaq_pipeline(fallback_year: int = 2016, fallback_month: int = 1) -> None:
    cities = [
        {"city_name": "nyc", "coordinates": (NYC_LATITUDE, NYC_LONGITUDE), "radius": 25000}
    ]
    for city in cities:
        try:
            client = OpenAQBronzeClient(
                city_name=city["city_name"],
                coordinates=city["coordinates"],
                radius=city["radius"]
            )
            client.run_incremental_air_measurements_ingestion(fallback_year=fallback_year, fallback_month=fallback_month)
        except Exception as err:
            logger.error(f"OpenAQ ingestion failed for {city['city_name']}: {err}")


def run_worldbank_pipeline(fallback_year: int = 2009) -> None:
    targets = [
        {"country_code": "USA", "indicator": "NY.GDP.MKTP.CD"}
    ]
    for target in targets:
        try:
            client = WorldBankBronzeClient(
                country_code=target["country_code"],
                indicator=target["indicator"]
            )
            client.run_incremental_ingestion(fallback_year=fallback_year)
        except Exception as err:
            logger.error(f"World Bank ingestion failed for {target['country_code']}: {err}")


def run_ecb_pipeline(fallback_start_date: str = "2009-01-01") -> None:
    currency_pairs = [
        ("USD", "EUR")
    ]
    for base, quote in currency_pairs:
        try:
            client = ECBBronzeClient(base_currency=base, quote_currency=quote)
            client.run_incremental_ingestion(fallback_start_date=fallback_start_date)
        except Exception as err:
            logger.error(f"ECB FX ingestion failed for {base}/{quote}: {err}")


def main():
    parser = argparse.ArgumentParser(description="Bronze Layer Ingestion Orchestrator")
    parser.add_argument(
        "--source",
        type=str,
        choices=["all", "taxi", "openaq", "worldbank", "ecb"],
        default="all",
        help="Specify which data source pipeline to execute (default: all)."
    )
    args = parser.parse_args()

    pipelines = {
        "taxi": run_taxi_pipeline,
        "openaq": run_openaq_pipeline,
        "worldbank": run_worldbank_pipeline,
        "ecb": run_ecb_pipeline,
    }

    with track_execution_time(f"Bronze Orchestrator (source={args.source})"):
        if args.source == "all":
            for name, pipeline_func in pipelines.items():
                logger.info(f"--- Starting pipeline: {name.upper()} ---")
                pipeline_func()
        else:
            pipelines[args.source]()

if __name__ == "__main__":
    main()
