
"""
tests/pipeline/core/test_sql.py
 
1 fonction de test par fonction testée dans sql.py.
Structure AAA : Arrange / Act / Assert.
 
Les fixtures (mock_theguardian_archive, mock_transformed_articles…)
sont définies dans tests/conftest.py et injectées automatiquement
par pytest via le nom du paramètre — aucun import nécessaire.
 
Lancer les tests critiques seulement :
    pytest -m critical tests/pipeline/core/src/test_sql.py -v
 
Lancer tous les tests :
    pytest tests/pipeline/core/src/test_sql.py -v
"""
 
import pytest
import pandas as pd
from datetime import date
from unittest.mock import MagicMock, patch
 
from pipeline.core.src.sql import (
    transform_articles,
    insert_articles,
    update_sentiment_batch,
    fetch_unprocessed,
    inject_drift,
    rollback_drift,
    create_job,
    fetch_job,
    write_forecasts,
)
 
# Helper défini dans conftest.py — importé explicitement car c'est
# un helper (fonction normale), pas une fixture pytest
from tests.conftest import make_engine
 
 
# ──────────────────────────────────────────────
#  transform_articles
# ──────────────────────────────────────────────
 
@pytest.mark.critical
def test_transform_articles(mock_theguardian_archive):
    # Arrange
    expected_df = pd.DataFrame({
        "id": ["article-1", "article-2"],
        "date": [
            pd.to_datetime("2024-01-15").date(),
            pd.to_datetime("2024-02-20").date(),
        ],
        "text": [
            "Markets rally. Stocks surged worldwide. Investors welcomed the news.",
            "Oil prices fall. Energy sector reacts. Analysts expect more volatility.",
        ],
    })
    # Act
    result_df = transform_articles(mock_theguardian_archive)
    # Assert
    # assert_frame_equal est préféré à df.equals() :
    # il indique exactement quelle colonne ou valeur diffère si le test échoue
    pd.testing.assert_frame_equal(result_df.reset_index(drop=True), expected_df)
    

# ──────────────────────────────────────────────
#  insert_articles
# ──────────────────────────────────────────────

@pytest.mark.critical
def test_insert_articles_case_1(mock_transformed_articles):
    # Test insert success
    # Arrange
    engine, conn = make_engine(rowcount=2)
    # Act
    result = insert_articles(engine, mock_transformed_articles)
    # Assert
    assert result == 2
 
 
@pytest.mark.critical
def test_insert_articles_case_2():
    # Test insert with empty DataFrame: limit case -> early returns
    # Arrange
    engine, conn = make_engine()
    # Act
    result = insert_articles(engine, pd.DataFrame())
    # Assert
    assert result == 0
    # Vérifie que la connexion n'a pas été utilisée pour appeler la DB
    conn.execute.assert_not_called()


# ──────────────────────────────────────────────
#  update_sentiment_batch
# ──────────────────────────────────────────────
 
@pytest.mark.critical
def test_update_sentiment_batch_case_1(mock_sentiment_records):
    # Vérifie que la connexion a été utilisée pour appeler la DB
    # Arrange
    engine, conn = make_engine()
    # Act
    update_sentiment_batch(engine, mock_sentiment_records)
    # Assert
    conn.execute.assert_called_once()
 
 
@pytest.mark.smoke
def test_update_sentiment_batch_case_2():
    # Vérifie que la connexion n'a pas été utilisée pour appeler la DB
    # Arrange
    engine, conn = make_engine()
    # Act
    update_sentiment_batch(engine, [])
    # Assert
    conn.execute.assert_not_called()


# ──────────────────────────────────────────────
#  fetch_unprocessed
# ──────────────────────────────────────────────
 
@pytest.mark.critical
def test_fetch_unprocessed():
    # Arrange
    engine, conn = make_engine()
    expected = pd.DataFrame({"id": ["article-1"], "text": ["Some text."]})
    # Act
    with patch("pipeline.core.src.sql.pd.read_sql", return_value=expected):
        result = fetch_unprocessed(engine)
    # Assert
    pd.testing.assert_frame_equal(result, expected)


