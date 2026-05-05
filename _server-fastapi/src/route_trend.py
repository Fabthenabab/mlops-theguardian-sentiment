from fastapi import APIRouter, HTTPException
from datetime import date
import pandas as pd
from pipeline.core.src.sql import get_engine, fetch_forecasts

# ===============================
# Logging
# ================================
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ===============================
# Router
# ===============================
trend_router = APIRouter()
engine = get_engine()

# ===============================
# Pydantic
# ===============================
from pydantic import BaseModel

class ForecastPoint(BaseModel):
    ds: date
    yhat: float
    yhat_lower: float
    yhat_upper: float

class TrendResponse(BaseModel):
    run_id: str
    run_date: date
    forecasts: list[ForecastPoint]


def _get_trend(run_date=None) -> TrendResponse:
    df = fetch_forecasts(engine, run_date=run_date)
    if df.empty:
        raise HTTPException(status_code=404, detail="No forecasts found")

    return TrendResponse(
        run_id=df["run_id"].iloc[0],
        run_date=df["run_date"].iloc[0],
        forecasts=df[["ds", "yhat", "yhat_lower", "yhat_upper"]].to_dict(orient="records")
    )


# ===============================
# Trend entry point
# ===============================
@trend_router.get("/trend", response_model=TrendResponse, include_in_schema=True)
async def ep_get_trend_latest():
    return _get_trend()


@trend_router.get("/trend/{run_date}", response_model=TrendResponse, include_in_schema=True)
async def ep_get_trend_by_date(run_date: date):
    return _get_trend(run_date=run_date)
  