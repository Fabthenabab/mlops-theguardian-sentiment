import requests
import os

URL_API = f"{os.getenv('PROXY_PASS_API')}"

def get_health():
    return requests.get(f"{URL_API}/health").json()


def predict(payload: dict) -> dict:
    resp = requests.post(f"{URL_API}/predict", json=payload)
    resp.raise_for_status()
    return resp.json()











def get_pending_from_cache():
    return requests.get(f"{URL_API}/transactions/pending").json()

def validate(trans_num: str, label: int):
    return requests.patch(f"{URL_API}/transactions/{trans_num}", json={"label": label}).json()



def inject_drift(params: dict):
    return requests.post(f"{URL_API}/admin/inject-drift", json=params).json()

def purge():
    return requests.post(f"{URL_API}/admin/purge").json()