# tabs/block_admin_rollback_drift.py
import streamlit as st
from utils.api import rollback_drift


@st.fragment
def render():
    st.markdown("### Rollback Drift")

    if st.button("↩️ Rollback drift", key="rollback_button"):
        with st.spinner("Rollback..."):
            result = rollback_drift()
            if result:
                st.success(result.get("message", "Done"))
                