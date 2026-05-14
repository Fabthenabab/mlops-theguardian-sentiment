# Lit MAX(date) depuis theguardian.articles (exclut les articles drift_ pour ne pas biaiser la date)*
#   READ   theguardian.articles  → fetch_last_article_date()
# Calcule les mois manquants entre cette date et aujourd'hui
# Fetche chaque mois manquant via fetch_archives()
#   GET content.guardianapis.com/search → fetch_archives()
# Filtre section "business"
# Transforme via transform_articles()
# Insère via insert_articles() — ON CONFLICT DO NOTHING (idempotent : peut être relancé sans risque de doublon)
#   WRITE  theguardian.articles  → insert_articles()
#   WRITE  theguardian.jobs      → update_job (done | error, articles_processed)

# _workers/fetch_worker.py

import os
import datetime
import pandas as pd
from dateutil.relativedelta import relativedelta

# ===============================
# Logging
# ================================
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("fetch_worker")
logger.setLevel(logging.INFO)

# ===========================
# ENV
# ===========================
SCHEMA = os.getenv("DB_SCHEMA", "theguardian")
JOB_ID = os.getenv("JOB_ID")


# ===========================
# RUN
# ===========================
def run(dry_run: bool = False, limit_months: int = None):
    logger.debug("fetch_worker started")
    engine = None

    try:
        from pipeline.core.src.sql import get_engine, fetch_job, update_job, fetch_last_article_date, insert_articles
        from pipeline.core.src.theguardian import fetch_archives
        from pipeline.core.src.sql import transform_articles

        engine = get_engine()

        if JOB_ID:
            job = fetch_job(engine, job_id=JOB_ID)
            logger.info(f"Running job: {job['job_id']} — status: {job['status']}")

        # Last date in DB
        last_date = fetch_last_article_date(engine, schema=SCHEMA)
        today = datetime.date.today()

        if last_date is None:
            logger.warning("No articles in base — nothing to fetch incrementally")
            if JOB_ID:
                update_job(engine, JOB_ID, "done",
                        finished_at=datetime.datetime.now(datetime.UTC),
                        articles_processed=0)
            return

        # Missing months between last date and today
        current = last_date.replace(day=1)
        months_to_fetch = []
        while current <= today.replace(day=1):
            months_to_fetch.append((current.year, current.month))
            current += relativedelta(months=1)

        if limit_months:
            months_to_fetch = months_to_fetch[:limit_months]
            logger.info(f"Limit applied — fetching {limit_months} months only")

        logger.info(f"Months to fetch: {len(months_to_fetch)}")
        
        total_inserted = 0

        for year, month in months_to_fetch:
            logger.info(f"Fetching {year}/{month:02d}...")
            df_raw = fetch_archives(year, month)

            # Filter business section
            mask = df_raw["sectionName"] == "Business"
            df_business = df_raw.loc[mask, ["id", "webPublicationDate",
                                            "webTitle", "fields.trailText",
                                            "fields.bodyText"]].copy()

            if df_business.empty:
                logger.info(f"No business articles for {year}/{month:02d}")
                continue

            df_transformed = transform_articles(df_business)
            if dry_run:
                logger.info(f"Dry run — would insert {len(df_transformed)} articles")
                continue
            inserted = insert_articles(engine, df_transformed, schema=SCHEMA)
            total_inserted += inserted
            logger.info(f"Inserted {inserted} articles for {year}/{month:02d}")

        logger.info(f"fetch_worker done — {total_inserted} articles inserted")

        if JOB_ID:
            update_job(engine, JOB_ID, "done",
                    finished_at=datetime.datetime.now(datetime.UTC),
                    articles_processed=total_inserted)

    except Exception as e:
        logger.error(f"fetch_worker failed: {e}")
        if JOB_ID and engine:
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Fetch without inserting in database"
    )
    parser.add_argument(
        "--limit-months",
        type=int,
        default=None,
        help="Limit number of months to fetch (for testing)"
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run, limit_months=args.limit_months)