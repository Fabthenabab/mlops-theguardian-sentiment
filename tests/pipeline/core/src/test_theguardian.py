"""
tests/pipeline/core/test_theguardian.py
 
Tests unitaires pour pipeline/core/src/theguardian.py.
 
Stratégie :
    fetch_archives() fait des appels HTTP à l'API Guardian.
    On mocke requests.get pour simuler les réponses sans réseau.
    On utilise unittest.mock.patch comme context manager dans chaque test
    plutôt qu'un décorateur, pour rester cohérent avec le pattern AAA
    et conserver la lisibilité.
 
Lancer :
    pytest -m critical tests/pipeline/core/src/test_theguardian.py -v
    pytest tests/pipeline/core/src/test_theguardian.py -v
"""
 
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
 
from pipeline.core.src.theguardian import fetch_archives
 
 
# ──────────────────────────────────────────────
#  Helper local — fabrique une réponse mock requests
# ──────────────────────────────────────────────
 
def make_response(results: list, pages: int = 1) -> MagicMock:
    """
    Simule un objet requests.Response contenant une page de résultats Guardian.
 
    L'API Guardian retourne :
        { "response": { "results": [...], "pages": N } }
 
    Args:
        results : liste de dicts simulant des articles
        pages   : nombre total de pages (pour tester la pagination)
    """
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "response": {
            "results": results,
            "pages":   pages,
        }
    }
    return mock_resp
 
 
def make_article(article_id: str) -> dict:
    """Fabrique un article Guardian minimal pour les tests."""
    return {
        "id":                   article_id,
        "webPublicationDate":   "2024-01-15T10:00:00Z",
        "webTitle":             f"Title {article_id}",
        "fields.trailText":     "Trail text.",
        "fields.bodyText":      "Body text.",
    }
 


# ──────────────────────────────────────────────
#  fetch_archives
# ──────────────────────────────────────────────
 
@pytest.mark.critical
def test_fetch_archives_case_1():
    """
    fetch_archives doit retourner un DataFrame pandas.
    Cas nominal : 1 page, 2 articles.
    """
    # Teste si fetch_archives retourne un DataFrame avec les bonnes données
    # Arrange
    articles = [make_article("article-001"), make_article("article-002")]
    mock_resp = make_response(articles, pages=1)
 
    # Act
    # patch remplace requests.get par une fonction qui retourne mock_resp
    # et lance le code de fetch_archives normalement, sans faire de vrai appel HTTP
    # après le with, requests.get redevient normal (mais on n'en a pas besoin ici)
    with patch("pipeline.core.src.theguardian.requests.get", return_value=mock_resp):
        result = fetch_archives(2024, 1)
 
    # Assert
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
 
 
@pytest.mark.critical
def test_fetch_archives_case_2():
    """
    Sur une seule page de résultats, requests.get doit être appelé
    exactement une fois.
    """
    # Teste si fetch_archives appelle requests.get une seule fois pour 1 page
    # Arrange
    mock_resp = make_response([make_article("article-001")], pages=1)
 
    # Act
    # Remplace ponctuellement requests.get dans l'appel de la fonction
    # par une requête factice (sans appel HTTP) qui retourne mock_resp, et vérifie que c'est bien appelé
    with patch("pipeline.core.src.theguardian.requests.get", return_value=mock_resp) as mock_get:
        fetch_archives(2024, 1)
 
    # Assert
    assert mock_get.call_count == 1
 
 
@pytest.mark.critical
def test_fetch_archives_case_3():
    """
    Sur N pages, requests.get doit être appelé N fois
    et le DataFrame final doit contenir tous les articles.
 
    C'est le comportement critique : sans pagination correcte,
    on perd des articles en base.
    """
    # Teste si fetch_archives gère la pagination et agrège les résultats
    # Arrange — 2 pages, 1 article chacune
    page1 = make_response([make_article("article-001")], pages=2)
    page2 = make_response([make_article("article-002")], pages=2)
 
    # Act
    # side_effect=[page1, page2] : chaque appel à mock_get consomme l'élément suivant de la liste.
    with patch("pipeline.core.src.theguardian.requests.get", side_effect=[page1, page2]) as mock_get:
        with patch("pipeline.core.src.theguardian.time.sleep"):  # évite les 0.5s entre pages
            result = fetch_archives(2024, 1)
 
    # Assert
    assert mock_get.call_count == 2
    assert len(result) == 2
 
 
@pytest.mark.critical
def test_fetch_archives_case_4():
    """
    Si l'API Guardian retourne une erreur HTTP (401, 429, 500…),
    fetch_archives doit propager l'exception via raise_for_status().
    On ne doit pas retourner un DataFrame silencieusement.
    """
    # Teste si fetch_archives gère les erreurs HTTP en levant une exception
    # Arrange
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("HTTP 429 Too Many Requests")
 
    # Act + Assert
    with patch("pipeline.core.src.theguardian.requests.get", return_value=mock_resp):
        with pytest.raises(Exception, match="429"):
            fetch_archives(2024, 1)
 
 
@pytest.mark.smoke
def test_fetch_case_5():
    """
    Si l'API retourne 0 articles (mois sans publication),
    le DataFrame doit être vide mais valide.
    """
    # Teste si fetch_archives retourne un DataFrame vide quand il n'y a pas d'articles
    # Arrange
    mock_resp = make_response([], pages=1)
 
    # Act
    with patch("pipeline.core.src.theguardian.requests.get", return_value=mock_resp):
        result = fetch_archives(2024, 1)
 
    # Assert
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0
 
 
@pytest.mark.smoke
def test_fetch_archives_case_6():
    """
    Les paramètres from-date et to-date envoyés à l'API doivent
    correspondre exactement au mois demandé.
    Vérifie que le calcul monthrange est correct (ex: février = 29 jours en 2024).
    """
    # Teste si fetch_archives calcule correctement les paramètres de date pour l'API
    # Arrange
    mock_resp = make_response([], pages=1)
 
    # Act
    with patch("pipeline.core.src.theguardian.requests.get", return_value=mock_resp) as mock_get:
        fetch_archives(2024, 2)  # février 2024 = 29 jours (année bissextile)
 
    # Assert
    call_params = mock_get.call_args[1]["params"]  # keyword arg "params"
    assert call_params["from-date"] == "2024-02-01"
    assert call_params["to-date"]   == "2024-02-29"
 