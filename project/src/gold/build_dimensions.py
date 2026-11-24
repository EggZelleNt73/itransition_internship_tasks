import io
import csv
import httpx
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    IntegerType, 
    StringType, 
    StructField, 
    StructType
)

from src.common.config import settings
from src.common.logger import logger
from src.common.timer import timeit


@timeit
def build_dim_date_and_macro(spark: SparkSession) -> None:
    """Builds Gold DimDate and DimMacro from Silver Macro Economic data."""
    logger.info(f"Reading Silver Macro table: {settings.SILVER_MACRO_TABLE}")
    macro_df = spark.table(settings.SILVER_MACRO_TABLE)

    dim_date = (
        macro_df.select("calendar_date")
        .distinct()
        .withColumn("date_key", F.date_format("calendar_date", "yyyyMMdd").cast(IntegerType()))
        .withColumn("year", F.year("calendar_date"))
        .withColumn("quarter", F.quarter("calendar_date"))
        .withColumn("month", F.month("calendar_date"))
        .withColumn("month_name", F.date_format("calendar_date", "MMMM"))
        .withColumn("day_of_month", F.dayofmonth("calendar_date"))
        .withColumn("day_of_week", F.dayofweek("calendar_date"))
        .withColumn("day_name", F.date_format("calendar_date", "EEEE"))
        .withColumn("is_weekend", F.dayofweek("calendar_date").isin(1, 7))
        .select(
            "date_key", "calendar_date", "year", "quarter", "month",
            "month_name", "day_of_month", "day_of_week", "day_name", "is_weekend"
        )
    )

    logger.info(f"Writing Gold Dimension: {settings.GOLD_DIM_DATE_TABLE}")
    dim_date.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(settings.GOLD_DIM_DATE_TABLE)

    dim_macro = (
        macro_df.withColumn("date_key", F.date_format("calendar_date", "yyyyMMdd").cast(IntegerType()))
        .select("date_key", "calendar_date", "usd_to_eur_rate", "is_trading_day", "usa_annual_gdp_usd")
    )

    logger.info(f"Writing Gold Dimension: {settings.GOLD_DIM_MACRO_TABLE}")
    dim_macro.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(settings.GOLD_DIM_MACRO_TABLE)


@timeit
def build_dim_location(spark: SparkSession) -> None:
    """Fetches official NYC TLC Taxi Zone Lookup table and materializes Gold DimLocation."""
    lookup_url = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
    logger.info(f"Fetching NYC Taxi Zone Lookup from: {lookup_url}")

    headers = {"User-Agent": "Mozilla/5.0 (DataEngineeringPipeline/1.0)"}
    with httpx.Client(headers=headers, timeout=30.0) as client:
        response = client.get(lookup_url)
        response.raise_for_status()

    reader = csv.DictReader(io.StringIO(response.text))
    rows = [
        (
            int(row["LocationID"]),
            row["Borough"].strip(),
            row["Zone"].strip(),
            row["service_zone"].strip(),
        )
        for row in reader
        if row.get("LocationID")
    ]
    rows.append((-1, "Unknown", "Pre-2016 GPS / Unassigned", "N/A"))

    schema = StructType([
        StructField("location_id", IntegerType(), False),
        StructField("borough", StringType(), True),
        StructField("zone_name", StringType(), True),
        StructField("service_zone", StringType(), True),
    ])

    dim_location = spark.createDataFrame(rows, schema=schema)

    logger.info(f"Writing Gold Dimension: {settings.GOLD_DIM_LOCATION_TABLE}")
    dim_location.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(settings.GOLD_DIM_LOCATION_TABLE)
