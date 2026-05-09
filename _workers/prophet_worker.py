# _workers/prophet_worker.py

import os
import logging
import mlflow
import mlflow.prophet
import pandas as pd
from prophet import Prophet
from pipeline.core.src.sql import get_engine

# ===========================
# LOGGING
# ===========================
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("prophet_worker")


# ===========================
# ENV
# ===========================
SCHEMA       = os.getenv("DB_SCHEMA", "theguardian")
HORIZON_DAYS = int(os.getenv("HORIZON_DAYS", 30))
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI")
EXPERIMENT_NAME = os.getenv("EXPERIMENT_NAME")
RUN_NAME = os.getenv("RUN_NAME")
MODEL_NAME = os.getenv("MODEL_NAME")
MODEL_ALIAS = os.getenv("MODEL_ALIAS")

# JOB_ID
# Define WORKER context
# Interaction avec theguardian.jobs
from pipeline.core.src.sql import fetch_job, update_job
import datetime
# Get JOB_ID passed to sub process in worker's parent process run_router
JOB_ID = os.getenv("JOB_ID")


# ===========================
# LOCAL FUNCTIONS
# ===========================
def _fetch_weekly_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute processed articles, signed score, aggregate weekly.
    Returns DataFrame with columns [ds, y] ready for Prophet.
    """
    # Score signé
    df["y"] = df["sentiment_score"] * df["sentiment_label"].map({
        "positive":  1,
        "negative": -1,
        "neutral":   0
    })

    # Agrégation hebdomadaire
    df["date"] = pd.to_datetime(df["date"])
    weekly = (
        df.set_index("date")
        .resample("W")["y"]
        .mean()
        .reset_index()
        .rename(columns={"date": "ds"})
    )

    logger.info("Weekly sentiment: %d weeks", len(weekly))
    return weekly


# ===========================
# RUN
# ===========================
def run(retrain, horizon_days: int = HORIZON_DAYS):
    logger.info("prophet_worker started")
    engine = None
    try:
        from pipeline.core.src.sql import fetch_processed
        
        engine = get_engine()
        if JOB_ID:
            job = fetch_job(engine, job_id=JOB_ID)
            logger.info(f"Running job: {job['job_id']} — status: {job['status']}")

        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(EXPERIMENT_NAME)
        
        articles = fetch_processed(engine=engine, schema=SCHEMA)
        weekly = _fetch_weekly_sentiment(articles)

        if weekly.empty:
            logger.info("No processed articles — nothing to do")
            return

        with mlflow.start_run(run_name=RUN_NAME):
            model = Prophet()
            model.fit(weekly)

            future   = model.make_future_dataframe(periods=horizon_days)
            forecast = model.predict(future)
            forecast["label"] = "economic_sentiment"

            # Metrics
            from sklearn.metrics import mean_absolute_error
            fitted = forecast.loc[forecast["ds"].isin(weekly["ds"]), "yhat"]
            mae    = mean_absolute_error(weekly["y"], fitted)

            mlflow.log_param("granularity",    "weekly")
            mlflow.log_param("horizon_days",   horizon_days)
            mlflow.log_param("history_start",  str(weekly["ds"].min()))
            mlflow.log_param("history_end",    str(weekly["ds"].max()))
            mlflow.log_metric("mae",           mae)
            
            # Log model without registering in registry
            mlflow.prophet.log_model(model, name=MODEL_NAME)
            run_id = mlflow.active_run().info.run_id
            
            
            # WRITE PROPHET FORECASTS
            # Persist predictions for this run_id in Database
            from pipeline.core.src.sql import write_forecasts
            import datetime
            run_date = datetime.date.today()
            write_forecasts(engine, forecast, run_id=run_id, run_date=run_date, schema=SCHEMA)
            
            # Set tag
            mlflow.set_tag("triggered_by", retrain)
            
            # Register model
            model_uri = f"runs:/{run_id}/{MODEL_NAME}"
            mv = mlflow.register_model(model_uri, name=MODEL_NAME)

            # Alias
            client = mlflow.MlflowClient()
            client.set_registered_model_alias(
                name=MODEL_NAME,
                alias=MODEL_ALIAS,
                version=mv.version
            )

            logger.info(f"Model v{mv.version} triggered by {retrain} - promoted to @{MODEL_ALIAS} — run_id: {run_id}")
        if JOB_ID:
                update_job(engine, JOB_ID, "done",
                        finished_at=datetime.datetime.now(datetime.UTC),
                        articles_processed=len(articles))
        logger.info("prophet_worker done")
    
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
    # retrain used to store the condtion of retrain in mlflow : retrain because of trigger by evidently or retrain because of schedule
    # retrain need to be passed as "scheduled" or "evidently_drift"
    parser.add_argument(
        "--retrain",
        type=str,
        choices=["scheduled", "evidently_drift"],
        default="scheduled",
        help="Origin of the retrain run"
    )   
    parser.add_argument("--horizon-days", type=int, default=HORIZON_DAYS)
    args = parser.parse_args()
    run(retrain=args.retrain, horizon_days=args.horizon_days)