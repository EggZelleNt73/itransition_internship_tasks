import streamlit as st
import pandas as pd
import numpy as np
from src.logger import logger


@st.cache_data(ttl=60)
def load_mining_data(url) -> pd.DataFrame:
    logger.info("Extracting data from google sheet...")
    try:
        df = pd.read_csv(url)
        date_series = pd.to_datetime(df.iloc[:, 0], errors='coerce')
        df_metrics = df.iloc[:, 1:].copy()
        df_metrics.index = date_series
        df_metrics.index.name = "Date"
        df_metrics = df_metrics[df_metrics.index.notna()]
        df_metrics = df_metrics.dropna(how='all', axis=0)
        df_metrics = df_metrics.apply(pd.to_numeric, errors='coerce')
        df_metrics = df_metrics.select_dtypes(include=[np.number])
        df_metrics = df_metrics.loc[:, ~df_metrics.columns.str.contains('^Unnamed')]
        df_metrics["Total Corporate Output"] = df_metrics.sum(axis=1)
        logger.info("Successfully loaded data from google sheet and convert it into dataframe")
        return df_metrics
    except Exception as e:
        logger.error(f"Ingestion Connection Failure: {e}")
        return pd.DataFrame


if __name__ == "__main__":
    pass