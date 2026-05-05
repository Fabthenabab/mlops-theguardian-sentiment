# modules/module_transactions.py
import streamlit as st
import pandas as pd

# Cache
from utils.api import inject_drift, purge

# Tabs

def body():
    # ************************************************************************************************************
    # ========================================
    # CACHE SETUP
    # ========================================
    # Empty session_state cache of previous page
    
    # CACHE
    
    
    
    st.title("🗃️ Admin")
    st.markdown("Manage transactions")

    # ========================================
    # TABS
    # ========================================
    
    
    st.subheader("🔍 Inject Drift")

    col1, col2 = st.columns(2)
    with col1:
        n = st.number_input("Number of rows", min_value=1, value=100, step=10)
        amt_multiplier = st.number_input("Amount multiplier", min_value=0.1, value=5.0, step=0.5)
        fraud_ratio = st.slider("Fraud ratio", min_value=0.0, max_value=1.0, value=0.3, step=0.05)
    with col2:
        force_category = st.selectbox("Force category", [
            "shopping_net", "grocery_pos", "gas_transport",
            "misc_net", "shopping_pos", "misc_pos",
            "food_dining", "entertainment", "health_fitness",
            "home", "kids_pets", "personal_care", "travel",
        ])
        force_state = st.text_input("Force state", value="AK", max_chars=2)

    if st.button("🔍 Inject drift", key="inject_drift_button"):
        with st.spinner("Injecting..."):
            resp = inject_drift({
                "n": n,
                "amt_multiplier": amt_multiplier,
                "fraud_ratio": fraud_ratio,
                "force_category": force_category,
                "force_state": force_state,
            })
            st.session_state["drift_result"] = resp
            st.rerun()

    if "drift_result" in st.session_state:
        st.success(f"Injected {st.session_state['drift_result'].get('n_rows', '?')} rows")
        st.json(st.session_state["drift_result"])
        if st.button("Clear", key="clear_drift"):
            del st.session_state["drift_result"]
            st.rerun()  

    #if st.button("✔️ Purge database", key="purge_button"):
    #    with st.spinner("Purging..."):
    #        resp = purge()
    #        st.json(resp)
    
    
    # ========================================
    # CACHE CLEANING
    # ========================================
    # Send list of session_state keys for cleanup in the next page
