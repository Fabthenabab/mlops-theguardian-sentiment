# modules/module_predict.py
import streamlit as st
import pandas as pd

# Cache
from utils.api import predict

# Tabs

def body():
    st.title("🔮 Sentiment Prediction")
    
    # Tabs for different sections
    tab0, tab1 = st.tabs([
        "🧪 Test one article",
        "🗞️ The Guardian API",
    ])
    with tab0:
        st.markdown("### Test FinBERT sentiment analysis on a news article")

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
        st.markdown("### Live Guardian fetch + predict")

        selected_date = st.date_input("Select a date", value=pd.Timestamp.today())

        if st.button("🔍 Fetch & Predict", key="fetch_predict_button"):
            with st.spinner("Fetching articles from The Guardian..."):
                from pipeline.core.src.theguardian import fetch_archives
                
                df = fetch_archives(selected_date.year, selected_date.month)
                
                # Filtre sur la date exacte
                df["webPublicationDate"] = pd.to_datetime(df["webPublicationDate"])
                df = df[df["webPublicationDate"].dt.date == selected_date]
                
                if df.empty:
                    st.warning("No business articles found for this date.")
                else:
                    # Construire le texte
                    df["text"] = (
                        df["webTitle"].fillna("") + ". " +
                        df["fields.trailText"].fillna("") + ". " +
                        df["fields.bodyText"].fillna("")
                    )
                    
                    payload = {
                        "articles": df[["id", "text"]].to_dict(orient="records")
                    }
                    
                    with st.spinner(f"Predicting sentiment for {len(df)} articles..."):
                        result = predict(payload)
                    
                    if result and "results" in result:
                        df_results = pd.DataFrame(result["results"])
                        df_results = df_results.drop(columns=["text"])
                        
                        # Affichage
                        st.success(f"{len(df_results)} articles predicted")
                        
                        # Distribution
                        col1, col2, col3 = st.columns(3)
                        counts = df_results["sentiment_label"].value_counts()
                        col1.metric("🟢 Positive", counts.get("positive", 0))
                        col2.metric("🔴 Negative", counts.get("negative", 0))
                        col3.metric("🟡 Neutral",  counts.get("neutral", 0))
                        
                        # Tableau
                        st.dataframe(df_results)