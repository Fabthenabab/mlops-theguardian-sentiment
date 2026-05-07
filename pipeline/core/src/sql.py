import pandas as pd
# ===============================
# Logging
# ================================
import os
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("pipeline_sql")
logger.setLevel(logging.INFO)

# ===============================
# Env
# ================================
from dotenv import load_dotenv

load_dotenv()

DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_SCHEMA = os.getenv("DB_SCHEMA", "theguardian")


from datetime import datetime, timezone
from sqlalchemy import create_engine, text


# ──────────────────────────────────────────────
#  Engine
# ──────────────────────────────────────────────

def get_engine():
    """Return a SQLAlchemy engine connected to Neon PostgreSQL."""
    endpoint_id = DB_HOST.split(".")[0] if DB_HOST else None
    url = (
        f"postgresql://{DB_USERNAME}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        f"?sslmode=require&options=endpoint%3D{endpoint_id}"
    )
    engine = create_engine(url, pool_pre_ping=True)
    logger.info("Engine created — %s@%s/%s", DB_USERNAME, DB_HOST, DB_NAME)
    return engine


# ──────────────────────────────────────────────
#  Schema & tables
# ──────────────────────────────────────────────

_ARTICLE_COLUMNS = """
    id               VARCHAR(200) PRIMARY KEY,
    date             DATE,
    text             TEXT,
    sentiment_label  VARCHAR(20),
    sentiment_score  FLOAT,
    created_at       TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'utc')
"""

TABLES_SQL = {
    "articles": f"""
        CREATE TABLE IF NOT EXISTS {{schema}}.articles (
            {_ARTICLE_COLUMNS}
        )
    """,
}

INDEXES_SQL = [
    f"CREATE INDEX IF NOT EXISTS idx_articles_date      ON {DB_SCHEMA}.articles (date)",
    f"CREATE INDEX IF NOT EXISTS idx_articles_created   ON {DB_SCHEMA}.articles (created_at)",
    f"CREATE INDEX IF NOT EXISTS idx_articles_sentiment ON {DB_SCHEMA}.articles (sentiment_label)",
]

def create_schema(engine, schema=DB_SCHEMA):
    """Drop schema if exists, then recreate it clean."""
    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
        logger.info("Dropped schema %s", schema)
        conn.execute(text(f"CREATE SCHEMA {schema}"))
        logger.info("Created schema %s", schema)


# Initial creation
def create_tables(engine, schema=DB_SCHEMA):
    """Drop then create tables + respective indexes in TABLES_SQL + INDEXES_SQL."""
    with engine.begin() as conn:
        for name in reversed(list(TABLES_SQL.keys())):
            conn.execute(text(f"DROP TABLE IF EXISTS {schema}.{name} CASCADE"))
            logger.info("Dropped table: %s.%s", schema, name)
        for name, ddl in TABLES_SQL.items():
            conn.execute(text(ddl.format(schema=schema)))
            logger.info("Created table: %s.%s", schema, name)
        for idx in INDEXES_SQL:
            conn.execute(text(idx.format(schema=schema)))
        logger.info("Indexes ready")


# New table creation - Done separately because we don't want to re-receate everything (and drop tables first..)
def create_table_forecasts(engine, schema=DB_SCHEMA):
    """Create theguardian.forecasts table if not exists."""
    stmt = text(f"""
        CREATE TABLE IF NOT EXISTS {schema}.forecasts (
            id         SERIAL PRIMARY KEY,
            run_id     VARCHAR(100),
            run_date   DATE,
            ds         DATE,
            yhat       FLOAT,
            yhat_lower FLOAT,
            yhat_upper FLOAT,
            created_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'utc')
        )
    """)
    with engine.begin() as conn:
        conn.execute(stmt)
    logger.info("Table ready: %s.forecasts", schema)

# New table creation - Done separately because we don't want to re-receate everything (and drop tables first..)
def create_table_jobs(engine, schema=DB_SCHEMA):
    """Create theguardian.jobs table if not exists."""
    stmt = text(f"""
        CREATE TABLE IF NOT EXISTS {schema}.jobs (
            job_id             VARCHAR(36) PRIMARY KEY,
            worker             VARCHAR(50),
            status             VARCHAR(20),
            started_at         TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'utc'),
            finished_at        TIMESTAMP,
            error              TEXT,
            articles_processed INTEGER
        )
    """)
    with engine.begin() as conn:
        conn.execute(stmt)
    logger.info("Table ready: %s.jobs", schema)


