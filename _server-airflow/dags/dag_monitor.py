from airflow.sdk import dag, task
from airflow.sdk.exceptions import AirflowException
from airflow.providers.http.operators.http import HttpOperator
from airflow.providers.http.sensors.http import HttpSensor
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.task.trigger_rule import TriggerRule


import json
from datetime import datetime

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@dag(
    dag_id="dag_monitor",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,  # Don't try to run missed runs between start_date and now
    max_active_runs=1,  # Ensure only one run at a time to avoid overlapping
    tags=["monitor", "drift", "evidently", "retrain"],
)
def dag_monitor():
        
    run_monitor = HttpOperator(
        task_id="run_monitor",
        http_conn_id="manager-server-api",  # connection name defined in airflow connexions
        endpoint="/run/monitor?mode=compare",
        method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps({}),
        response_filter=lambda r: r.json(),
        log_response=True,  # enables logging in run_monitor task logs 
    )

    def _check_done(response):
        # Enable fast failure of sensor if the job fails (status= 'error')
        # instead of waiting for whole timeout
        payload = response.json()
        status = payload.get("status")
        if status == "done":
            return True
        if status in ("error",):
            raise AirflowException(f"Job failed: {payload}")
        return False  # still running, keep polling
    
    poll_monitor = HttpSensor(
        task_id="poll_monitor",
        http_conn_id="manager-server-api",
        endpoint="/status/{{ ti.xcom_pull(task_ids='run_monitor')['job_id'] }}",
        #response_check=lambda r: r.json()["status"] == "done",  # automatically pushes response from run_monitor in XCom to poll_monitor
        response_check=_check_done,
        poke_interval=30,
        timeout=600,
        mode='reschedule',  # free the slot between 2 pokes
    )
    
    run_get_drift_report = HttpOperator(
        task_id="run_get_drift_report",
        http_conn_id="manager-server-api",  # connection name defined in airflow connexions
        endpoint="/admin/drift-report/{{ ti.xcom_pull(task_ids='run_monitor')['job_id'] }}",
        method="GET",
        response_filter=lambda r: r.json(),
        log_response=True,  # enables logging in run_monitor task logs 
    )
    
    @task.branch(task_id="check_drift")
    def check_drift(ti) -> str:
        # Pull the drift report from XCom and check the drift score
        drift_report = ti.xcom_pull(task_ids='run_get_drift_report')
        if drift_report and drift_report.get("drift"):
            return "retrain_on_drift"
        else:
            return "skip_retrain"
    
    branch = check_drift()

    retrain_on_drift = HttpOperator(
        task_id="retrain_on_drift",
        http_conn_id="manager-server-api",
        endpoint="/run/prophet?retrain=evidently_drift",
        method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps({}),
        response_filter=lambda r: r.json(),
        log_response=True,  # enables logging in run_forecast task logs
    )
    
    skip_retrain = EmptyOperator(task_id="skip_retrain")
    
    poll_retrain = HttpSensor(
        task_id="poll_retrain",
        http_conn_id="manager-server-api",
        endpoint="/status/{{ ti.xcom_pull(task_ids='retrain_on_drift')['job_id'] }}",
        #response_check=lambda r: r.json()["status"] == "done",  # automatically pushes response from run_forecast in XCom to poll_forecast
        response_check=_check_done,
        poke_interval=30,
        timeout=600,
        mode='reschedule',  # free the slot between 2 pokes
    )
    
    @task(trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS)
    def end_monitor():
        # 2 tasks will lead to this function call
        # so we need to set a trigger rule
        # telling that only one of the upstream task has to be a success (ALL_SUCCESS by default)
        logger.info("dag_monitor ended properly")
    
    clean_end = end_monitor()
    
    run_monitor >> poll_monitor >> run_get_drift_report >> branch
    branch >> [retrain_on_drift, skip_retrain]
    retrain_on_drift >> poll_retrain >> clean_end
    skip_retrain >> clean_end

dag_monitor()