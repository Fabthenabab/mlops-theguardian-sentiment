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


def inject_drift(n: int = 100) -> dict:
    resp = requests.post(f"{URL_API}/admin/inject-drift", json={"n": n})
    resp.raise_for_status()
    return resp.json()


def rollback_drift() -> int:
    resp = requests.post(f"{URL_API}/admin/rollback-drift")
    resp.raise_for_status()
    return resp.json()


def run_monitor(mode: str = "compare") -> str:
    # Pass argument mode to post request param
    resp = requests.post(f"{URL_API}/run/monitor", params={"mode": mode})
    resp.raise_for_status()
    return resp.json()

def get_drift_report(job_id: str) -> dict:
    resp = requests.get(f"{URL_API}/admin/drift-report/{job_id}")
    if resp.status_code == 404:
        return {}
    else:
        resp.raise_for_status()
        return resp.json()   

def get_status(job_id: str) -> dict:
    resp = requests.get(f"{URL_API}/status/{job_id}")
    if resp.status_code == 404:
        return {}
    else:
        resp.raise_for_status()
        return resp.json()   