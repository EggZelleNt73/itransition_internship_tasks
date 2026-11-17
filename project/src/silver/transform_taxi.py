from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    LongType,
    TimestampType
)


from src.common.config import settings
from src.common.logger import logger
from src.common.timer import timeit


def clean_taxi_dataframe(df: DataFrame) -> DataFrame:
    """Applies schema standardization, quality filtering, and derived metrics to NYC Taxi data."""

    standardized_df = (
        df.select(
            F.col("VendorID").cast(IntegerType()).alias("vendor_id"),
            F.col("tpep_pickup_datetime").cast(TimestampType()).alias("pickup_datetime"),
            F.col("tpep_dropoff_datetime").cast(TimestampType()).alias("dropoff_datetime"),
            F.coalesce(F.col("passenger_count").cast(IntegerType()), F.lit(1)).alias("passenger_count"),
            F.col("trip_distance").cast(DoubleType()).alias("trip_distance_miles"),
            F.col("RatecodeID").cast(IntegerType()).alias("rate_code_id"),
            F.col("store_and_fwd_flag").alias("store_and_fwd_flag"),
            F.col("PULocationID").cast(IntegerType()).alias("pu_location_id"),
            F.col("DOLocationID").cast(IntegerType()).alias("do_location_id"),
            F.col("payment_type").cast(LongType()).alias("payment_type"),
            F.col("fare_amount").cast(DoubleType()).alias("fare_amount_usd"),
            F.col("extra").cast(DoubleType()).alias("extra_usd"),
            F.col("mta_tax").cast(DoubleType()).alias("mta_tax_usd"),
            F.col("tip_amount").cast(DoubleType()).alias("tip_amount_usd"),
            F.col("tolls_amount").cast(DoubleType()).alias("tolls_amount_usd"),
            F.col("improvement_surcharge").cast(DoubleType()).alias("improvement_surcharge_usd"),
            F.col("total_amount").cast(DoubleType()).alias("total_amount_usd"),
            F.coalesce(F.col("congestion_surcharge").cast(DoubleType()), F.lit(0.0)).alias("congestion_surcharge_usd"),
            F.coalesce(F.col("Airport_fee").cast(DoubleType()), F.lit(0.0)).alias("airport_fee_usd"),
            F.coalesce(F.col("cbd_congestion_fee").cast(DoubleType()), F.lit(0.0)).alias("cbd_congestion_fee_usd"),
        )
        .filter(
            (F.col("pickup_datetime").isNotNull())
            & (F.col("dropoff_datetime").isNotNull())
            & (F.col("dropoff_datetime") > F.col("pickup_datetime"))
            & (F.col("pickup_datetime") >= F.lit("2009-01-01"))
            & (F.col("trip_distance_miles") > 0.0)
            & (F.col("fare_amount_usd") > 0.0)
            & (F.col("total_amount_usd") > 0.0)
        )
        .withColumn("trip_date", F.to_date("pickup_datetime"))
        .withColumn("trip_year", F.year("pickup_datetime"))
        .withColumn("trip_month", F.month("pickup_datetime"))
        .withColumn(
            "trip_duration_minutes",
            F.round((F.unix_timestamp("dropoff_datetime") - F.unix_timestamp("pickup_datetime")) / 60.0, 2),
        )
        .filter((F.col("trip_duration_minutes") > 0.5) & (F.col("trip_duration_minutes") <= 720.0))
        .dropDuplicates(["vendor_id", "pickup_datetime", "dropoff_datetime", "pu_location_id", "do_location_id", "total_amount_usd"])
    )

    return standardized_df


@timeit
def run_silver_taxi_transform(spark: SparkSession, bronze_path: str) -> None:
    logger.info(f"Reading raw NYC Taxi Parquet files from: {bronze_path}")

    raw_df = spark.read.parquet(bronze_path)
    silver_df = clean_taxi_dataframe(raw_df)

    logger.info(f"Writing Silver Delta table: {settings.SILVER_TAXI_TABLE}")
    (
        silver_df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .partitionBy("trip_year", "trip_month")
        .saveAsTable(settings.SILVER_TAXI_TABLE)
    )
    logger.info(f"Successfully materialized {settings.SILVER_TAXI_TABLE}.")