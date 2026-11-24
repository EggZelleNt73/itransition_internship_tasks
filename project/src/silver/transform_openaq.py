from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType, 
    IntegerType, 
    LongType
)
from delta.tables import DeltaTable
from pathlib import Path


from src.common.config import settings
from src.common.logger import logger
from src.common.timer import timeit
from src.common.paths import to_spark_path
from src.common.watermark import (
    read_watermark,
    write_watermark
)


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
def run_silver_openaq_transform(spark: SparkSession, openqa_path: str, watermark_path: str) -> None:
    watermark_path = Path(watermark_path) / "_silver_openaq_watermark.json"
    all_jsonl_files = sorted(Path(openqa_path).glob("openaq_*.jsonl"))
    if not all_jsonl_files:
        logger.warning(f"No OpenAQ JSONL files found in {openqa_path}.")
        return

    last_processed_file = read_watermark(watermark_path, key="last_processed_file")
    if last_processed_file and spark.catalog.tableExists(settings.SILVER_AIR_QUALITY_TABLE):
        pending_files = [jf for jf in all_jsonl_files if jf.name > last_processed_file]
    else:
        pending_files = all_jsonl_files

    if not pending_files:
        logger.info("Silver Air Quality table is already up to date. No new JSONL files to process.")
        return

    logger.info(f"Found {len(pending_files)} new OpenAQ JSONL file(s) to process.")

    raw_df = spark.read.json(pending_files)
    silver_df = clean_openaq_dataframe(raw_df)

    if spark.catalog.tableExists(settings.SILVER_AIR_QUALITY_TABLE):
        logger.info(f"Merging incremental records into {settings.SILVER_AIR_QUALITY_TABLE}...")
        target_table = DeltaTable.forName(spark, settings.SILVER_AIR_QUALITY_TABLE)
        (
            target_table.alias("target")
            .merge(
                silver_df.alias("source"),
                "target.sensor_id = source.sensor_id "
                "AND target.parameter_name = source.parameter_name "
                "AND target.period_start_utc = source.period_start_utc",
            )
            .whenMatchedUpdateAll()
            .whenNotMatchedInsertAll()
            .execute()
        )
    else:
        logger.info(f"Creating initial Silver Delta table: {settings.SILVER_AIR_QUALITY_TABLE}")
        (
            silver_df.write.format("delta")
            .mode("overwrite")
            .option("overwriteSchema", "true")
            .saveAsTable(settings.SILVER_AIR_QUALITY_TABLE)
        )

    latest_file_name = pending_files[-1].name
    write_watermark(watermark_path, latest_file_name, key="last_processed_file")
    logger.info(f"Successfully updated {settings.SILVER_AIR_QUALITY_TABLE} up to {latest_file_name}.")
