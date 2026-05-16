"""
tests/_workers/test_fetch_worker.py

Tests unitaires pour _workers/fetch_worker.py.

Stratégie :
    run() contient des imports locaux — on patche au niveau
    du module fetch_worker (ex: "fetch_worker.get_engine").

    Pourquoi "fetch_worker.get_engine" et pas "pipeline.core.src.sql.get_engine" ?
    Parce que run() fait `from pipeline.core.src.sql import get_engine` :
    le nom get_engine est lié dans le namespace de fetch_worker.
    C'est donc là qu'on doit le remplacer — règle d'or du patch :
    "patch where it's used, not where it's defined".

Lancer :
    pytest -m critical tests/_workers/test_fetch_worker.py -v
    pytest tests/_workers/test_fetch_worker.py -v
"""

import pytest
import datetime
import pandas as pd
from unittest.mock import MagicMock, patch
from tests.conftest import make_engine

import fetch_worker

# ──────────────────────────────────────────────
#  Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def mock_raw_df() -> pd.DataFrame:
    """DataFrame brut retourné par fetch_archives() — section Business."""
    return pd.DataFrame({
        "id":                 ["article-001", "article-002"],
        "webPublicationDate": ["2024-01-15T10:00:00Z", "2024-01-16T10:00:00Z"],
        "webTitle":           ["Markets rally", "Oil drops"],
        "fields.trailText":   ["Stocks up", "Energy down"],
        "fields.bodyText":    ["Body 1.", "Body 2."],
        "sectionName":        ["Business", "Business"],
    })


@pytest.fixture
def mock_raw_df_no_business() -> pd.DataFrame:
    """DataFrame brut sans aucun article Business."""
    return pd.DataFrame({
        "id":                 ["article-001"],
        "webPublicationDate": ["2024-01-15T10:00:00Z"],
        "webTitle":           ["Sports news"],
        "fields.trailText":   ["Football match"],
        "fields.bodyText":    ["Body text."],
        "sectionName":        ["Sport"],
    })


@pytest.fixture
def mock_transformed_df() -> pd.DataFrame:
    """DataFrame transformé retourné par transform_articles()."""
    return pd.DataFrame({
        "id":   ["article-001", "article-002"],
        "date": [datetime.date(2024, 1, 15), datetime.date(2024, 1, 16)],
        "text": ["Markets rally. Stocks up. Body 1.",
                 "Oil drops. Energy down. Body 2."],
    })


# ──────────────────────────────────────────────
#  Tests
# ──────────────────────────────────────────────

@pytest.mark.critical
def test_run_case_1(mock_raw_df, mock_transformed_df):
    """
    Cas nominal : last_date connue, 1 mois à fetcher, articles insérés.
    fetch_archives, transform_articles et insert_articles doivent
    être appelés exactement une fois.
    """
    # Test si les opérations fetch, transform et insert ne sont executées qu'une seule fois
    # dans le cas où on n'a qu'un mois à fetcher.
    # Arrange
    engine, _ = make_engine()

    # Act
    # On nomme les patches en fonction des assertions qu'on veut faire à la fin :
    with patch("fetch_worker.get_engine", return_value=engine), \
         patch("fetch_worker.fetch_last_article_date", return_value=datetime.date(2024, 1, 1)), \
         patch("fetch_worker.datetime") as mock_dt, \
         patch("fetch_worker.fetch_archives", return_value=mock_raw_df) as mock_fetch, \
         patch("fetch_worker.transform_articles", return_value=mock_transformed_df) as mock_transform, \
         patch("fetch_worker.insert_articles", return_value=2) as mock_insert, \
         patch("fetch_worker.fetch_job", return_value={}), \
         patch("fetch_worker.update_job"):
        
        mock_dt.date.today.return_value = datetime.date(2024, 1, 31)   # ← fixer today
        mock_dt.date.side_effect = lambda *a, **k: datetime.date(*a, **k)  # ← garder date() constructible
        fetch_worker.run()

    # Assert
    mock_fetch.assert_called_once()
    mock_transform.assert_called_once()
    mock_insert.assert_called_once()


@pytest.mark.critical
def test_run_case_2():
    """
    Si fetch_last_article_date() retourne None (base vide),
    run() doit sortir immédiatement sans appeler fetch_archives.
    """
    # Vérifie que si la base est vide (last_date = None),
    # Ni fetch_archives, ni insert_articles ne sont appelés
    # Arrange
    engine, _ = make_engine()

    # Act
    with patch("fetch_worker.get_engine", return_value=engine), \
         patch("fetch_worker.fetch_last_article_date", return_value=None), \
         patch("fetch_worker.fetch_archives") as mock_fetch, \
         patch("fetch_worker.insert_articles") as mock_insert, \
         patch("fetch_worker.fetch_job", return_value={}), \
         patch("fetch_worker.update_job"):
        fetch_worker.run()

    # Assert
    mock_fetch.assert_not_called()
    mock_insert.assert_not_called()


