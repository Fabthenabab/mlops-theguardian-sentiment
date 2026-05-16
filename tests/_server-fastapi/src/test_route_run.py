"""
tests/_server-fastapi/test_route_run.py

Tests unitaires pour _server-fastapi/src/route_run.py.

Stratégie :
    _server-fastapi/src est déclaré dans pythonpath (pyproject.toml) :
        pythonpath = [".", "_workers", "_server-fastapi/src"]
    On importe donc route_run directement, sans préfixe de package.

    On teste _launch() via les endpoints /run/* avec TestClient FastAPI.
    On ne teste pas le lifespan (HuggingFace) — on monte uniquement
    run_router sur une app FastAPI minimale.

    Problème : route_run.py appelle get_engine() au niveau module
    (ligne `engine = get_engine()`), donc à l'import il tente une
    connexion Neon. Solution : patcher pipeline.core.src.sql.get_engine
    avant l'import du module, dans la fixture client.

    Endpoints couverts :
        POST /run/fetch      → _launch("fetch", ...)
        GET  /status/{id}    → fetch_job() → StatusResponse ou 404

Lancer :
    pytest -m critical tests/_server-fastapi/src/test_route_run.py -v
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ──────────────────────────────────────────────
#  App de test minimale
# ──────────────────────────────────────────────
import importlib.util, sys
from pathlib import Path
    
@pytest.fixture(scope="module")
def client():
    """
    TestClient FastAPI avec uniquement run_router monté.
    get_engine est patché avant l'import pour éviter toute connexion DB.
    """
    path = Path("_server-fastapi/src/route_run.py")
    spec = importlib.util.spec_from_file_location("route_run", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["route_run"] = mod
    
    with patch("pipeline.core.src.sql.get_engine", return_value=MagicMock()):
        spec.loader.exec_module(mod)

        app = FastAPI()
        app.include_router(mod.run_router)
        return TestClient(app)


# ──────────────────────────────────────────────
#  _launch() via POST /run/fetch
# ──────────────────────────────────────────────

@pytest.mark.critical
def test_run_fetch_case_1(client):
    """
    POST /run/fetch doit retourner un RunResponse avec
    job_id (uuid), worker='fetch', status='started'.
    Vérifie le contrat de réponse attendu par Airflow.
    """
    # Test run fetch
    with patch("route_run.create_job"), \
         patch("route_run.os.makedirs"), \
         patch("route_run.subprocess.Popen"), \
         patch("builtins.open", MagicMock()):

        response = client.post("/run/fetch")

    assert response.status_code == 200
    body = response.json()
    assert body["worker"] == "fetch"
    assert body["status"] == "started"
    assert "job_id" in body
    assert len(body["job_id"]) == 36  # format UUID


@pytest.mark.critical
def test_run_fetch_case_2(client):
    """
    _launch() doit appeler create_job() exactement une fois
    avant de lancer le subprocess.
    Ordre critique : si le subprocess démarre avant create_job(),
    le worker ne peut pas tracker son job_id.
    """
    # Teste que create_job est appelé une fois pour créer le job dans DB
    # et avant de lancer le subprocess
    with patch("route_run.create_job") as mock_create, \
         patch("route_run.os.makedirs"), \
         patch("route_run.subprocess.Popen"), \
         patch("builtins.open", MagicMock()):

        client.post("/run/fetch")

    mock_create.assert_called_once()


@pytest.mark.critical
def test_run_fetch_case_3(client):
    """
    _launch() doit lancer subprocess.Popen avec fetch_worker.py dans la cmd.
    C'est le mécanisme de découplage entre FastAPI et les workers.
    """
    # Teste que subprocess.Popen est appelé avec fetch_worker.py dans la cmd
    with patch("route_run.create_job"), \
         patch("route_run.os.makedirs"), \
         patch("route_run.subprocess.Popen") as mock_popen, \
         patch("builtins.open", MagicMock()):

        client.post("/run/fetch")

    mock_popen.assert_called_once()
    cmd = mock_popen.call_args[0][0]
    assert any("fetch_worker.py" in arg for arg in cmd)


@pytest.mark.critical
def test_run_fetch_case_4(client):
    """
    Le subprocess doit recevoir JOB_ID dans son environnement.
    Sans ça, le worker ne peut pas mettre à jour theguardian.jobs.
    """
    # Teste que subprocess.Popen est appelé avec un env contenant JOB_ID
    with patch("route_run.create_job"), \
         patch("route_run.os.makedirs"), \
         patch("route_run.subprocess.Popen") as mock_popen, \
         patch("builtins.open", MagicMock()):

        client.post("/run/fetch")

    env = mock_popen.call_args[1]["env"]
    assert "JOB_ID" in env
    assert len(env["JOB_ID"]) == 36  # format UUID


# ──────────────────────────────────────────────
#  GET /status/{job_id}
# ──────────────────────────────────────────────

@pytest.mark.critical
def test_get_status_case_1(client):
    """
    GET /status/{job_id} doit retourner un StatusResponse complet
    quand le job existe dans theguardian.jobs.
    """
    # Teste que GET /status/{job_id} retourne un StatusResponse complet
    mock_job = {
        "job_id":             "test-uuid-1234",
        "worker":             "fetch",
        "status":             "done",
        "started_at":         "2024-01-15 10:00:00",
        "finished_at":        "2024-01-15 10:05:00",
        "error":              None,
        "articles_processed": 42,
    }

    with patch("route_run.fetch_job", return_value=mock_job):
        response = client.get("/status/test-uuid-1234")

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == "test-uuid-1234"
    assert body["status"] == "done"
    assert body["articles_processed"] == 42  # StatusResponse stringify les valeurs


@pytest.mark.critical
def test_get_status_case_2(client):
    """
    GET /status/{job_id} doit retourner 404 si le job n'existe pas.
    fetch_job() retourne {} quand le job_id est inconnu.
    """
    # Teste que GET /status/{job qui n'existe pas c'est à dire {}} retourne 404   
    with patch("route_run.fetch_job", return_value={}):
        response = client.get("/status/job-inexistant")

    assert response.status_code == 404
    assert "job-inexistant" in response.json()["detail"]


@pytest.mark.smoke
def test_get_status_none_fields_stay_none(client):
    """
    Les champs optionnels None (error, finished_at) doivent rester None
    dans la réponse — pas convertis en string "None".
    Dans le endpoint status/, on a cette logique : return StatusResponse(**{k: str(v) if v is not None else None for k, v in job.items()})
        expliqué ainsi :
        if value is None, leave it as None
        Unpack every Key/value of job to populate variables of StatusResponse model
    Documente que le `if v is not None else None` dans StatusResponse est intentionnel.
    """
    # Teste que les champs optionnels None restent None dans la réponse
    mock_job = {
        "job_id":             "test-uuid-5678",
        "worker":             "fetch",
        "status":             "started",
        "started_at":         "2024-01-15 10:00:00",
        "finished_at":        None,
        "error":              None,
        "articles_processed": None,
    }

    with patch("route_run.fetch_job", return_value=mock_job):
        response = client.get("/status/test-uuid-5678")

    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert body["finished_at"] is None