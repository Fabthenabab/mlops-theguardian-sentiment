# tabs/block_trend_history.py
import streamlit as st
import pandas as pd
from datetime import date
from utils.api import get_trend_by_date
from utils.libs import plot_forecast


@st.fragment
def render():
    selected_date = st.date_input("Select a run date", value=date.today())

    if st.button("🔍 Search", key="search_trend"):
        result = get_trend_by_date(selected_date)

        if not result or not result.get("forecasts"):
            st.warning(f"No forecast found for or before {selected_date}.")
            return

        df = pd.DataFrame(result["forecasts"])
        st.caption(f"Run date : {result['run_date']} — run_id : {result['run_id']}")
        st.plotly_chart(
            plot_forecast(df, f"Prophet forecast — run {result['run_date']}"),
            width="stretch"
        )