# tabs/block_predict_fetch_theguardian.py
import streamlit as st
import pandas as pd

from pipeline.core.src.theguardian import fetch_archives
from utils.api import predict

@st.fragment
def render():
    st.markdown("### Live Guardian fetch + predict")

    selected_date = st.date_input("Select a date", value=pd.Timestamp.today())

    if st.button("🔍 Fetch & Predict", key="fetch_predict_button"):
        with st.spinner("Fetching articles from The Guardian..."):
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