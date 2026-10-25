from src.pipeline.extract.extraction import load_mining_data
import os
from src.web_interface import load_web_page
from src.enums import EnvVariables
from src.logger import logger
import streamlit as st
from src.configs import PAGE_CONFIG


def main():
    st.set_page_config(page_title=PAGE_CONFIG["page_title"], layout="wide")
    st.title(PAGE_CONFIG["title"])
    st.subheader("Mining Operations Analytics & Anomaly Detection Center")

    with st.spinner("Accessing Weyland-Yutani Core Data Feeds..."):
        try:
            extracted_data = load_mining_data(os.getenv(EnvVariables.GOOGLE_SHEET_URL))
        except Exception as e:
            logger.error(f"Critical Ingestion Connection Failure: {e}")
            st.error(f"Secure Core Connection Failure: {e}")
            return
        
    if (extracted_data is not None) and (not extracted_data.empty):
        logger.info("Loading web page...")
        load_web_page(extracted_data)
    else:
        logger.warning("Extracted matrix is vacant. Processing halted.")
        st.error("Operational Log Empty: The target data source contains no extractable resource data grids.")
        st.info("Verify your application configuration parameters or Azure Key Vault secret strings.")


if __name__ == "__main__":
    main()
