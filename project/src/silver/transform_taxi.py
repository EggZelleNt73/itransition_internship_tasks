from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    LongType,
    TimestampType,
    StringType
)
from pathlib import Path
import pyarrow.parquet as pq
from collections import defaultdict
from functools import reduce


from src.common.config import settings
from src.common.logger import logger
from src.common.timer import timeit
from src.common.paths import to_spark_path
from src.common.watermark import (
    read_watermark,
    write_watermark
)


def clean_taxi_dataframe(df: DataFrame) -> DataFrame:
    """Applies schema standardization, quality filtering, and derived metrics to NYC Taxi data."""

    cols_lower = {c.lower(): c for c in df.columns}

    def pick_col(candidates: list[str], target_type, default_val=None) -> F.Column:
        matched = [
            F.col(cols_lower[cand.lower()]).cast(target_type)
            for cand in candidates
            if cand.lower() in cols_lower
        ]
        if not matched:
            return F.lit(default_val).cast(target_type)
        if default_val is not None:
            matched.append(F.lit(default_val).cast(target_type))
        return F.coalesce(*matched) if len(matched) > 1 else matched[0]


    # Resolve Vendor ID across integer (1, 2) and legacy string ('CMT', 'VTS') formats
    raw_vendor = F.upper(F.trim(pick_col(["VendorID", "vendor_name"], StringType())))
    vendor_col = (
        F.when(raw_vendor.isin("1", "CMT"), F.lit(1))
        .when(raw_vendor.isin("2", "VTS"), F.lit(2))
        .otherwise(F.lit(None))
        .cast(IntegerType())
    )

    # Resolve Payment Type across numeric codes and legacy string labels
    raw_payment = F.upper(F.trim(pick_col(["payment_type"], StringType())))
    payment_col = (
        F.when(raw_payment.isin("1", "CRD", "CREDIT"), F.lit(1))
        .when(raw_payment.isin("2", "CSH", "CASH"), F.lit(2))
        .when(raw_payment.isin("3", "NOC", "NO CHARGE"), F.lit(3))
        .when(raw_payment.isin("4", "DIS", "DISPUTE"), F.lit(4))
        .otherwise(F.lit(None))
        .cast(LongType())
    )

    return (
        df.select(
            vendor_col.alias("vendor_id"),
            pick_col(["tpep_pickup_datetime", "Trip_Pickup_DateTime", "pickup_datetime"], TimestampType()).alias("pickup_datetime"),
            pick_col(["tpep_dropoff_datetime", "Trip_Dropoff_DateTime", "dropoff_datetime"], TimestampType()).alias("dropoff_datetime"),
            pick_col(["passenger_count"], IntegerType(), default_val=1).alias("passenger_count"),
            pick_col(["trip_distance"], DoubleType()).alias("trip_distance_miles"),
            pick_col(["RatecodeID", "Rate_Code"], IntegerType()).alias("rate_code_id"),
            pick_col(["store_and_fwd_flag", "store_and_forward"], StringType()).alias("store_and_fwd_flag"),
            pick_col(["PULocationID"], IntegerType()).alias("pu_location_id"),
            pick_col(["DOLocationID"], IntegerType()).alias("do_location_id"),
            payment_col.alias("payment_type"),
            pick_col(["fare_amount", "Fare_Amt"], DoubleType()).alias("fare_amount_usd"),
            pick_col(["extra", "surcharge"], DoubleType(), default_val=0.0).alias("extra_usd"),
            pick_col(["mta_tax"], DoubleType(), default_val=0.0).alias("mta_tax_usd"),
            pick_col(["tip_amount", "Tip_Amt"], DoubleType(), default_val=0.0).alias("tip_amount_usd"),
            pick_col(["tolls_amount", "Tolls_Amt"], DoubleType(), default_val=0.0).alias("tolls_amount_usd"),
            pick_col(["improvement_surcharge"], DoubleType(), default_val=0.0).alias("improvement_surcharge_usd"),
            pick_col(["total_amount", "Total_Amt"], DoubleType()).alias("total_amount_usd"),
            pick_col(["congestion_surcharge"], DoubleType(), default_val=0.0).alias("congestion_surcharge_usd"),
            pick_col(["Airport_fee"], DoubleType(), default_val=0.0).alias("airport_fee_usd"),
            pick_col(["cbd_congestion_fee"], DoubleType(), default_val=0.0).alias("cbd_congestion_fee_usd"),
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


@timeit
def run_silver_taxi_transform(spark: SparkSession, taxi_path: str, watermark_path: str) -> None:
    watermark_path = Path(watermark_path) / "_silver_taxi_watermark.json"
    all_parquet_files = sorted(Path(taxi_path).glob("yellow_tripdata_*.parquet"))
    if not all_parquet_files:
        logger.warning(f"No NYC Taxi Parquet files found in {taxi_path}.")
        return

    last_processed_file = read_watermark(watermark_path, key="last_processed_file")
    if last_processed_file and spark.catalog.tableExists(settings.SILVER_TAXI_TABLE):
        pending_files = [pf for pf in all_parquet_files if pf.name > last_processed_file]
    else:
        pending_files = all_parquet_files

    if not pending_files:
        logger.info("Silver Taxi table is already up to date. No new Parquet files to process.")
        return

    logger.info(f"Found {len(pending_files)} new NYC Taxi Parquet file(s) to process.")

    schema_buckets: dict[str, list[str]] = defaultdict(list)
    for pf in pending_files:
        schema_sig = str(pq.read_schema(pf))
        schema_buckets[schema_sig].append(to_spark_path(str(pf)))

    normalized_dfs = []
    for idx, file_group in enumerate(schema_buckets.values(), start=1):
        logger.info(f"Processing schema bucket {idx}/{len(schema_buckets)} ({len(file_group)} files)...")
        raw_bucket_df = spark.read.parquet(*file_group)
        normalized_dfs.append(clean_taxi_dataframe(raw_bucket_df))

    silver_df = reduce(lambda df1, df2: df1.unionByName(df2), normalized_dfs)

    logger.info(f"Incrementally updating Silver Delta table: {settings.SILVER_TAXI_TABLE}")
    spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")
    if spark.catalog.tableExists(settings.SILVER_TAXI_TABLE):
        (
            silver_df.write.format("delta")
            .mode("overwrite")
            .partitionBy("trip_year", "trip_month")
            .saveAsTable(settings.SILVER_TAXI_TABLE)
        )
    else:
        (
            silver_df.write.format("delta")
            .mode("overwrite")
            .option("overwriteSchema", "true")
            .partitionBy("trip_year", "trip_month")
            .saveAsTable(settings.SILVER_TAXI_TABLE)
        )

    latest_file_name = pending_files[-1].name
    write_watermark(watermark_path, latest_file_name, key="last_processed_file")
    logger.info(f"Successfully updated {settings.SILVER_TAXI_TABLE} up to {latest_file_name}.")