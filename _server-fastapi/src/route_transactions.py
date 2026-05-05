from fastapi import APIRouter

from pipeline.core.src.sql import get_engine, get_pending, validate_transaction

transactions_router = APIRouter()

@transactions_router.get("/transactions/pending", include_in_schema=True)
async def ep_get_pending():
    engine = get_engine()
    d_pending = get_pending(engine=engine)
    return d_pending

from fastapi import Body
@transactions_router.patch("/transactions/{trans_num}", include_in_schema=True)
async def ep_validate(trans_num: str, label: int = Body(..., embed=True)):
    engine = get_engine()
    validate_transaction(engine, trans_num, int(label))
    return {"status": "validated", "trans_num": trans_num, "label": label}

