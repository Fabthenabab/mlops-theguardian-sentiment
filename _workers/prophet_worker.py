# _workers/worker_prophet.py

import os
import logging
import mlflow
import mlflow.prophet
import pandas as pd
from prophet import Prophet
from pipeline.core.src.sql import get_engine

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("worker_prophet")

SCHEMA       = os.getenv("DB_SCHEMA", "theguardian")
HORIZON_DAYS = int(os.getenv("HORIZON_DAYS", 30))
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI")
EXPERIMENT_NAME = os.getenv("EXPERIMENT_NAME")
RUN_NAME = os.getenv("RUN_NAME")
MODEL_NAME = os.getenv("MODEL_NAME")
MODEL_ALIAS = os.getenv("MODEL_ALIAS")


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


def run(horizon_days: int = HORIZON_DAYS):
    from pipeline.core.src.sql import fetch_processed
    
    logger.info("worker_prophet started")

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    engine = get_engine()
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

        # Métriques
        from sklearn.metrics import mean_absolute_error
        fitted = forecast.loc[forecast["ds"].isin(weekly["ds"]), "yhat"]
        mae    = mean_absolute_error(weekly["y"], fitted)

        mlflow.log_param("granularity",    "weekly")
        mlflow.log_param("horizon_days",   horizon_days)
        mlflow.log_param("history_start",  str(weekly["ds"].min()))
        mlflow.log_param("history_end",    str(weekly["ds"].max()))
        mlflow.log_metric("mae",           mae)
        
        mv = mlflow.prophet.log_model(model,    name=MODEL_NAME)

        # Model alias
        client = mlflow.MlflowClient()
        version = mv.model_versions[0].version
        client.set_registered_model_alias(
            name=MODEL_NAME,
            alias=MODEL_ALIAS,
            version=version
        )

        run_id = mlflow.active_run().info.run_id
        logger.info(f"MLflow run {RUN_NAME} logged — run_id: {run_id}. Model v{version} promoted to {MODEL_ALIAS}")

    logger.info("worker_prophet done")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon-days", type=int, default=HORIZON_DAYS)
    args = parser.parse_args()
    run(horizon_days=args.horizon_days)