"""
tests/conftest.py
 
Fixtures partagées — disponibles automatiquement dans tous les fichiers test_*.py
sans aucun import. pytest les injecte via le nom du paramètre de la fonction.
 
Markers enregistrés dans pyproject.toml :
    critical    → gate CI Jenkins bloquant      (pytest -m critical)
    smoke       → sanity check démarrage rapide (pytest -m smoke)
    slow        → workers ML lourds, exclus CI  (pytest -m "not slow")
    integration → nécessite DB ou réseau réel
"""
 
import pytest
import pandas as pd
from datetime import date
from unittest.mock import MagicMock
 
 
# ──────────────────────────────────────────────
#  Mock engine SQLAlchemy
# ──────────────────────────────────────────────
 
def make_engine(rowcount=0, fetchone_result=None, scalar_result=None):
    """
    Helper (pas une fixture) — retourne (engine, conn) mockés.
 
    Pourquoi ce mock est nécessaire :
        sql.py fait `with engine.begin() as conn: conn.execute(stmt, rows)`
        Sans mock → Python tente une vraie connexion à Neon PostgreSQL.
        Avec mock → objet factice, zéro réseau, on vérifie les appels.
 
    Paramètres :
        rowcount        → lignes affectées simulées (INSERT / DELETE)
        fetchone_result → Row simulée pour SELECT ... LIMIT 1
        scalar_result   → scalaire simulé pour conn.execute().scalar()
    """
    engine = MagicMock()
    conn = MagicMock()
    # code testé          →   mock (mapping)          →   valeur simulée
    # engine.begin() as conn:  →  engine.begin.return_value.__enter__.return_value  → conn
    # engine.connect() as conn:  →  engine.connect.return_value.__enter__.return_value  → conn
    engine.begin.return_value.__enter__.return_value = conn
    engine.connect.return_value.__enter__.return_value = conn
    conn.execute.return_value.rowcount = rowcount
    conn.execute.return_value.fetchone.return_value = fetchone_result
    conn.execute.return_value.scalar.return_value = scalar_result
    return engine, conn
 
 
# ──────────────────────────────────────────────
#  Fixtures — Articles
# ──────────────────────────────────────────────
 
@pytest.fixture
def mock_theguardian_archive() -> pd.DataFrame:
    """
    DataFrame brut tel que retourné par l'API Guardian.
    Format attendu en entrée de transform_articles().
    Contient une colonne parasite pour tester que transform_articles ne garde que les colonnes attendues
    """
    return pd.DataFrame({
        "id": ["article-1", "article-2"],
        "webPublicationDate": ["2024-01-15T10:30:00Z", "2024-02-20T08:15:00Z"],
        "webTitle": ["Markets rally", "Oil prices fall"],
        "fields.trailText": ["Stocks surged worldwide", "Energy sector reacts"],
        "fields.bodyText": ["Investors welcomed the news.", "Analysts expect more volatility."],
        "parasite": ["News", "Business"],  # colonne parasite
    })


@pytest.fixture
def mock_transformed_articles() -> pd.DataFrame:
    """
    DataFrame déjà transformé, prêt pour insert_articles().
    Colonnes : id, date, text — pas de sentiment (FinBERT n'a pas tourné).
    """
    return pd.DataFrame({
        "id":   ["article-1", "article-2"],
        "date": [date(2024, 1, 15), date(2024, 2, 20)],
        "text": [
            "Markets rally. Stocks surged worldwide. Investors welcomed the news.",
            "Oil prices fall. Energy sector reacts. Analysts expect more volatility.",
        ],
    })


@pytest.fixture
def mock_sentiment_records() -> list:
    """Records pour update_sentiment_batch() — format attendu par sql.py."""
    return [
        {"id": "article-1", "label": "positive", "score": 0.91},
        {"id": "article-2", "label": "negative", "score": 0.73},
    ]


# ──────────────────────────────────────────────
#  Fixtures — Jobs
# ──────────────────────────────────────────────
 
@pytest.fixture
def mock_job_row() -> MagicMock:
    """
    Simule une Row SQLAlchemy pour fetch_job().
    sql.py fait dict(row._mapping) — on reproduit ce comportement.
    """
    row = MagicMock()
    row._mapping = {
        "job_id":             "job-uuid-001",
        "worker":             "fetch_worker",
        "status":             "success",
        "started_at":         "2024-01-15 10:00:00",
        "finished_at":        "2024-01-15 10:05:00",
        "error":              None,
        "articles_processed": 42,
    }
    return row

# ──────────────────────────────────────────────
#  Fixtures — Forecasts
# ──────────────────────────────────────────────
 
@pytest.fixture
def mock_forecast_df() -> pd.DataFrame:
    """
    DataFrame Prophet minimal pour write_forecasts().
    Simule une prévision Prophet
    """
    return pd.DataFrame({
        "ds":         pd.to_datetime(["2024-02-01", "2024-02-02", "2024-02-03"]),
        "yhat":       [0.12, 0.15, 0.10],
        "yhat_lower": [0.08, 0.11, 0.06],
        "yhat_upper": [0.16, 0.19, 0.14],
    })
