from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType, 
    IntegerType, 
    LongType
)


from src.common.config import settings
from src.common.logger import logger
from src.common.timer import timeit
from src.common.paths import to_spark_path


def clean_openaq_dataframe(df: DataFrame) -> DataFrame:
    """Flattens nested OpenAQ JSONL payloads and deduplicates hourly sensor readings."""
    flattened_df = (
        df.select(
            F.col("_ingestion_meta.city").alias("city"),
            F.col("_ingestion_meta.location_id").cast(LongType()).alias("location_id"),
            F.col("_ingestion_meta.location_name").alias("location_name"),
            F.col("_ingestion_meta.sensor_id").cast(LongType()).alias("sensor_id"),
            F.col("_ingestion_meta.latitude").cast(DoubleType()).alias("latitude"),
            F.col("_ingestion_meta.longitude").cast(DoubleType()).alias("longitude"),
            F.lower(F.col("parameter.name")).alias("parameter_name"),
            F.col("parameter.units").alias("units"),
            F.col("value").cast(DoubleType()).alias("measurement_value"),
            F.to_timestamp("period.datetimeFrom.utc").alias("period_start_utc"),
            F.to_timestamp("period.datetimeTo.utc").alias("period_end_utc"),
            F.col("coverage.percentComplete").cast(DoubleType()).alias("coverage_percent"),
        )
        .filter(
            (F.col("measurement_value").isNotNull())
            & (F.col("measurement_value") >= 0.0)
            & (F.col("period_start_utc").isNotNull())
            & (F.col("sensor_id").isNotNull())
        )
        .withColumn("measurement_datetime_nyc", F.from_utc_timestamp("period_start_utc", "America/New_York"))
        .withColumn("measurement_date", F.to_date("measurement_datetime_nyc"))
        .withColumn("measurement_hour", F.hour("measurement_datetime_nyc"))
        .dropDuplicates(["sensor_id", "parameter_name", "period_start_utc"])
    )
    return flattened_df


@timeit
def run_silver_openaq_transform(spark: SparkSession, openqa_path: str) -> None:

    openaq_spark_path = f"{to_spark_path(openqa_path).rstrip("/")}/*.jsonl"
    logger.info(f"Reading raw OpenAQ JSONL files from: {openaq_spark_path}")
    
    raw_df = spark.read.json(openaq_spark_path)
    silver_df = clean_openaq_dataframe(raw_df)

    logger.info(f"Writing Silver Delta table: {settings.SILVER_AIR_QUALITY_TABLE}")
    (
        silver_df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(settings.SILVER_AIR_QUALITY_TABLE)
    )
    logger.info(f"Successfully materialized {settings.SILVER_AIR_QUALITY_TABLE}.")
