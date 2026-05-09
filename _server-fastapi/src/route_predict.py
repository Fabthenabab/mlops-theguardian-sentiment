# _server-fastapi/src/route_predict.py
import os

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
from fastapi import APIRouter
predict_router = APIRouter()


# ===============================
# Pydantic
# ===============================
# Passing var from fastapi.py main app to route.py
# via app.state
# ex: request.app.state.ml_models
from fastapi import Request
from pydantic import BaseModel

# Input
class Article(BaseModel):
    id: str
    text: str

class Articles(BaseModel):
    articles: list[Article]

# Output
class ArticlePredicted(BaseModel):
    id: str
    text: str
    sentiment_label: str
    sentiment_score: float

class ArticlesPredicted(BaseModel):
    results: list[ArticlePredicted]


# ===============================
# Predict entry point
# ===============================
@predict_router.post("/predict", response_model=ArticlesPredicted, include_in_schema=True)
async def ep_predict(request: Request, body: Articles) -> dict:
    logger.debug(f"function ep_predict")
    pipe = request.app.state.ml_models["finbert"]
    results = []
    
    for article in body.articles:
        result = pipe(article.text, truncation=True, max_length=512)[0]
        results.append(ArticlePredicted(
            id=article.id,
            text=article.text,
            sentiment_label=result["label"],
            sentiment_score=result["score"]
        ))
    
    return ArticlesPredicted(results=results)