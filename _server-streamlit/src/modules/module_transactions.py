# modules/module_transactions.py
import streamlit as st
import pandas as pd

# Cache
from utils.api import get_pending_from_cache, validate

# Tabs

def body():
    # ************************************************************************************************************
    # ========================================
    # CACHE SETUP
    # ========================================
    # Empty session_state cache of previous page
    # CACHE
    
    
    
    st.title("💸 Pred")
    st.markdown("Display and validate transactions")

    # ========================================
    # TABS
    # ========================================
    st.title("🔍 Search for one book")
    st.markdown("Search on different criteria")
    
    # ========================================
    # TABS
    # ========================================
   # Tabs for different sections
    tab0, tab1, tab2 = st.tabs([
        "⭐ Top-Rated books",
        "❤️‍🔥 Popular books",
        "🔍 Multi criteria search"
    ])
    
    with tab0:
        st.markdown("Test FinBERT sentiment analysis on a news article")

        # Zone de saisie
        article_id = st.text_input("Article ID", value="test-001")
        article_text = st.text_area("Article text", height=200,
            placeholder="Paste a Guardian business article here...")

        if st.button("🔮 Predict sentiment", key="predict_button"):
            if not article_text.strip():
                st.warning("Please enter some text.")
            else:
                with st.spinner("Predicting..."):
                    payload = {
                        "articles": [
                            {"id": article_id, "text": article_text}
                        ]
                    }
                    result = predict(payload)

                if result and "results" in result:
                    r = result["results"][0]
                    label = r["sentiment_label"]
                    score = r["sentiment_score"]

                    color = {"positive": "🟢", "negative": "🔴", "neutral": "🟡"}.get(label, "⚪")
                    st.markdown(f"### {color} {label.upper()}")
                    st.metric("Confidence", f"{score:.1%}")
                else:
                    st.error("Prediction failed")
    with tab1:
        st.markdown("Test FinBERT sentiment analysis sur les articles du jour")