def init_db(engine=None, schema=DB_SCHEMA):
    """Drop everything, recreate schema + tables."""
    engine = engine or get_engine()
    create_schema(engine, schema)
    create_tables(engine, schema)
    #create_table_forecasts(engine, schema)
    return engine

# ──────────────────────────────────────────────
#  ARTICLES
# ──────────────────────────────────────────────
def transform_articles(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare a raw The Guardian archive DataFrame for insertion into theguardian.articles.

    Input columns expected : id, webPublicationDate, webTitle, fields.trailText, fields.bodyText
    Output columns         : id, date, text
    Sentiment columns (sentiment_label, sentiment_score) are left absent —
    they will be filled later by the FinBERT worker.
    """
    logger.info("function transform_articles")
    df = df.copy()

    expected_cols = ["id", "webPublicationDate", "webTitle", "fields.trailText", "fields.bodyText"]
    df = df.loc[:, expected_cols].copy()

    # Transform pub_date into useable format
    df["date"] = pd.to_datetime(df["webPublicationDate"]).dt.date
    df.drop(columns=["webPublicationDate"], inplace=True)

    # Concat snippet & lead_paragraph
    df["text"] = df['webTitle'] + '. ' + df['fields.trailText'] + '. ' + df['fields.bodyText']
    df.drop('webTitle', axis=1, inplace=True)
    df.drop('fields.trailText', axis=1, inplace=True)
    df.drop('fields.bodyText', axis=1, inplace=True)

    return df


def insert_articles(engine, df: pd.DataFrame, schema=DB_SCHEMA) -> int:
    """
    Insert a transformed DataFrame into theguardian.articles.
    Skips rows whose uri already exists (ON CONFLICT DO NOTHING).

    Args:
        engine : SQLAlchemy engine
        df     : DataFrame with columns [id, date, text]
        schema : target schema

    Returns:
        Number of rows inserted.
    """
    logger.info("function insert_articles")
    if df.empty:
        logger.info("insert_articles: empty DataFrame, nothing to insert")
        return 0

    rows = df.to_dict(orient="records")
    stmt = text(f"""
        INSERT INTO {schema}.articles (id, date, text)
        VALUES (:id, :date, :text)
        ON CONFLICT (id) DO NOTHING
    """)

    with engine.begin() as conn:
        result = conn.execute(stmt, rows)

    inserted = result.rowcount
    logger.info("Inserted %d / %d rows into %s.articles", inserted, len(df), schema)
    return inserted


def update_sentiment(engine, id: str, label: str, score: float, schema=DB_SCHEMA):
    """
    Update sentiment_label and sentiment_score for a single article.

    Called by the FinBERT worker after inference.
    """
    logger.info("function update_sentiment")
    stmt = text(f"""
        UPDATE {schema}.articles
        SET sentiment_label = :label,
            sentiment_score = :score
        WHERE id = :id
    """)
    with engine.begin() as conn:
        conn.execute(stmt, {"id": id, "label": label, "score": score})


def update_sentiment_batch(engine, records: list[dict], schema=DB_SCHEMA):
    """
    Batch update sentiment for multiple articles.

    Args:
        records : list of dicts with keys [id, label, score]
    """
    logger.info("function update_sentiment_batch")
    if not records:
        return

    stmt = text(f"""
        UPDATE {schema}.articles
        SET sentiment_label = :label,
            sentiment_score = :score
        WHERE id = :id
    """)
    with engine.begin() as conn:
        conn.execute(stmt, records)

    logger.info("Updated sentiment for %d articles in %s.articles", len(records), schema)



#  Fetch (pour le worker FinBERT)

def fetch_unprocessed(engine, schema=DB_SCHEMA) -> pd.DataFrame:
    """
    Return articles not yet processed by FinBERT (sentiment_label IS NULL).
    """
    logger.info("function fetch_unprocessed")
    stmt = text(f"""
        SELECT id, text
        FROM {schema}.articles
        WHERE sentiment_label IS NULL
        ORDER BY date
    """)
    with engine.connect() as conn:
        df = pd.read_sql(stmt, conn)

    logger.info("Fetched %d unprocessed articles from %s.articles", len(df), schema)
    return df


#  Fetch (pour prophet)

def fetch_processed(engine, schema=DB_SCHEMA) -> pd.DataFrame:
    """
    Return articles already processed by FinBERT (sentiment_label IS NOT NULL).
    """
    logger.info("function fetch_processed")
    stmt = text(f"""
        SELECT *
        FROM {schema}.articles
        WHERE sentiment_label IS NOT NULL
        ORDER BY date
    """)
    with engine.connect() as conn:
        df = pd.read_sql(stmt, conn)

    logger.info("Fetched %d already processed articles from %s.articles", len(df), schema)
    return df


# ──────────────────────────────────────────────
#  FORECASTS
# ──────────────────────────────────────────────

def write_forecasts(engine, forecast: pd.DataFrame, run_id: str, run_date, schema=DB_SCHEMA) -> int:
    """
    Write Prophet forecast rows into theguardian.forecasts

    Args:
        engine   : SQLAlchemy engine
        forecast : Prophet forecast DataFrame (ds, yhat, yhat_lower, yhat_upper)
        run_id   : MLflow run_id for traceability
        run_date : date of the Prophet run
        schema   : target schema

    Returns:
        Number of rows written.
    """
    logger.info("function write_forecasts")
    if forecast.empty:
        logger.info("write_forecasts: empty DataFrame, nothing to write")
        return 0

    df = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
    df["run_id"]   = run_id
    df["run_date"] = run_date
    df["ds"]       = pd.to_datetime(df["ds"]).dt.date

    rows = df.to_dict(orient="records")

    stmt = text(f"""
        INSERT INTO {schema}.forecasts (run_id, run_date, ds, yhat, yhat_lower, yhat_upper)
        VALUES (:run_id, :run_date, :ds, :yhat, :yhat_lower, :yhat_upper)
    """)

    with engine.begin() as conn:
        conn.execute(stmt, rows)

    logger.info("Wrote %d forecast rows into %s.forecasts (run_id: %s)", len(df), schema, run_id)
    return len(df)


def fetch_forecasts(engine, run_date=None, schema=DB_SCHEMA) -> pd.DataFrame:
    """
    Return Prophet forecasts for a given run_date.
    If run_date is None, returns the latest run.

    Args:
        engine   : SQLAlchemy engine
        run_date : date of the run (optional, defaults to latest)
        schema   : target schema

    Returns:
        DataFrame with columns [ds, yhat, yhat_lower, yhat_upper, run_id, run_date]
    """
    logger.info("function fetch_forecasts")
    # Get the last run if no date is provided
    if run_date is None:
        subquery = f"""
            SELECT run_id FROM {schema}.forecasts
            ORDER BY run_date DESC
            LIMIT 1
        """
    else:   # Get the closest to the provided date
        subquery = f"""
            SELECT run_id FROM {schema}.forecasts
            WHERE run_date <= :date
            ORDER BY run_date DESC
            LIMIT 1
        """

    stmt = text(f"""
        SELECT ds, yhat, yhat_lower, yhat_upper, run_id, run_date
        FROM {schema}.forecasts
        WHERE run_id = ({subquery})
        ORDER BY ds
    """)

    with engine.connect() as conn:
        df = pd.read_sql(stmt, conn, params={"date": run_date} if run_date else {})

    logger.info(f"Fetched {len(df)} forecast rows (run_date: {run_date or 'latest'})")
    return df


# ──────────────────────────────────────────────
#  JOBS
# ──────────────────────────────────────────────

def create_job(engine, job_id: str, worker: str, schema=DB_SCHEMA):
    """Insert a new job with status 'started'."""
    logger.info("function create_job")
    stmt = text(f"""
        INSERT INTO {schema}.jobs (job_id, worker, status)
        VALUES (:job_id, :worker, 'started')
    """)
    with engine.begin() as conn:
        conn.execute(stmt, {"job_id": job_id, "worker": worker})
    logger.info(f"Job created: {job_id} ({worker})")


def update_job(engine, job_id: str, status: str, schema=DB_SCHEMA, **kwargs):
    """
    Update job status and optional fields.
    kwargs: finished_at, error, articles_processed
    """
    logger.info("function update_job")
    fields = {"status": status}
    fields.update(kwargs)

    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    stmt = text(f"""
        UPDATE {schema}.jobs
        SET {set_clause}
        WHERE job_id = :job_id
    """)
    fields["job_id"] = job_id

    with engine.begin() as conn:
        conn.execute(stmt, fields)
    logger.info(f"Job updated: {job_id} → {status}")


def fetch_job(engine, job_id: str, schema=DB_SCHEMA) -> dict:
    """Return job status as dict."""
    logger.info("function fetch_job")
    stmt = text(f"""
        SELECT job_id, worker, status, started_at, finished_at,
               error, articles_processed
        FROM {schema}.jobs
        WHERE job_id = :job_id
    """)
    with engine.connect() as conn:
        row = conn.execute(stmt, {"job_id": job_id}).fetchone()

    if row is None:
        return {}

    return dict(row._mapping)