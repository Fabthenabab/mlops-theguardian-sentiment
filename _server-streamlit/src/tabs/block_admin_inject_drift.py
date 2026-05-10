# tabs/block_admin_inject_drift.py
import streamlit as st
from utils.api import inject_drift


@st.fragment
def render():
    st.markdown("### Inject Drift")
    
    n = st.number_input("Drifted articles to inject", min_value=1, max_value=2000, value=10)
    
    if st.button("💉 Inject drift", key="inject_button"):
        with st.spinner("Injecting..."):
            result = inject_drift(n=n)
            if result:
                st.success(result.get("message", "Done"))
                