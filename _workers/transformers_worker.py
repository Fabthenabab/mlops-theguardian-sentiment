# _workers/transformers_worker.py

# Lit JOB_ID depuis l'environnement
# Crée le moteur PostgreSQL
# Fetch le job depuis theguardian.jobs pour log
#   READ   theguardian.jobs     → fetch_job (log du statut)
# Fetch les articles non traités (sentiment_label IS NULL)
#   READ   theguardian.articles → fetch_unprocessed (WHERE sentiment_label IS NULL)
# Applique optionnellement un --limit pour les tests
# Charge FinBERT depuis HuggingFace (@production ou Hub direct)
# Traite par batch de 32 articles (defaut = 32)
# Met à jour sentiment_label et sentiment_score par batch
#   WRITE  theguardian.articles → update_sentiment_batch (sentiment_label, sentiment_score)
# Met à jour le job done ou error dans theguardian.jobs
#   WRITE  theguardian.jobs     → update_job (status: done | error, articles processed)

import os
import logging
from transformers import pipeline
from pipeline.core.src.sql import get_engine, fetch_unprocessed, update_sentiment_batch

# Enable CLI arguments to be passed to internal run function
import argparse

# ===========================
# LOGGING
# ===========================
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("transformers_worker")


# ===========================
# ENV
# ===========================
SCHEMA = os.getenv("DB_SCHEMA", "theguardian")

# JOB_ID
# Define WORKER context
# Interaction with theguardian.jobs
from pipeline.core.src.sql import fetch_job, update_job
import datetime
# Get JOB_ID passed to sub process in worker's parent process run_router
JOB_ID = os.getenv("JOB_ID")


# ===========================
# RUN
# ===========================

def run(batch_size: int = 32, limit: int = None):
    # apply FinBERT to the body of an article stored in SQL DB
    # Proceed by batch processing
     # allow to limit the size of processed articles
    logger.debug("transformers_worker started")
    engine = None
    try:
        engine = get_engine()
        if JOB_ID:
            job = fetch_job(engine, job_id=JOB_ID)
            logger.info(f"Running job: {job['job_id']} — status: {job['status']}")
        
        articles = fetch_unprocessed(engine, schema=SCHEMA)

        if articles.empty:
            logger.info("No unprocessed articles — nothing to do")
            return

        if limit:
            articles = articles.iloc[:limit]
            logger.info(f"Limit applied — processing {limit} articles")

        logger.info("Loading FinBERT...")
        pipe = pipeline("text-classification", model="ProsusAI/finbert")

        total = len(articles)
        processed = 0

        for start in range(0, total, batch_size):
            batch = articles.iloc[start:start + batch_size]

            results = [
                pipe(text, truncation=True, max_length=512)[0]
                for text in batch["text"]
            ]

            records = [
                {"id": row["id"], "label": result["label"], "score": result["score"]}
                for row, result in zip(batch.to_dict(orient="records"), results)
            ]

            update_sentiment_batch(engine, records, schema=SCHEMA)
            processed += len(batch)
            logger.info(f"Progress: {processed} / {total}")
        
        if JOB_ID:
            update_job(engine, JOB_ID, "done",
                      finished_at=datetime.datetime.now(datetime.UTC),
                      articles_processed=processed)
        logger.info(f"transformers_worker done — {total} articles processed")
    
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--limit", type=int, default=None, help="Process N articles only (for testing)")
    args = parser.parse_args()
    run(batch_size=args.batch_size, limit=args.limit)