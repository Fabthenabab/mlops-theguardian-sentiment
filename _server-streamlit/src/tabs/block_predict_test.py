# tabs/block_predict_test.py
import streamlit as st
#import pandas as pd

from utils.api import predict

@st.fragment
def render():
    st.markdown("### Test FinBERT sentiment analysis on a news article")

    # Input
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
    