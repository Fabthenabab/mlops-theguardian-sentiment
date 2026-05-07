import requests
import os

URL_API = f"{os.getenv('PROXY_PASS_API')}"

def get_health():
    return requests.get(f"{URL_API}/health").json()


def predict(payload: dict) -> dict:
    resp = requests.post(f"{URL_API}/predict", json=payload)
    resp.raise_for_status()
    return resp.json()


def get_trend() -> dict:
    resp = requests.get(f"{URL_API}/trend")
    resp.raise_for_status()
    return resp.json()


def get_trend_by_date(run_date) -> dict:
    resp = requests.get(f"{URL_API}/trend/{run_date}")
    if resp.status_code == 404:
        return {}
    resp.raise_for_status()
    return resp.json()
