# tabs/block_admin_drift_report.py
import streamlit as st
import time
from utils.api import run_monitor, get_status, get_drift_report


# Get Drift report on the last run
# To do so, this block needs 2 API calls
# First run a monitor on /run/monitor
# Then call /admin/drift-report/{job_id}
# It needs to get the job_id of the monitor, ONLY once the job is done (status =done)
# So we store the job_id in session_state and watch the job status
# until it's in done state in table theguardian.jobs


@st.fragment
def render():
    st.markdown("### Drift report")
    
    # Run monitor
    if st.button("↩️ Run Monitor", key="run_monitor_button"):
        with st.spinner("Running..."):
            result = run_monitor(mode="compare")
            if result:
                job_id = result.get('job_id')
                # store in session_state
                st.session_state["job_id"] = job_id
                st.success(f"Monitor started - job_id: {job_id}")
                
    # Poll status if job is running
    if "job_id" in st.session_state:
        job_id = st.session_state["job_id"]
        job_status = get_status(job_id).get('status')
        
        if job_status:
            if job_status == "done":
                # Fetch report for this job_id
                report = get_drift_report(job_id=job_id)
                if report:
                    drift = report.get("drift")
                    score = report.get("drift_score")
                    run_date = report.get("run_date")
                    
                    color = "🔴" if drift else "🟢"
                    st.markdown(f"### {color} {'Drift detected' if drift else 'No drift'}")

                    col1, col2, col3 = st.columns(3)
                    col1.metric("Drift score", f"{score:.2f}")
                    col2.metric("Run date", run_date)
                    col3.metric("Status", "⚠️ Drift" if drift else "✅ Stable")
                    
                    if drift:
                        st.warning("Prophet retraining recommended")
                    
                    del st.session_state["job_id"]
                else:
                    st.error("Report not found")
            
            elif job_status == "error":
                st.error(f"Worker error: {job_status}")
                del st.session_state["job_id"]
            
            elif job_status in ("started", "running"):
                placeholder = st.empty()
                while job_status in ("started", "running"):
                    placeholder.info(f"Worker running... status: {job_status}")
                    time.sleep(3)
                    job_status = get_status(job_id).get('status')
                placeholder.empty()
                st.rerun()

