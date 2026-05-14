# _server-fastapi/src/route_admin.py

import os

# ===============================
# Logging
# ================================
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ===============================
# Router
# ===============================
from fastapi import APIRouter
admin_router = APIRouter()



# ===============================
# Pydantic
# ===============================
from fastapi import Request, HTTPException
from pydantic import BaseModel

# Input
class InjectDriftRequest(BaseModel):
    n: int = 100

# Output
class InjectDriftResponse(BaseModel):
    inserted: int
    message:  str


class RollbackResponse(BaseModel):
    deleted: int
    message: str


class DriftReportResponse(BaseModel):
    job_id:      str | None
    run_date:    str | None
    mode:        str | None
    drift:       bool | None
    drift_score: float | None



# ===============================
# Admin entry point
# ===============================
from pipeline.core.src.sql import get_engine, inject_drift, rollback_drift, fetch_monitor_by_job_id

engine = get_engine()

# ──────────────────────────────────────────────
#  POST /admin/inject-drift
# ──────────────────────────────────────────────

@admin_router.post("/admin/inject-drift", response_model=InjectDriftResponse)
async def ep_inject_drift(body: InjectDriftRequest = InjectDriftRequest()):
    logger.info(f"function ep_inject_drift — n: {body.n}")
    inserted = inject_drift(engine, n=body.n)
    return InjectDriftResponse(
        inserted=inserted,
        message=f"{inserted} drift articles injected"
    )


# ──────────────────────────────────────────────
#  POST /admin/rollback-drift
# ──────────────────────────────────────────────

@admin_router.post("/admin/rollback-drift", response_model=RollbackResponse)
async def ep_rollback_drift():
    logger.info("function ep_rollback_drift")
    deleted = rollback_drift(engine)
    return RollbackResponse(
        deleted=deleted,
        message=f"{deleted} drift articles removed"
    )


# ──────────────────────────────────────────────
#  GET /admin/drift-report
# ──────────────────────────────────────────────

@admin_router.get("/admin/drift-report/{job_id}", response_model=DriftReportResponse)
async def ep_drift_report(job_id: str):
    logger.info("function ep_drift_report")
    logger.info(f"Evidently report for job_id: {job_id}")
    report = fetch_monitor_by_job_id(engine, job_id=job_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"No drift report found for job_id: {job_id}")
    return DriftReportResponse(
        job_id      = report.get("job_id"),
        run_date    = str(report.get("run_date")),
        mode        = report.get("mode"),
        drift       = report.get("drift"),
        drift_score = report.get("drift_score")
    )