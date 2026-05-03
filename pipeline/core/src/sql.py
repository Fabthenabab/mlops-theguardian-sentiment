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
DB_SCHEMA = os.getenv("DB_SCHEMA", "nyt")


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
    uri              VARCHAR(100) PRIMARY KEY,
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


def init_db(engine=None, schema=DB_SCHEMA):
    """Drop everything, recreate schema + tables."""
    engine = engine or get_engine()
    create_schema(engine, schema)
    create_tables(engine, schema)
    return engine

# ──────────────────────────────────────────────
#  Transform
# ──────────────────────────────────────────────
def transform_articles(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare a raw NYT archive DataFrame for insertion into nyt.articles.

    Input columns expected : uri, snippet, lead_paragraph, pub_date
    Output columns         : uri, date, text
    Sentiment columns (sentiment_label, sentiment_score) are left absent —
    they will be filled later by the FinBERT worker.
    """
    df = df.copy()

    expected_cols = ["uri", "snippet", "lead_paragraph", "pub_date"]
    df = df.loc[:, expected_cols].copy()
    

    # Transform pub_date into useable format
    df["date"] = pd.to_datetime(df["pub_date"]).dt.date
    df.drop(columns=["pub_date"], inplace=True)

    # Concat snippet & lead_paragraph
    df["text"] = df['snippet'] + ' : ' + df['lead_paragraph']
    df.drop('snippet',axis=1,inplace=True)
    df.drop('lead_paragraph',axis=1,inplace=True)

    return df


# ──────────────────────────────────────────────
#  Insert
# ──────────────────────────────────────────────

def insert_articles(engine, df: pd.DataFrame, schema=DB_SCHEMA) -> int:
    """
    Insert a transformed DataFrame into nyt.articles.
    Skips rows whose uri already exists (ON CONFLICT DO NOTHING).

    Args:
        engine : SQLAlchemy engine
        df     : DataFrame with columns [uri, date, text]
        schema : target schema

    Returns:
        Number of rows inserted.
    """
    if df.empty:
        logger.info("insert_articles: empty DataFrame, nothing to insert")
        return 0

    rows = df.to_dict(orient="records")
    stmt = text(f"""
        INSERT INTO {schema}.articles (uri, date, text)
        VALUES (:uri, :date, :text)
        ON CONFLICT (uri) DO NOTHING
    """)

    with engine.begin() as conn:
        result = conn.execute(stmt, rows)

    inserted = result.rowcount
    logger.info("Inserted %d / %d rows into %s.articles", inserted, len(df), schema)
    return inserted


# ──────────────────────────────────────────────
#  Update sentiment
# ──────────────────────────────────────────────

def update_sentiment(engine, uri: str, label: str, score: float, schema=DB_SCHEMA):
    """
    Update sentiment_label and sentiment_score for a single article.

    Called by the FinBERT worker after inference.
    """
    stmt = text(f"""
        UPDATE {schema}.articles
        SET sentiment_label = :label,
            sentiment_score = :score
        WHERE uri = :uri
    """)
    with engine.begin() as conn:
        conn.execute(stmt, {"uri": uri, "label": label, "score": score})


def update_sentiment_batch(engine, records: list[dict], schema=DB_SCHEMA):
    """
    Batch update sentiment for multiple articles.

    Args:
        records : list of dicts with keys [uri, label, score]
    """
    if not records:
        return

    stmt = text(f"""
        UPDATE {schema}.articles
        SET sentiment_label = :label,
            sentiment_score = :score
        WHERE uri = :uri
    """)
    with engine.begin() as conn:
        conn.execute(stmt, records)

    logger.info("Updated sentiment for %d articles in %s.articles", len(records), schema)


# ──────────────────────────────────────────────
#  Fetch (pour le worker FinBERT)
# ──────────────────────────────────────────────

def fetch_unprocessed(engine, schema=DB_SCHEMA) -> pd.DataFrame:
    """
    Return articles not yet processed by FinBERT (sentiment_label IS NULL).
    """
    stmt = text(f"""
        SELECT uri, text
        FROM {schema}.articles
        WHERE sentiment_label IS NULL
        ORDER BY date
    """)
    with engine.connect() as conn:
        df = pd.read_sql(stmt, conn)

    logger.info("Fetched %d unprocessed articles from %s.articles", len(df), schema)
    return df