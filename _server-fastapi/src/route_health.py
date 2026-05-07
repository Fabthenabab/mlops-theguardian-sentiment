# _server-fastapi/src/route_health.py

from fastapi import APIRouter

health_router = APIRouter()

@health_router.get("/health", include_in_schema=True)
async def get_health():
    return {"status": "ok"}