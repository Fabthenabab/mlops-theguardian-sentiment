# _workers/worker_transformers.py

import os
import logging
from transformers import pipeline
from pipeline.core.src.sql import get_engine, fetch_unprocessed, update_sentiment_batch

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("transformers_worker")

SCHEMA = os.getenv("DB_SCHEMA", "theguardian")


# Enable CLI arguments to be passed to internal run function
import argparse

def run(batch_size: int = 32, limit: int = None):
    # apply FinBERT to the body of an article stored in SQL DB
    # Proceed by batch processing
    logger.info("worker_transformers started")

    engine = get_engine()
    articles = fetch_unprocessed(engine, schema=SCHEMA)

    if articles.empty:
        logger.info("No unprocessed articles — nothing to do")
        return

    if limit:
        articles = articles.iloc[:limit]
        logger.info("Limit applied — processing %d articles", limit)

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
        logger.info("Progress: %d / %d", processed, total)

    logger.info("worker_transformers done — %d articles processed", total)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--limit", type=int, default=None, help="Process N articles only (for testing)")
    args = parser.parse_args()
    run(batch_size=args.batch_size, limit=args.limit)