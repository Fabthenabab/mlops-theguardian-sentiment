import os
from sqlalchemy import create_engine, text

url = os.environ["BACKEND_STORE_URI"]
engine = create_engine(url)

with engine.begin() as conn:
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS mlflow"))
    print("Schema mlflow ready")