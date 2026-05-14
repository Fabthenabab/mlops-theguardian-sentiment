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
    dag_id="dag_snapshot",
    schedule="@monthly",
    start_date=datetime(2026, 1, 1),
    catchup=False,  # Don't try to run missed runs between start_date and now
    max_active_runs=1,  # Ensure only one run at a time to avoid overlapping
    tags=["monitor", "snapshot"],
)
def dag_snapshot():
    
    run_snapshot = HttpOperator(
        task_id="run_snapshot",
        http_conn_id="manager-server-api",  # connection name defined in airflow connexions
        endpoint="/run/monitor?mode=snapshot",
        method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps({}),
        response_filter=lambda r: r.json(),
        log_response=True,  # enables logging in run_snapshot task logs 
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

    poll_snapshot = HttpSensor(
        task_id="poll_snapshot",
        http_conn_id="manager-server-api",
        endpoint="/status/{{ ti.xcom_pull(task_ids='run_snapshot')['job_id'] }}",
        #response_check=lambda r: r.json()["status"] == "done",  # automatically pushes response from run_snapshot in XCom to poll_snapshot
        response_check=_check_done,
        poke_interval=30,
        timeout=600,
        mode='reschedule',  # free the slot between 2 pokes
    )
    
    run_snapshot >> poll_snapshot

dag_snapshot()