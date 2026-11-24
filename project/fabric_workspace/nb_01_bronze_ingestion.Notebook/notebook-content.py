# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "f58b6c8c-955b-441a-9862-610d8244d644",
# META       "default_lakehouse_name": "lh_nyc_analytics",
# META       "default_lakehouse_workspace_id": "05462b15-e0cb-4e7b-9f28-cef12a0a7f51",
# META       "known_lakehouses": [
# META         {
# META           "id": "f58b6c8c-955b-441a-9862-610d8244d644"
# META         }
# META       ]
# META     },
# META     "environment": {
# META       "environmentId": "f3cdc9d3-3393-b87c-4884-073cd67d81f9",
# META       "workspaceId": "00000000-0000-0000-0000-000000000000"
# META     }
# META   }
# META }

# CELL ********************

import os
import notebookutils

var_lib = notebookutils.variableLibrary.getLibrary("vl_nyc_analytics")

os.environ["ENVIRONMENT"] = var_lib.ENVIRONMENT
os.environ["LOG_LEVEL"] = var_lib.LOG_LEVEL

os.environ["NYC_TAXI_BASE_URL"] = var_lib.NYC_TAXI_BASE_URL
os.environ["NYC_FILE_PREFIX"] = var_lib.NYC_FILE_PREFIX
os.environ["NYC_TAXI_RAW_TARGET_DIR"] = var_lib.NYC_TAXI_RAW_TARGET_DIR
os.environ["NYC_WATERMARK_FILENAME"] = var_lib.NYC_WATERMARK_FILENAME

os.environ["OPENAQ_API_URL"] = var_lib.OPENAQ_API_URL
os.environ["OPENAQ_API_KEY"] = var_lib.OPENAQ_API_KEY
os.environ["OPENAQ_RAW_TARGET_DIR"] = var_lib.OPENAQ_RAW_TARGET_DIR
os.environ["OPENAQ_WATERMARK_FILENAME"] = var_lib.OPENAQ_WATERMARK_FILENAME

os.environ["WORLDBANK_API_URL"] = var_lib.WORLDBANK_API_URL
os.environ["WORLDBANK_RAW_TARGET_DIR"] = var_lib.WORLDBANK_RAW_TARGET_DIR
os.environ["WORLDBANK_WATERMARK_FILENAME"] = var_lib.WORLDBANK_WATERMARK_FILENAME

os.environ["ECB_FX_URL"] = var_lib.ECB_FX_URL
os.environ["ECB_FX_RAW_TARGET_DIR"] = var_lib.ECB_FX_RAW_TARGET_DIR
os.environ["ECB_FX_WATERMARK_FILENAME"] = var_lib.ECB_FX_WATERMARK_FILENAME

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from src.common.logger import logger
from src.common.timer import track_execution_time
from src.bronze.orchestrator import (
    run_taxi_pipeline,
    run_openaq_pipeline,
    run_worldbank_pipeline,
    run_ecb_pipeline,
)

with track_execution_time("Fabric Bronze Layer Full Ingestion"):
    logger.info("Starting World Bank GDP ingestion...")
    run_worldbank_pipeline(fallback_year=2009)

    logger.info("Starting ECB FX ingestion...")
    run_ecb_pipeline(fallback_start_date="2009-01-01")

    logger.info("Starting NYC Taxi ingestion...")
    run_taxi_pipeline(fallback_year=2009, fallback_month=1)

    logger.info("Starting OpenAQ ingestion...")
    run_openaq_pipeline(fallback_year=2016, fallback_month=1)


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
