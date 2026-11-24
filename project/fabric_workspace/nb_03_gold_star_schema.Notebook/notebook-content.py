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

os.environ["GOLD_DIM_DATE_TABLE"] = var_lib.GOLD_DIM_DATE_TABLE
os.environ["GOLD_DIM_MACRO_TABLE"] = var_lib.GOLD_DIM_MACRO_TABLE
os.environ["GOLD_DIM_LOCATION_TABLE"] = var_lib.GOLD_DIM_LOCATION_TABLE
os.environ["GOLD_FACT_MOBILITY_ENV_TABLE"] = var_lib.GOLD_FACT_MOBILITY_ENV_TABLE

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from src.common.timer import track_execution_time
from src.gold.build_dimensions import build_dim_date_and_macro, build_dim_location
from src.gold.build_fact_mobility_env import build_fact_mobility_env

with track_execution_time("Fabric Gold Layer Star Schema Build"):
    build_dim_date_and_macro(spark)
    build_dim_location(spark)
    build_fact_mobility_env(spark)


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
