"""
tests/pipeline/core/test_drift.py
 
Tests unitaires pour pipeline/core/src/drift.py.
 
Stratégie :
    save_reference / load_reference → on mocke les fonctions aws
    (save_parquet_to_s3 / load_parquet_from_s3) pour ne pas toucher S3.
 
    compute_drift → on mocke evidently.report.Report pour ne pas
    charger le modèle Evidently et rester en test unitaire pur.
 
Lancer :
    pytest -m critical tests/pipeline/core/src/test_drift.py -v
        
"""
 
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
 
from pipeline.core.src.drift import save_reference, load_reference, compute_drift

 
# ──────────────────────────────────────────────
#  Fixtures locales
# ──────────────────────────────────────────────
 
@pytest.fixture
def sentiment_df() -> pd.DataFrame:
    """DataFrame minimal avec les colonnes attendues par drift.py."""
    return pd.DataFrame({
        "sentiment_label": ["positive", "negative", "neutral", "positive"],
        "sentiment_score": [0.91, 0.73, 0.55, 0.88],
    })
 
 
@pytest.fixture
def mock_evidently_result_no_drift() -> dict:
    """
    Simule report.as_dict() d'Evidently — cas sans drift.
    On reproduit uniquement la structure utilisée par compute_drift().
    """
    return {
        "metrics": [
            {
                "metric": "DatasetDriftMetric",
                "result": {
                    "dataset_drift":              False,
                    "share_of_drifted_columns":   0.0,
                    "number_of_drifted_columns":  0,
                    "number_of_columns":          2,
                    "drift_share":                0.05,
                }
            }
        ]
    }
 
 
@pytest.fixture
def mock_evidently_result_with_drift() -> dict:
    """
    Simule report.as_dict() d'Evidently — cas avec drift détecté.
    drift_share > DRIFT_THRESHOLD_SCORE (0.10 par défaut).
    """
    return {
        "metrics": [
            {
                "metric": "DatasetDriftMetric",
                "result": {
                    "dataset_drift":              True,
                    "share_of_drifted_columns":   0.5,
                    "number_of_drifted_columns":  1,
                    "number_of_columns":          2,
                    "drift_share":                0.5,
                }
            }
        ]
    }
 
 
# ──────────────────────────────────────────────
#  save_reference
# ──────────────────────────────────────────────
 
@pytest.mark.critical
def test_save_reference(sentiment_df):
    """
    save_reference doit appeler save_parquet_to_s3 exactement une fois
    avec uniquement les colonnes [sentiment_label, sentiment_score].
    On ne teste pas S3 lui-même — uniquement le contrat d'appel.
    """
    # Teste que la fonction save_reference appelle save_parquet_to_s3:
    # au moins une fois
    # avec les bonnes données : un df avec 2 colonnes ["sentiment_label", "sentiment_score"]
    # Arrange + Act
    with patch("pipeline.core.src.drift.save_parquet_to_s3") as mock_save:
        save_reference(sentiment_df)
 
    # Assert
    mock_save.assert_called_once()
    saved_df = mock_save.call_args[0][0]  # premier argument positionnel
    assert list(saved_df.columns) == ["sentiment_label", "sentiment_score"]
    

# ──────────────────────────────────────────────
#  load_reference
# ──────────────────────────────────────────────
 
@pytest.mark.critical
def test_load_reference(sentiment_df):
    """
    load_reference doit retourner le DataFrame tel que chargé depuis S3.
    On mocke load_parquet_from_s3 pour simuler un retour S3.
    """
    # Teste que la fonction load_reference retourne un DataFrame avec les bonnes colonnes
    # et le bon nombre de lignes, tel que simulé par le mock.
    # et que load_parquet_from_s3 est appelé exactement une fois.       
    # Arrange + Act
    with patch("pipeline.core.src.drift.load_parquet_from_s3", return_value=sentiment_df) as mock_load:
        result = load_reference()
 
    # Assert
    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == ["sentiment_label", "sentiment_score"]
    assert len(result) == 4
    mock_load.assert_called_once()


# ──────────────────────────────────────────────
#  compute_drift
# ──────────────────────────────────────────────

@pytest.mark.critical
def test_compute_drift_case_1(sentiment_df, mock_evidently_result_with_drift):
    """
    compute_drift doit retourner un dict correctement mappé
    depuis la structure Evidently.
    """
    # Teste que compute_drift retourne un dict avec les clés "drift", "drift_score", "details"
    mock_report = MagicMock()
    mock_report.as_dict.return_value = mock_evidently_result_with_drift

    with patch("pipeline.core.src.drift.Report", return_value=mock_report):
        result = compute_drift(current=sentiment_df, reference=sentiment_df)

    assert isinstance(result, dict)
    assert set(result.keys()) == {"drift", "drift_score", "details"}
    assert isinstance(result["drift"], bool)
    assert isinstance(result["drift_score"], float)
    assert isinstance(result["details"], dict)


@pytest.mark.critical
def test_compute_drift_case_2(sentiment_df):
    """
    Si DatasetDriftMetric est absent du rapport Evidently,
    compute_drift lève StopIteration via next().
    Ce test documente ce comportement non géré — dette technique connue.
    """
    # Teste si le rapport Evidently ne contient pas de metric "DatasetDriftMetric",
    # Avant de tester le drift en lui-même, entre la réference et le current
    # Arrange — rapport sans DatasetDriftMetric
    mock_report = MagicMock()
    mock_report.as_dict.return_value = {"metrics": [{"metric": "SomeOtherMetric", "result": {}}]}
 
    # Act + Assert
    with patch("pipeline.core.src.drift.Report", return_value=mock_report):
        with pytest.raises(StopIteration):
            compute_drift(current=sentiment_df, reference=sentiment_df)
 

@pytest.mark.smoke
def test_compute_case_3(sentiment_df, mock_evidently_result_no_drift):
    """
    compute_drift doit appeler report.run() avec reference_data et current_data.
    Sans run(), Evidently ne calcule rien.
    """
    # Teste que compute_drift appelle report.run() avec les bons arguments (reference_data et current_data).
    # Arrange
    mock_report = MagicMock()
    mock_report.as_dict.return_value = mock_evidently_result_no_drift
 
    # Act
    with patch("pipeline.core.src.drift.Report", return_value=mock_report):
        compute_drift(current=sentiment_df, reference=sentiment_df)
 
    # Assert
    mock_report.run.assert_called_once_with(
        reference_data=sentiment_df,
        current_data=sentiment_df
    )
 