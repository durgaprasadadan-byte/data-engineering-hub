# Testing and verified status

Run: `pytest -q` (Spark test is skipped automatically when pyspark/Java are missing).

## Verified during development (sandbox without Streamlit, PySpark, PyArrow, Plotly)
- 30 unit/integration tests passed: data quality framework (all 8 dimensions, quarantine, reports, history), ingestion
  (CSV, JSON, JSON Lines, API with retries), run tracker (success, retry, failure), E-commerce ETL, ELT (SQLite engine),
  banking pipeline and healthcare pipeline.
- ETL (Pandas) and ELT (SQL) produce the same orders, revenue, monthly revenue and segment sizes on the same input.
- All four pipelines ran successfully on the bundled CSV/JSON sample files.
- Every Streamlit page was executed against a stand-in Streamlit API to catch code errors.

## NOT verified here: please test on your machine
- Real Streamlit rendering and layout (the stand-in does not render anything), Plotly charts, Mermaid (CDN) view.
- The Spark SQL path, Delta Lake writes, PySpark banking features, Structured Streaming and Kafka code.
  Run `pytest tests/test_spark_optional.py` and `python -m scripts.spark_selftest` after installing `requirements-spark.txt`.
- PostgreSQL loading, Databricks connectivity and the Databricks notebook, the Airflow DAG.
- Parquet output (the sandbox had no pyarrow, so only the CSV fallback ran; `requirements.txt` installs pyarrow).

## Known design limits
- Fraud model metrics are on synthetic data with injected signal; they do not predict real-world performance.
- Per-account statistics in the fraud features use the whole dataset (not point-in-time), a documented simplification.
- Streaming is simulated by replaying held-out transactions; nothing connects to a live source.
- ELT quality score is measured on Silver after filtering; ETL's is measured on transformed data before quarantine, so
  ETL scores lower on the same input by design.
