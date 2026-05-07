#fastapi.py
import os
import io
import sys

from fastapi import FastAPI, Request, HTTPException, Form, Response, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.openapi.docs import get_swagger_ui_html
from pydantic import BaseModel

import joblib
from pathlib import Path

import numpy as np
import pandas as pd


# ************************************************************************************************************
# Logging
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ************************************************************************************************************
# Environment
from dotenv import load_dotenv
load_dotenv()

# Give access to env variables
project_root_path = os.getenv("PROJECT_ROOT")
project_dir_name = os.getenv("PROJECT_NAME")


# ************************************************************************************************************
# Lifespan for model persistance
from contextlib import asynccontextmanager
from transformers import pipeline
from huggingface_hub import login

# ml_models passed to route via app.state
ml_models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    login(token=os.getenv("TOKEN_HF"))
    # Loaded at startup
    app.state.ml_models = {
        "finbert": pipeline("text-classification", model="ProsusAI/finbert")
    }
    yield
    # clean when stopped
    app.state.ml_models.clear()



# ************************************************************************************************************
# Set root_path for nginx
app = FastAPI(
    lifespan=lifespan,  # Lifespan for model persistance
    root_path="/api",
    title="📰 The Guardian - Sentiment Analysis - ⚙️ Management API",
    description="The Guardian - Sentiment Analysis Management Tool",
    version="1.0.0"
    )

@app.get("/")
def read_root():
    return {"message": "FastAPI server -> Up and Running ✅"}

# ************************************************************************************************************
# Include router
from .route_health import health_router
app.include_router(health_router)


# ************************************************************************************************************
# Include router
from .route_predict import predict_router
app.include_router(predict_router)


# ************************************************************************************************************
# Include router
from .route_trend import trend_router
app.include_router(trend_router)


# ************************************************************************************************************
# Include router
from .route_run import run_router
app.include_router(run_router)

# ************************************************************************************************************
# Include router
#from .route_admin import admin_router
#app.include_router(admin_router)

# ************************************************************************************************************
# Include router
#from .route_reload_model import reload_model_router
#app.include_router(reload_model_router)