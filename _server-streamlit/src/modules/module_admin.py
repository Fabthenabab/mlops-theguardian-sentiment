# modules/module_admin.py
import streamlit as st

# Tabs
from tabs.block_admin_drift_report import render as render_drift_report
from tabs.block_admin_inject_drift import render as render_inject_drift
from tabs.block_admin_rollback_drift import render as render_rollback_drift


def body():
    st.title("🗃️ Admin page")
    
    # Tabs for different sections
    tab_inject_drift, tab_drift_report, tab_rollback_drift = st.tabs([
        "💉 Inject Drift",
        "📄 Check Drift Report",
        "↩️ Rollback Drift injection"
    ])
    with tab_inject_drift:
        render_inject_drift()
    with tab_drift_report:
        render_drift_report()
    with tab_rollback_drift:
        render_rollback_drift()