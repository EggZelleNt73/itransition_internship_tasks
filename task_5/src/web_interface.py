import streamlit as st
import os
import pandas as pd
from src.configs import PAGE_CONFIG
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import jinja2
import weasyprint
from src.pipeline.aggregation.anomally_detection import (
    detect_iqr_outliers,
    detect_zscore_outliers,
    detect_ma_distance_outliers,
    detect_grubbs_outliers
)
from pathlib import Path
from src.enums import EnvVariables


def load_web_page(data: pd.DataFrame):
    if st.sidebar.button("🔄 Sync Live Sheet Data"):
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.header("Global Configuration System")
    target_mine = st.sidebar.selectbox("Select Target Mine Asset", data.columns)
    chart_type = st.sidebar.selectbox("Visualization View Model", ["Line Profile", "Bar Spectrum", "Stacked Corporation Composite"])
    poly_degree = st.sidebar.slider("Polynomial Trendline Order (Degree)", 1, 4, 1)

    st.sidebar.markdown("---")
    st.sidebar.subheader("Anomaly Core Directives")
    iqr_k = st.sidebar.slider("IQR Range Rule Multiplier (k)", 1.0, 3.5, 1.5, step=0.1)
    z_thresh = st.sidebar.slider("Z-Score Sigma Threshold", 1.5, 4.5, 3.0, step=0.1)
    ma_win = st.sidebar.slider("Moving Average Window (Days)", 3, 21, 7)
    ma_dist = st.sidebar.slider("MA Deviation Threshold %", 5.0, 50.0, 20.0, step=1.0)
    grubbs_alpha = st.sidebar.slider("Grubbs Significance Level (α)", 0.01, 0.10, 0.05, step=0.01)

    y_series = data[target_mine].dropna()
    x_dates = y_series.index

    outliers_iqr = detect_iqr_outliers(y_series, k=iqr_k)
    outliers_z = detect_zscore_outliers(y_series, threshold=z_thresh)
    outliers_ma = detect_ma_distance_outliers(y_series, window=ma_win, threshold_pct=ma_dist)
    outliers_grubbs = detect_grubbs_outliers(y_series, alpha=grubbs_alpha)

    anomaly_method = st.selectbox("Active Primary Outlier Flag Engine", ["IQR Rule", "Z-Score Exception", "Moving Average Drift", "Grubbs Isolated Target"])
    outlier_mask = {
        "IQR Rule": outliers_iqr,
        "Z-Score Exception": outliers_z,
        "Moving Average Drift": outliers_ma,
        "Grubbs Isolated Target": outliers_grubbs
    }[anomaly_method]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Mean Daily Output", f"{y_series.mean():.2f} tons")
    col2.metric("Standard Deviation (σ)", f"{y_series.std():.2f}")
    col3.metric("Median (Q2 Horizon)", f"{y_series.median():.2f} tons")

    iqr_val = y_series.quantile(0.75) - y_series.quantile(0.25)
    iqr_delta = y_series.quantile(0.75) - iqr_val
    col4.metric("Interquartile Range (IQR)", f"{iqr_delta:.2f}")

    x_numeric = np.arange(len(y_series))
    coefficients = np.polyfit(x_numeric, y_series.values, poly_degree)
    poly_func = np.poly1d(coefficients)
    trend_curve = poly_func(x_numeric)

    fig = go.Figure()
    if chart_type == "Line Profile":
        fig.add_trace(go.Scatter(x=x_dates, y=y_series, mode='lines', name=target_mine, line=dict(color='#3498db', width=2)))
    elif chart_type == "Bar Spectrum":
        fig.add_trace(go.Bar(x=x_dates, y=y_series, name=target_mine, marker_color='#2c3e50'))
    elif chart_type == "Stacked Corporation Composite":
        for col in data.columns[:-1]:
            fig.add_trace(go.Bar(x=data.index, y=data[col], name=col))
        fig.update_layout(barmode='stack')

    fig.add_trace(go.Scatter(x=x_dates, y=trend_curve, mode='lines', name=f'Poly Degree {poly_degree} Trend', line=dict(color=PAGE_CONFIG["accent"], dash='dash')))
    fig.add_trace(go.Scatter(x=x_dates[outlier_mask], y=y_series[outlier_mask], mode='markers', name='Flagged Outlier', marker=dict(color=PAGE_CONFIG["anomaly"], size=10, symbol='x')))

    fig.update_layout(template="plotly_dark", title=f"Time Series Extract Profile: {target_mine}", xaxis_title="Operational Timeline Horizon", yaxis_title="Resource Metric Quantities (Tons)")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Executive Documentation Command")

    if st.button("Generate Detailed Corporate PDF Audit Report"):
        html_template_path = Path(__file__).parent / os.getenv(EnvVariables.PDF_TEMPLATE_NAME)
        if html_template_path.exists():
            anomaly_list = [{"date": str(dt.date()), "value": f"{val:.2f}"} for dt, val in y_series[outlier_mask].items()]
            html_template = html_template_path.read_text(encoding="utf-8")
            template_render = jinja2.Template(html_template).render(
                mine_id=target_mine,
                mean=f"{y_series.mean():.2f}",
                std=f"{y_series.std():.2f}",
                median=f"{y_series.median():.2f}",
                iqr=f"{iqr_delta:.2f}",
                method=anomaly_method,
                anomalies=anomaly_list
            )
        pdf_bytes = weasyprint.HTML(string=template_render).write_pdf()

        st.download_button(
            label="Download Polished PDF Document",
            data=pdf_bytes,
            file_name=f"WeylandYutani_{target_mine}_AuditReport.pdf",
            mime="application/pdf"
        )


if __name__ == "__main__":
    pass
