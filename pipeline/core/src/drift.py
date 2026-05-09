# pipeline/core/src/drift.py
# Library responsible for drift testing operations with Evidently
# Saves window reference to s3
# Loads reference from s3
# Compute drift with evidently

import pandas as pd


# ===============================
# Logging
# ================================
import os
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ===============================
# CONFIG
# ================================
DRIFT_THRESHOLD_LABEL = float(os.getenv("DRIFT_THRESHOLD_LABEL", 0.10))
DRIFT_THRESHOLD_SCORE = float(os.getenv("DRIFT_THRESHOLD_SCORE", 0.10))
S3_BUCKET = os.getenv("AWS_S3_BUCKET")
S3_REFERENCE = 'monitor/reference.parquet'

# ===============================
# S3
# ================================
from pipeline.libs.src.aws import save_parquet_to_s3, load_parquet_from_s3
from pipeline.libs.src.utils import get_project_name
from pathlib import Path
S3_KEY = f"{get_project_name()}/{S3_REFERENCE}"

def save_reference(df: pd.DataFrame):
    logger.debug("function save_reference")
    save_parquet_to_s3(df[["sentiment_label", "sentiment_score"]], S3_KEY)
    logger.info(f"Reference snapshot saved to s3://{S3_BUCKET}/{S3_KEY} ({len(df)} rows)")


def load_reference() -> pd.DataFrame:
    logger.debug("function load_reference")
    df = load_parquet_from_s3(S3_KEY)
    logger.info(f"Reference snapshot loaded from s3://{S3_BUCKET}/{S3_KEY} ({len(df)} rows)")
    return df

# ──────────────────────────────────────────────
#  Drift detection
# ──────────────────────────────────────────────

def compute_drift(current: pd.DataFrame, reference: pd.DataFrame) -> dict:
    """
    Compute drift between current and reference distributions
    using Evidently.

    Args:
        current   : DataFrame with columns [sentiment_label, sentiment_score]
        reference : DataFrame with columns [sentiment_label, sentiment_score]

    Returns:
        dict with keys:
            drift       : bool — drift detected
            drift_score : float — max drift score across monitored columns
            details     : dict — per-column drift scores
    """
    logger.debug("function compute_drift")
    from evidently.report import Report
    from evidently.metric_preset import DataDriftPreset

    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=reference, current_data=current)

    result = report.as_dict()

    drift_by_column = result["metrics"][0]["result"].get("drift_by_columns", {})

    score_label = drift_by_column.get("sentiment_label", {}).get("drift_score", 0.0)
    score_score = drift_by_column.get("sentiment_score", {}).get("drift_score", 0.0)

    drift_score = max(score_label, score_score)
    drift = (
        score_label > DRIFT_THRESHOLD_LABEL or
        score_score > DRIFT_THRESHOLD_SCORE
    )

    logger.info(f"Drift — label: {score_label} (thr: {DRIFT_THRESHOLD_LABEL}) | score: {score_score} (thr: {DRIFT_THRESHOLD_SCORE}) | drift: {drift}")

    return {
        "drift":       drift,
        "drift_score": drift_score,
        "details": {
            "sentiment_label": score_label,
            "sentiment_score": score_score
        }
    }