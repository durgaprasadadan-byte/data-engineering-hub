# Data Engineering Hub

*Building Scalable, Reliable, and Intelligent Data Pipelines.*

An interactive Streamlit portfolio of three end-to-end data engineering projects. Runs fully locally on synthetic data;
Spark, Delta Lake, PostgreSQL, Databricks and Airflow are optional extras.

| Project | What it does |
|---|---|
| E-commerce | Pandas ETL and SQL ELT (Bronze/Silver/Gold), quarantine, revenue / AOV / segmentation / product analytics |
| Banking fraud | Validation, causal frequency features, account statistics, Scikit-learn model, **simulated** streaming replay |
| Healthcare claims | ID standardization, claim validation and duplicate detection, processing times, cost and provider reports (synthetic data only) |

## Quick start
```bash
pip install -r requirements.txt
streamlit run app.py
pytest -q
```
Optional: `pip install -r requirements-spark.txt` (needs Java 17) for Spark SQL, Delta Lake, PostgreSQL and Databricks SQL.

## Pages
Home · Architecture (ETL, ELT, Lakehouse, Streaming; downloadable `.mmd` / `.dot`) · Analytics · E-commerce · Banking ·
Healthcare · Data Quality · Monitoring · PySpark · Databricks · Docs.

## Code map
| Path | Purpose |
|---|---|
| `src/ingestion/loaders.py` | CSV, JSON, JSON Lines, REST API (retries, http/https only), sample directories |
| `src/validation/dq.py` | Reusable quality framework: completeness, uniqueness, validity, consistency, accuracy, timeliness, referential integrity, schema; failed records, quarantine, JSON/CSV/Markdown reports, history |
| `src/validation/rules.py` | Rule sets per project and dataset |
| `src/transformation/` | Pandas transformations per project |
| `src/processing/` | Shared Spark/SQLite SQL (`sql_layers.py`), Spark session/ELT, fraud model, PySpark banking and streaming code |
| `src/loading/` | Parquet (CSV fallback), SQLite, optional PostgreSQL, Gold output persistence |
| `src/monitoring/` | Logging, run registry (`actual` vs `sample`), retrying tracker |
| `pipelines/` | `ecommerce_etl`, `ecommerce_elt`, `banking_pipeline`, `healthcare_pipeline` |
| `airflow/dags/`, `databricks/` | Airflow DAG and Databricks notebook (not executed in tests) |
| `data/sample/` | Synthetic sample data with injected defects; regenerate with `python -m scripts.generate_sample_data` |

## Honesty rules built in
- Home and Monitoring show only runs actually executed (`logs/pipeline_runs.jsonl`); demo rows are labelled `sample` and hidden by default.
- Streaming is labelled SIMULATED. Databricks, Spark, Kafka and PostgreSQL features say what they need and what happens without it.
- No credentials in the repo; configuration comes from environment variables or Streamlit secrets (`.env.example`).

See `docs/TESTING.md` for what was verified and what still needs your testing, and `docs/DEPLOYMENT.md` for GitHub and Streamlit Cloud steps.
