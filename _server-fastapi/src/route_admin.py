import os
from fastapi import APIRouter

from fastapi import Body
from pipeline.core.src.sql import get_engine, inject_drift, drift_report, rollback_drift

from pipeline.core.src.drift_generator import generate_drift_batch


admin_router = APIRouter()


# ===============================
# Pydantic
# ================================

from pydantic import BaseModel, ConfigDict, Field


class InjectDriftParams(BaseModel):
    n: int = Field(100, description="Number of rows to generate")
    amt_multiplier: float = Field(5.0, description="Shift amount multiplier")
    fraud_ratio: float = Field(0.3, description="Proportion of label=1")
    force_category: str = Field("shopping_net", description="Concentrate on one category")
    force_state: str = Field("AK", description="Concentrate on one state")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "n": 50,
                    "amt_multiplier": 8.0,
                    "fraud_ratio": 0.5,
                    "force_category": "shopping_net",
                    "force_state": "AK",
                }
            ]
        }
    )


# ===============================
# Entry points
# ================================
_INJECT_DRIFT_DESC = """
Generate and inject synthetic drifted transactions into validated.
```bash
curl -X POST http://localhost:9000/admin/inject-drift \\
  -H "Content-Type: application/json" \\
  -d '{{"n": 5, "amt_multiplier": 8.0, "fraud_ratio": 0.5}}'
```
"""


@admin_router.post(
    "/admin/inject-drift",
    summary="Inject synthetic drifted transactions",
    description=_INJECT_DRIFT_DESC,
)
async def ep_inject_drift(params: InjectDriftParams):
    """
    Generate and inject synthetic drifted transactions into validated.
    
    Params:
        n: number of rows (default 100)
        amt_multiplier: shift amount (default 5.0)
        fraud_ratio: proportion of label=1 (default 0.3)
        force_category: concentrate on one category (default shopping_net)
        force_state: concentrate on one state (default AK)
    """
    engine = get_engine()
    rows = generate_drift_batch(
        engine=engine,
        n=params.n,
        amt_multiplier=params.amt_multiplier,
        fraud_ratio=params.fraud_ratio,
        force_category=params.force_category,
        force_state=params.force_state,
    )
    if not rows:
        return {"status": "error", "detail": "No validated data to base drift on"}

    inject_drift(engine, rows)

    return {
        "status": "injected",
        "n_rows": len(rows),
        "params": {
            "amt_multiplier": params.amt_multiplier,
            "fraud_ratio": params.fraud_ratio,
            "force_category": params.force_category,
            "force_state": params.force_state,
        },
    }



@admin_router.post("/admin/purge", include_in_schema=False)
async def purge():
    return {"status": "purged"}