# ──────────────────────────────────────────────
#  inject_drift
# ──────────────────────────────────────────────
 
@pytest.mark.critical
def test_inject_drift_case_1():
    # Teste si le drift a bien été injecté
    # Arrange
    engine, conn = make_engine(scalar_result=date(2024, 1, 15))
    # Act
    result = inject_drift(engine, n=10)
    # Assert
    assert result == 10
 
 
@pytest.mark.critical
def test_inject_drift_case_2():
    # Teste si les inserts de drift ont le format attendu 'drift_"...
    # Arrange
    engine, conn = make_engine(scalar_result=date(2024, 1, 15))
    # Act
    inject_drift(engine, n=3)
    # Assert — 1er execute() = SELECT MAX(date), 2e = INSERT
    insert_call = conn.execute.call_args_list[1]
    rows = insert_call[0][1]
    assert all(r["id"].startswith("drift_") for r in rows)


# ──────────────────────────────────────────────
#  rollback_drift
# ──────────────────────────────────────────────
 
@pytest.mark.critical
def test_rollback_drift_case_1():
    # Teste si le rollback compte bien les lignes affectées
    # Arrange
    engine, conn = make_engine(rowcount=10)
    # Act
    result = rollback_drift(engine)
    # Assert
    assert result == 10
 
 
@pytest.mark.critical
def test_rollback_drift_case_2():
    # Teste si la fonction cible le prefix 'drift_%'
    # Arrange
    engine, conn = make_engine(rowcount=10)
    # Act
    rollback_drift(engine)
    # Assert — le SQL émis doit cibler 'drift_%'
    sql_emitted = str(conn.execute.call_args[0][0])
    assert "drift_" in sql_emitted


# ──────────────────────────────────────────────
#  create_job
# ──────────────────────────────────────────────
 
@pytest.mark.smoke
def test_create_job():
    # Teste si la création de job est appelée au moins une fois pour insertion
    # et utilise les paramètres corrects
    # Arrange
    engine, conn = make_engine()
    # Act
    create_job(engine, "job-uuid-001", "fetch_worker")
    # Assert
    conn.execute.assert_called_once()
    params = conn.execute.call_args[0][1]
    assert params["job_id"] == "job-uuid-001"
    assert params["worker"] == "fetch_worker"


# ──────────────────────────────────────────────
#  fetch_job
# ──────────────────────────────────────────────
 
@pytest.mark.critical
def test_fetch_job_case_1(mock_job_row):
    # Teste si la récupération de job retourne un dict avec les bonnes clés
    # Arrange
    engine, conn = make_engine(fetchone_result=mock_job_row)
    # Act
    result = fetch_job(engine, "job-uuid-001")
    # Assert
    assert isinstance(result, dict)
    assert result["status"] == "success"
    assert result["articles_processed"] == 42
 
 
@pytest.mark.critical
def test_fetch_job_case_2():
    # Teste si la récupération de job retourne un dict vide quand le job n'est pas trouvé
    # Arrange
    engine, conn = make_engine(fetchone_result=None)
    # Act
    result = fetch_job(engine, "job-uuid-inexistant")
    # Assert
    assert result == {}


# ──────────────────────────────────────────────
#  write_forecasts
# ──────────────────────────────────────────────
 
@pytest.mark.critical
def test_write_forecasts_case_1(mock_forecast_df):
    # Teste si la fonction write_forecasts retourne le nombre de lignes insérées
    # Arrange
    engine, conn = make_engine()
    # Act
    result = write_forecasts(engine, mock_forecast_df, run_id="mlflow-abc", run_date=date(2024, 2, 1))
    # Assert
    assert result == 3  # mock_forecast_df a 3 lignes
 
 
@pytest.mark.smoke
def test_write_forecasts_case_2():
    # Teste si la fonction write_forecasts ne fait pas d'insertion ni n'ouvre de connexion quand le DataFrame est vide
    # Arrange
    engine, conn = make_engine()
    # Act
    result = write_forecasts(engine, pd.DataFrame(), run_id="mlflow-abc", run_date=date(2024, 2, 1))
    # Assert
    assert result == 0
    conn.execute.assert_not_called()