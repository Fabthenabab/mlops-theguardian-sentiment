# modules/module_trend.py
import streamlit as st

# Tabs
from tabs.block_trend_latest import render as render_latest
from tabs.block_trend_history import render as render_history



def body():
    st.title("📈 Economic Sentiment Trend")

    # Tabs for different sections
    tab_latest, tab_history = st.tabs([
        "📈 Latest forecast",
        "📆 Historical search",
    ])
    # Last forecast
    with tab_latest:
        render_latest()
    # Search forecast by date
    with tab_history:
        render_history()