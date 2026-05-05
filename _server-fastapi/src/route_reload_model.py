#route_reload_model.py
import os
from fastapi import APIRouter, Header, HTTPException

import subprocess

reload_model_router = APIRouter()

# Set authentification token
RELOAD_TOKEN = os.getenv("RELOAD_TOKEN")

@reload_model_router.post("/reload_model", include_in_schema=False)
async def reload_model(authorization: str = Header(...)):
    token = authorization.strip().removeprefix("Bearer").strip()    # Authorization: Bearer <token> can be Upper or lower case
    if token != RELOAD_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        result = subprocess.run(["supervisorctl", "restart", "worker-predict"], check=True)
        return {"status": "worker-predict restarting", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=e.stderr)