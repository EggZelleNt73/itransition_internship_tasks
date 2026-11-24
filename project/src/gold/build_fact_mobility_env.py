from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType

from src.common.config import settings
from src.common.logger import logger
from src.common.timer import timeit


@timeit
def build_fact_mobility_env(spark: SparkSession) -> None:
    """
    Aggregates Silver Taxi trips to daily/zone grain and enriches with 
    daily Air Quality pollutant averages and EUR currency conversions.
    """
    logger.info("Reading Silver tables for Gold Fact aggregation...")
    taxi_df = spark.table(settings.SILVER_TAXI_TABLE)
    aq_df = spark.table(settings.SILVER_AIR_QUALITY_TABLE)
    macro_df = spark.table(settings.SILVER_MACRO_TABLE)

    taxi_daily_zone = (
        taxi_df.withColumn("pu_location_id", F.coalesce(F.col("pu_location_id"), F.lit(-1)))
        .groupBy("trip_date", "pu_location_id")
        .agg(
            F.count("*").alias("total_trips"),
            F.sum("passenger_count").alias("total_passengers"),
            F.round(F.sum("trip_distance_miles"), 2).alias("total_distance_miles"),
            F.round(F.sum("fare_amount_usd"), 2).alias("total_fare_usd"),
            F.round(F.sum("tip_amount_usd"), 2).alias("total_tips_usd"),
            F.round(F.sum("total_amount_usd"), 2).alias("total_revenue_usd"),
            F.round(F.avg("trip_duration_minutes"), 2).alias("avg_trip_duration_min"),
            F.round(F.avg("trip_distance_miles"), 2).alias("avg_trip_distance_miles"),
        )
    )

    aq_daily = (
        aq_df.filter(F.col("parameter_name").isin("pm25", "no2", "o3", "co"))
        .groupBy("measurement_date")
        .pivot("parameter_name", ["pm25", "no2", "o3", "co"])
        .agg(F.round(F.avg("measurement_value"), 4))
        .withColumnRenamed("pm25", "avg_pm25")
        .withColumnRenamed("no2", "avg_no2")
        .withColumnRenamed("o3", "avg_o3")
        .withColumnRenamed("co", "avg_co")
    )

    fact_df = (
        taxi_daily_zone
        .join(aq_daily, taxi_daily_zone["trip_date"] == aq_daily["measurement_date"], how="left")
        .join(macro_df.select("calendar_date", "usd_to_eur_rate"), taxi_daily_zone["trip_date"] == macro_df["calendar_date"], how="left")
        .withColumn("date_key", F.date_format("trip_date", "yyyyMMdd").cast(IntegerType()))
        .withColumn("trip_year", F.year("trip_date"))
        .withColumn("total_revenue_eur", F.round(F.col("total_revenue_usd") * F.col("usd_to_eur_rate"), 2))
        .select(
            "date_key",
            "trip_date",
            "trip_year",
            "pu_location_id",
            "total_trips",
            "total_passengers",
            "total_distance_miles",
            "total_fare_usd",
            "total_tips_usd",
            "total_revenue_usd",
            "total_revenue_eur",
            "avg_trip_duration_min",
            "avg_trip_distance_miles",
            "avg_pm25",
            "avg_no2",
            "avg_o3",
            "avg_co",
        )
    )

    logger.info(f"Writing Gold Fact table: {settings.GOLD_FACT_MOBILITY_ENV_TABLE}")
    (
        fact_df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .partitionBy("trip_year")
        .saveAsTable(settings.GOLD_FACT_MOBILITY_ENV_TABLE)
    )
    logger.info(f"Successfully materialized {settings.GOLD_FACT_MOBILITY_ENV_TABLE}.")
