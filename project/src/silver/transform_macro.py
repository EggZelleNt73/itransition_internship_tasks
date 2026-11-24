from pyspark.sql import SparkSession, DataFrame, Window
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, IntegerType
import json

from src.common.config import settings
from src.common.logger import logger
from src.common.timer import timeit
from src.common.paths import to_spark_path


def build_silver_macro_dataframe(spark: SparkSession, ecb_df: DataFrame, wb_df: DataFrame) -> DataFrame:
    """
    Cleans ECB daily FX rates, forward-fills weekend/holiday gaps over a continuous 
    daily calendar spine, and enriches each date with annual World Bank GDP.
    """

    clean_fx = (
        ecb_df.select(
            F.to_date("TIME_PERIOD", "yyyy-MM-dd").alias("calendar_date"),
            F.col("CURRENCY").alias("base_currency"),
            F.col("CURRENCY_DENOM").alias("quote_currency"),
            F.col("OBS_VALUE").cast(DoubleType()).alias("raw_fx_rate"),
        )
        .filter((F.col("calendar_date").isNotNull()) & (F.col("raw_fx_rate").isNotNull()))
        .dropDuplicates(["calendar_date", "base_currency", "quote_currency"])
    )

    bounds = clean_fx.agg(F.min("calendar_date").alias("min_dt"), F.max("calendar_date").alias("max_dt")).collect()
    min_dt, max_dt = bounds[0]["min_dt"], bounds[0]["max_dt"]
    date_spine = spark.sql(f"SELECT explode(sequence(to_date('{min_dt}'), to_date('{max_dt}'), interval 1 day)) AS calendar_date")

    window_ffill = Window.orderBy("calendar_date").rowsBetween(Window.unboundedPreceding, 0)
    daily_fx = (
        date_spine.join(clean_fx, on="calendar_date", how="left")
        .withColumn("usd_to_eur_rate", F.last("raw_fx_rate", ignorenulls=True).over(window_ffill))
        .withColumn("is_trading_day", F.col("raw_fx_rate").isNotNull())
        .withColumn("calendar_year", F.year("calendar_date"))
        .select("calendar_date", "calendar_year", "usd_to_eur_rate", "is_trading_day")
    )

    clean_gdp = (
        wb_df.select(
            F.col("date").cast(IntegerType()).alias("gdp_year"),
            F.col("countryiso3code").alias("country_code"),
            F.col("value").cast(DoubleType()).alias("annual_gdp_usd"),
        )
        .filter((F.col("gdp_year").isNotNull()) & (F.col("annual_gdp_usd").isNotNull()))
        .dropDuplicates(["gdp_year", "country_code"])
    )

    latest_gdp_row = clean_gdp.orderBy(F.desc("gdp_year")).first()
    latest_gdp_val = latest_gdp_row["annual_gdp_usd"] if latest_gdp_row else None

    macro_df = (
        daily_fx.join(clean_gdp, daily_fx["calendar_year"] == clean_gdp["gdp_year"], how="left")
        .withColumn("usa_annual_gdp_usd", F.coalesce(F.col("annual_gdp_usd"), F.lit(latest_gdp_val)))
        .select("calendar_date", "calendar_year", "usd_to_eur_rate", "is_trading_day", "usa_annual_gdp_usd")
    )
    return macro_df


@timeit
def run_silver_macro_transform(
    spark: SparkSession,
    ecb_path: str,
    wb_path: str,
) -> None:
    ecb_spark_path = f"{to_spark_path(ecb_path).rstrip("/")}/ecb_*.csv"
    wb_spark_path = f"{to_spark_path(wb_path).rstrip("/")}/worldbank_*.json"

    logger.info(f"Reading raw ECB FX CSVs from: {ecb_spark_path}")
    ecb_df = spark.read.option("header", "true").csv(ecb_spark_path)

    logger.info(f"Reading raw World Bank JSONs from: {wb_spark_path}")
    wb_json_rdd = spark.sparkContext.wholeTextFiles(wb_spark_path).values()

    def extract_wb_records(raw_text: str) -> list[str]:
        payload = json.loads(raw_text)
        if isinstance(payload, list) and len(payload) > 1 and isinstance(payload[1], list):
            return [json.dumps(rec) for rec in payload[1]]
        return []

    parsed_records = wb_json_rdd.flatMap(extract_wb_records)
    wb_df = spark.read.json(parsed_records)

    silver_df = build_silver_macro_dataframe(spark, ecb_df, wb_df)

    logger.info(f"Writing Silver Delta table: {settings.SILVER_MACRO_TABLE}")
    (
        silver_df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(settings.SILVER_MACRO_TABLE)
    )
    logger.info(f"Successfully materialized {settings.SILVER_MACRO_TABLE}.")
