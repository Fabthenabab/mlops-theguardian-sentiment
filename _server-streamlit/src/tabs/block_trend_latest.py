# tabs/block_trend_latest.py
import streamlit as st
import pandas as pd
from utils.api import get_trend
from utils.libs import plot_forecast


def render():
    result = get_trend()

    if not result or not result.get("forecasts"):
        st.warning("No forecast available yet.")
        return

    df = pd.DataFrame(result["forecasts"])
    st.caption(f"Run date : {result['run_date']} — run_id : {result['run_id']}")
    st.plotly_chart(plot_forecast(df, "Latest Prophet forecast"), width="stretch")
