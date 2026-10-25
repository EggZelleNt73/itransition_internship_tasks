import numpy as np
import pandas as pd
import scipy.stats as stats
from src.logger import logger
from src.constants import AnomalyDetectionConstants as ADCONST


def detect_iqr_outliers(series: pd.DataFrame, k=ADCONST.DEFAULT_IQR_K_VALUE) -> pd.Series:
    logger.info("Detecting IQR outliers...")
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - k * iqr
    upper_bound = q3 + k * iqr
    return (series < lower_bound) | (series > upper_bound)


def detect_zscore_outliers(series: pd.DataFrame, threshold:float=ADCONST.DEFAULT_ZSCORE_THRESHOLD) -> pd.Series:
    logger.info("Detecting Z score outliers...")
    z_scores = np.abs(stats.zscore(series, nan_policy="omit"))
    return pd.Series(z_scores > threshold, index=series.index )


def detect_ma_distance_outliers(series: pd.DataFrame, window: int=ADCONST.DEFAULT_MA_DISTANCE_WINDOW, threshold_pct: float=ADCONST.DEFAULT_MA_THRESHOLD) -> pd.Series:
    logger.info("Detecting MA distance outliers...")
    rolling_mean = series.rolling(window=window, min_periods=ADCONST.DEFAULT_MA_ROLLING_MIN_PERIOD).mean()
    pct_dist = (np.abs(series - rolling_mean) / rolling_mean) * ADCONST.HUNDRED_PERCENT
    return pct_dist > threshold_pct


def detect_grubbs_outliers(series: pd.DataFrame, alpha=ADCONST.DEFAULT_GRUBBS_ALPHA_VALUE) -> pd.Series:
    logger.info("Detecting Grubbs outliers...")
    outliers = pd.Series(False, index=series.index)
    data_working = series.copy()

    while True:
        n = len(data_working.dropna())
        if n < 3:
            break
        mean = data_working.mean()
        std = data_working.std()
        if std == 0:
            break

        absolute_deviations = np.abs(data_working - mean)
        max_idx = absolute_deviations.idxmax()
        g_calc = absolute_deviations[max_idx] / std

        t_dist = stats.t.ppf(1 - alpha / (2 * n), n - 2)
        numerator = (n - 1) * np.sqrt(np.square(t_dist))
        denominator = np.sqrt(n * (n - 2) + n * np.square(t_dist))
        g_crit = numerator / denominator

        if g_calc > g_crit:
            outliers[max_idx] = True
            data_working[max_idx] = np.nan
        else:
            break
    
    return outliers


if __name__ == "__main__":
    pass