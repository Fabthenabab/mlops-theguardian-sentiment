# modules/module_predict.py
import streamlit as st

# Tabs
from tabs.block_predict_test import render as render_test
from tabs.block_predict_fetch_theguardian import render as render_fetch_theguardian


def body():
    st.title("🔮 Sentiment Prediction")
    
    # Tabs for different sections
    tab_test, tab_fetch_the_guardian = st.tabs([
        "🧪 Test one article",
        "🗞️ The Guardian API",
    ])
    with tab_test:
        render_test()
    with tab_fetch_the_guardian:
        render_fetch_theguardian()