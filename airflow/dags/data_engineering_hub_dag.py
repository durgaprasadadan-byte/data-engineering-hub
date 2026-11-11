"""Airflow DAG running the hub pipelines on the bundled synthetic data. Requires Apache Airflow 2.x/3.x.
Copy or symlink this file into your Airflow dags folder and set PYTHONPATH to the project root.
Not executed by the project's automated tests (Airflow is not a dependency of the Streamlit app)."""
from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG

try:
    from airflow.providers.standard.operators.python import PythonOperator  # Airflow 3
except ImportError:  # Airflow 2
    from airflow.operators.python import PythonOperator

DEFAULT_ARGS = {"owner": "data-eng", "retries": 2, "retry_delay": timedelta(minutes=2)}


def _run(project: str, pipeline: str) -> None:
    from pipelines.banking_pipeline import run_banking
    from pipelines.ecommerce_elt import run_elt
    from pipelines.ecommerce_etl import run_etl
    from pipelines.healthcare_pipeline import run_healthcare
    from src.config.settings import SETTINGS
    from src.ingestion.loaders import load_sample_dir
    from src.monitoring.tracker import run_tracked
    names = {"ecommerce": ["customers", "products", "orders", "payments", "inventory"],
             "banking": ["customers", "accounts", "transactions"],
             "healthcare": ["patients", "providers", "claims", "visits", "prescriptions"]}[project]
    raw, _ = load_sample_dir(SETTINGS.sample_dir / project, names)
    fn = {"ecommerce_etl": run_etl, "ecommerce_elt": run_elt, "banking": run_banking,
          "healthcare": run_healthcare}[pipeline]
    run, _ = run_tracked(pipeline, lambda: fn(raw), max_retries=0)   # Airflow handles retries
    if run.status != "success":
        raise RuntimeError(run.error_message)


with DAG("data_engineering_hub", default_args=DEFAULT_ARGS, schedule="@daily", start_date=datetime(2026, 1, 1),
         catchup=False, tags=["data-engineering-hub"]) as dag:
    tasks = {p: PythonOperator(task_id=p, python_callable=_run, op_kwargs={"project": proj, "pipeline": p})
             for p, proj in (("ecommerce_etl", "ecommerce"), ("ecommerce_elt", "ecommerce"),
                             ("banking", "banking"), ("healthcare", "healthcare"))}
    tasks["ecommerce_etl"] >> tasks["ecommerce_elt"]
