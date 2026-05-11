# _server-fastapi/src/route_run.py
import os

# ===============================
# Logging
# ================================
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ===============================
# ENV
# ================================
WORKERS_PATH = os.getenv("WORKERS_PATH", "/home/user/app/_workers")


# ===============================
# Router
# ===============================
from fastapi import APIRouter
run_router = APIRouter()


# ===============================
# Pydantic
# ===============================
from pydantic import BaseModel
from typing import Optional

# Output
class RunResponse(BaseModel):
    job_id: str
    worker: str
    status: str


class StatusResponse(BaseModel):
    job_id: str
    worker: str
    status: str
    started_at:         str | None
    finished_at:        str | None
    error:              str | None
    articles_processed: int | None


# ===============================
# Run entry point
# ===============================
import uuid
import subprocess
import datetime
from typing import Literal

from fastapi import HTTPException, Query
from pipeline.core.src.sql import get_engine, create_job, fetch_job, update_job

engine = get_engine()


# ──────────────────────────────────────────────
#  Internal functions
# ──────────────────────────────────────────────

def _launch(worker: str, cmd: list) -> RunResponse:
    '''
    Factorize commune operations for different entry point
    Launch *_worker.py in a subprocess,
    As a new job, with job_id=uuid,
    and return this job in db with status="started"
    
    '''
    logger.info("function _launch")
    # Define unique id process for worker process
    job_id = str(uuid.uuid4())

    # Define info to be stored in .jobs table in DB to allow worker process tracking
    create_job(engine, job_id=job_id, worker=worker)

    # Define log file
    # Logfiles: one by worker + append in each logfile (no different logfile by worker run)
    logs_dir = os.getenv("WORKERS_LOGS_PATH", "/home/user/logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Launch worker in background non blocking process
    # Define cmd, env (define heritance from parent process + add new env)
    subprocess.Popen(
        cmd,
        env={**os.environ, "JOB_ID": job_id},
        stdout=open(f"{logs_dir}/{worker}.log", "a"),
        stderr=open(f"{logs_dir}/{worker}_err.log", "a"),
    )

    logger.info(f"Worker {worker} started — job_id: {job_id}")
    return RunResponse(job_id=job_id, worker=worker, status="started")


# ──────────────────────────────────────────────
#  /run/transformers
# ──────────────────────────────────────────────

@run_router.post("/run/transformers", response_model=RunResponse)
async def ep_run_transformers(
    limit: int = Query(default=None, description="Process N articles only (for testing)")
):
    logger.debug("function ep_run_transformers")
    cmd = [
        "python",
        os.path.join(WORKERS_PATH, "transformers_worker.py")
    ]
    if limit:
        cmd += ["--limit", str(limit)]
    
    return _launch("transformers", cmd)

# ──────────────────────────────────────────────
#  /run/prophet
# ──────────────────────────────────────────────

@run_router.post("/run/prophet", response_model=RunResponse)
async def ep_run_prophet(
    retrain: Literal["scheduled", "evidently_drift"] = Query(default="scheduled")
):
    logger.debug("function ep_run_prophet")
    cmd = [
        "python",
        os.path.join(WORKERS_PATH, "prophet_worker.py"),
        "--retrain", retrain
    ]
    return _launch("prophet", cmd)


# ──────────────────────────────────────────────
#  /run/monitor
# ──────────────────────────────────────────────

@run_router.post("/run/monitor", response_model=RunResponse)
async def ep_run_monitor(
    mode: Literal["snapshot", "compare"] = Query(default="snapshot")
):
    logger.debug(f"function ep_run_monitor - mode: {mode}")
    cmd = [
        "python",
        os.path.join(WORKERS_PATH, "monitor_worker.py"),
        "--mode", mode
    ]
    return _launch("monitor", cmd)


# ──────────────────────────────────────────────
#  /run/fetch
# ──────────────────────────────────────────────
@run_router.post("/run/fetch", response_model=RunResponse)
async def ep_run_fetch():
    logger.debug("function ep_run_fetch")
    cmd = ["python", os.path.join(WORKERS_PATH, "fetch_worker.py")]
    return _launch("fetch", cmd)


# ──────────────────────────────────────────────
#  /status/{job_id}
# ──────────────────────────────────────────────

@run_router.get("/status/{job_id}", response_model=StatusResponse)
async def ep_get_status(job_id: str):
    job = fetch_job(engine, job_id=job_id)
    # fetch_job returns job dict wtih keys = cols: job_id, worker, status, started_at, finished_at, error, articles_processed
    # StatusResponse is built directly from these columns (as keys) and their values
    # if value is None, leave it as None
    # Unpack every Key/value of job to populate variables of StatusResponse model
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return StatusResponse(**{k: str(v) if v is not None else None for k, v in job.items()})
