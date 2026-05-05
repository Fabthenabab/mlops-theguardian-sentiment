import pandas as pd
import time
import requests

# ===============================
# Logging
# ================================
import os
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("pipeline_theguardian")
logger.setLevel(logging.INFO)



def fetch_archives(year: int, month: int) -> pd.DataFrame:
    """
    Fetch The Guardian business articles for a given year/month.

    Args:
        year  : e.g. 2024
        month : 1-12

    Returns:
        pd.DataFrame with all articles for that month (json_normalize applied)
    """
    from calendar import monthrange

    THEGUARDIAN_API_KEY = os.getenv("THEGUARDIAN_API_KEY")
    
    # Bornes du mois
    from_date = f"{year}-{month:02d}-01"
    to_date   = f"{year}-{month:02d}-{monthrange(year, month)[1]:02d}"

    url = "https://content.guardianapis.com/search"
    params = {
        "section":    "business",
        "from-date":  from_date,
        "to-date":    to_date,
        "show-fields": "bodyText,trailText,headline",
        "page-size":  200,
        "api-key":    THEGUARDIAN_API_KEY,
    }

    all_results = []
    page = 1

    while True:
        params["page"] = page
        response = requests.get(url, params=params)
        response.raise_for_status()

        data       = response.json()["response"]
        results    = data["results"]
        all_results.extend(results)

        if page >= data["pages"]:
            break
        page += 1
        time.sleep(0.5)  # 12 req/s max, on reste large

    df = pd.json_normalize(all_results)
    logger.info("Fetched %d articles for %d/%02d", len(df), year, month)
    return df