@pytest.mark.critical
def test_run_case_3(mock_raw_df, mock_transformed_df):
    """
    En mode dry_run=True, insert_articles ne doit jamais être appelé.
    fetch_archives et transform_articles tournent normalement.
    """
    # Vérifie qu'en cas de dry_run, insert_articles n'est pas appelé
    # Arrange
    engine, _ = make_engine()

    # Act
    with patch("fetch_worker.get_engine", return_value=engine), \
         patch("fetch_worker.fetch_last_article_date", return_value=datetime.date(2024, 1, 1)), \
         patch("fetch_worker.fetch_archives", return_value=mock_raw_df), \
         patch("fetch_worker.transform_articles", return_value=mock_transformed_df), \
         patch("fetch_worker.insert_articles") as mock_insert, \
         patch("fetch_worker.fetch_job", return_value={}), \
         patch("fetch_worker.update_job"):
        fetch_worker.run(dry_run=True)

    # Assert
    mock_insert.assert_not_called()


@pytest.mark.critical
def test_run_case_4(mock_raw_df, mock_transformed_df):
    """
    limit_months=1 doit limiter fetch_archives à 1 appel,
    même si plusieurs mois sont disponibles.
    On fixe today=2024-02-01 et last_date=2023-11-01 → 4 mois candidats sans limit.
    """
    # Vérifie que le paramètre limit_months limite bien le nombre d'appels à fetch_archives
    # Arrange
    engine, _ = make_engine()
    fixed_today = datetime.date(2024, 2, 1)

    # Act
    with patch("fetch_worker.get_engine", return_value=engine), \
         patch("fetch_worker.fetch_last_article_date", return_value=datetime.date(2023, 11, 1)), \
         patch("fetch_worker.datetime") as mock_dt, \
         patch("fetch_worker.fetch_archives", return_value=mock_raw_df) as mock_fetch, \
         patch("fetch_worker.transform_articles", return_value=mock_transformed_df), \
         patch("fetch_worker.insert_articles", return_value=2), \
         patch("fetch_worker.fetch_job", return_value={}), \
         patch("fetch_worker.update_job"):
        mock_dt.date.today.return_value = fixed_today
        fetch_worker.run(limit_months=1)

    # Assert — sans limit : 4 appels (nov, déc, jan, fév) ; avec limit=1 : 1 seul
    assert mock_fetch.call_count == 1



@pytest.mark.critical
def test_run_case_5(mock_raw_df_no_business):
    """
    Si fetch_archives retourne uniquement des articles hors-section Business,
    run() doit ignorer ces articles : transform_articles et insert_articles
    ne doivent pas être appelés.
    C'est la logique de filtrage sectionName == 'Business' dans run().
    """
    # Test que si fetch_archives ne retourne que des articles hors Business,
    # ni transform_articles ni insert_articles ne sont appelés
    # Arrange
    engine, _ = make_engine()

    # Act
    with patch("fetch_worker.get_engine", return_value=engine), \
         patch("fetch_worker.fetch_last_article_date", return_value=datetime.date(2024, 1, 1)), \
         patch("fetch_worker.fetch_archives", return_value=mock_raw_df_no_business), \
         patch("fetch_worker.transform_articles") as mock_transform, \
         patch("fetch_worker.insert_articles") as mock_insert, \
         patch("fetch_worker.fetch_job", return_value={}), \
         patch("fetch_worker.update_job"):
        fetch_worker.run()

    # Assert
    mock_transform.assert_not_called()
    mock_insert.assert_not_called()


@pytest.mark.critical
def test_run_case_6(mock_raw_df):
    """
    Si une exception survient, run() doit :
    1. re-lever l'exception — ne pas l'avaler silencieusement
    2. appeler update_job avec status='error' pour tracer l'échec dans theguardian.jobs
    """
    # Vérifie que si une exception survient (ex: timeout API), elle est bien re-levée
    # Arrange
    engine, _ = make_engine()

    # Act + Assert
    with patch("fetch_worker.get_engine", return_value=engine), \
         patch("fetch_worker.fetch_last_article_date", return_value=datetime.date(2024, 1, 1)), \
         patch("fetch_worker.fetch_archives", side_effect=RuntimeError("API timeout")), \
         patch("fetch_worker.fetch_job", return_value={"job_id": "job-001", "status": "started"}), \
         patch("fetch_worker.update_job") as mock_update, \
         patch("fetch_worker.JOB_ID", "job-001"):

        with pytest.raises(RuntimeError, match="API timeout"):
            fetch_worker.run()

    # Assert — update_job appelé avec status='error'
    last_call_status = mock_update.call_args[0][2]
    assert last_call_status == "error"


@pytest.mark.smoke
def test_run_case_7():
    """Sanity check : run() doit créer un engine au démarrage."""
    # Vérifie que get_engine est appelé une fois pour créer une connexion à la base
    # Arrange
    engine, _ = make_engine()

    # Act
    with patch("fetch_worker.get_engine", return_value=engine) as mock_get_engine, \
         patch("fetch_worker.fetch_last_article_date", return_value=None), \
         patch("fetch_worker.fetch_job", return_value={}), \
         patch("fetch_worker.update_job"):
        fetch_worker.run()

    # Assert
    mock_get_engine.assert_called_once()