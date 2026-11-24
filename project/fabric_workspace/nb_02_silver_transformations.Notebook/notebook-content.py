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
os.environ["SILVER_TAXI_TABLE"] = var_lib.SILVER_TAXI_TABLE
os.environ["SILVER_AIR_QUALITY_TABLE"] = var_lib.SILVER_AIR_QUALITY_TABLE
os.environ["SILVER_MACRO_TABLE"] = var_lib.SILVER_MACRO_TABLE

os.environ["NYC_TAXI_RAW_TARGET_DIR"] = var_lib.NYC_TAXI_RAW_TARGET_DIR
os.environ["OPENAQ_RAW_TARGET_DIR"] = var_lib.OPENAQ_RAW_TARGET_DIR
os.environ["WORLDBANK_RAW_TARGET_DIR"] = var_lib.WORLDBANK_RAW_TARGET_DIR
os.environ["ECB_FX_RAW_TARGET_DIR"] = var_lib.ECB_FX_RAW_TARGET_DIR

os.environ["SILVER_WATERMARKS_PATH"] = var_lib.SILVER_WATERMARKS_PATH

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from src.common.timer import track_execution_time
from src.common.config import settings
from src.silver.transform_taxi import run_silver_taxi_transform
from src.silver.transform_openaq import run_silver_openaq_transform
from src.silver.transform_macro import run_silver_macro_transform

with track_execution_time("Fabric Silver Layer Transformations"):
    run_silver_macro_transform(spark, settings.ECB_FX_RAW_TARGET_DIR, settings.WORLDBANK_RAW_TARGET_DIR)
    run_silver_openaq_transform(spark, settings.OPENAQ_RAW_TARGET_DIR, settings.SILVER_WATERMARKS_PATH)
    run_silver_taxi_transform(spark, settings.NYC_TAXI_RAW_TARGET_DIR, settings.SILVER_WATERMARKS_PATH)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
