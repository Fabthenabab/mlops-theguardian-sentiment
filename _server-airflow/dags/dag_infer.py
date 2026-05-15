from airflow.sdk import dag
from airflow.sdk.exceptions import AirflowException
from airflow.providers.http.operators.http import HttpOperator
from airflow.providers.http.sensors.http import HttpSensor


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
    dag_id="dag_infer",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,  # Don't try to run missed runs between start_date and now
    max_active_runs=1,  # Ensure only one run at a time to avoid overlapping
    tags=["infer", "fetch", "transformers", "daily"],
)
def dag_infer():

    run_fetch = HttpOperator(
        task_id="run_fetch",
        http_conn_id="manager-server-api",
        endpoint="/run/fetch",
        method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps({}),
        response_filter=lambda r: r.json(),
        log_response=True,  # enables logging in run_fetch task logs 
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
    
    poll_fetch = HttpSensor(
        task_id="poll_fetch",
        http_conn_id="manager-server-api",
        endpoint="/status/{{ ti.xcom_pull(task_ids='run_fetch')['job_id'] }}",
        #response_check=lambda r: r.json()["status"] == "done",  # automatically pushes response from run_fetch in XCom to poll_fetch
        response_check=_check_done,
        poke_interval=30,
        timeout=600,
        mode='reschedule',  # free the slot between 2 pokes
    )
    
    run_transformers = HttpOperator(
        task_id="run_transformers",
        http_conn_id="manager-server-api",
        endpoint="/run/transformers",
        method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps({}),
        response_filter=lambda r: r.json(),
        log_response=True,  # enables logging in run_transformers task logs 
    )
    
    poll_transformers = HttpSensor(
        task_id="poll_transformers",
        http_conn_id="manager-server-api",
        endpoint="/status/{{ ti.xcom_pull(task_ids='run_transformers')['job_id'] }}",
        #response_check=lambda r: r.json()["status"] == "done",  # automatically pushes response from run_transformers in XCom to poll_transformers
        response_check=_check_done,
        poke_interval=30,
        timeout=600,
        mode='reschedule',  # free the slot between 2 pokes
    )
    
    run_fetch >> poll_fetch >> run_transformers >> poll_transformers

dag_infer()