# _workers/monitor_worker.py

# Fonction : monitoring de drift Evidently sur les scores de sentiment FinBERT 
# 2 MODES : snapshot (sauvegarde référence) et compare (détection de drift)
# le mode est passé par argparse
#
# Lit JOB_ID depuis l'environnement
# Crée le moteur PostgreSQL
# Fetch le job depuis theguardian.jobs pour log
#   READ   theguardian.jobs      → fetch_job (log du statut)
#
# MODE snapshot
#   Fetch les articles traités sur la fenêtre de référence (REFERENCE_WINDOW_DAYS=60j)
#       READ   theguardian.articles  → fetch_processed_for_drift(sentiment_label, sentiment_score sur fenêtre glissante 60j)
#   Sauvegarde le DataFrame [sentiment_label, sentiment_score] en parquet sur S3
#   Écrit une ligne dans theguardian.monitor (mode=snapshot, drift=False, score=0.0)
#       WRITE  theguardian.monitor   → write_monitor (job_id, mode, drift, drift_score)
#   Met à jour le job done ou error
#       WRITE  theguardian.jobs      → update_job (status: done | error) 
# ===========================
# MODE compare
#   Fetch les articles traités sur la fenêtre d'observation (OBSERVATION_WINDOW_DAYS=14j)
#       READ   theguardian.articles  → fetch_processed_for_drift(sentiment_label, sentiment_score sur fenêtre glissante 14j)
#   Charge la référence parquet depuis S3
#   Calcule le drift Evidently (DataDriftPreset) entre current et reference
#   Écrit le résultat dans theguardian.monitor (drift=True/False, drift_score)
#       WRITE  theguardian.monitor   → write_monitor (job_id, mode, drift, drift_score)
#   Met à jour le job done ou error
#       WRITE  theguardian.jobs      → update_job (status: done | error)

import os
import logging
import pandas as pd
from pipeline.core.src.sql import get_engine

# ===========================
# LOGGING
# ===========================
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("monitor_worker")

# ===========================
# ENV
# ===========================
SCHEMA       = os.getenv("DB_SCHEMA", "theguardian")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")
AWS_REGION = os.getenv("AWS_REGION")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

REFERENCE_WINDOW_DAYS = 60
OBSERVATION_WINDOW_DAYS = 14

# JOB_ID
# Define WORKER context
# Interaction avec theguardian.jobs
from pipeline.core.src.sql import fetch_job, update_job
import datetime
# Get JOB_ID passed to sub process in worker's parent process run_router
JOB_ID = os.getenv("JOB_ID")

# ===========================
# RUN
# ===========================
def run(mode):
    logger.info("monitor_worker started")
    engine = None
    try:
        from pipeline.core.src.sql import fetch_processed_for_drift, write_monitor
        from pipeline.core.src.drift import save_reference, load_reference, compute_drift
        
        engine = get_engine()
        if JOB_ID:
            job = fetch_job(engine, job_id=JOB_ID)
            logger.info(f"Running job: {job['job_id']} — status: {job['status']}")
        
        if mode == "snapshot":
            # Fetch from DB last processed articles (sliding window)
            # Serialize the df as a reference in S3 bucket (use drift.py module and don't serialize directly)
            
            # Get last processed (use REFERENCE_WINDOW_DAYS days default window size)
            last_processed = fetch_processed_for_drift(engine=engine, days=REFERENCE_WINDOW_DAYS, schema=SCHEMA)
            # Save to S3 via drift module 
            save_reference(last_processed)
            write_monitor(engine, job_id=JOB_ID or "manual",
                        mode="snapshot", drift=False, drift_score=0.0)
            
        else:
            # Fetch from DB last processed articles (sliding window)
            # Load reference from S3 bucket
            # Test drift by function call compute_drit in pinpeline drift.py
            # Write result in DB .monitor table
            # Update DB .jobs status of the current worker
            
            # Get current (use OBSERVATION_WINDOW_DAYS days window size)
            last_processed = fetch_processed_for_drift(engine=engine, days=OBSERVATION_WINDOW_DAYS, schema=SCHEMA)
            # Load reference from S3
            reference = load_reference()
            # Compute drift
            compute_result = compute_drift(last_processed, reference)
            write_monitor(engine, job_id=JOB_ID or "manual",
                         mode="compare",
                         drift=compute_result["drift"],
                         drift_score=compute_result["drift_score"])
        
        if JOB_ID:
            update_job(engine, JOB_ID, "done", finished_at=datetime.datetime.now(datetime.UTC))
        
    except Exception as e:
        if JOB_ID:
            update_job(engine, JOB_ID, "error",
                      finished_at=datetime.datetime.now(datetime.UTC),
                      error=str(e))
        raise

# ===========================
# MAIN
# ===========================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    # mode need to be passed as "snapshot" or "compare"
    parser.add_argument(
        "--mode",
        type=str,
        choices=["snapshot", "compare"],
        default="snapshot",
        help="Task attributed to the worker"
    )   
    args = parser.parse_args()
    run(mode=args.mode)