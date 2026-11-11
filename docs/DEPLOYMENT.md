# Deployment

## Local
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt            # add: -r requirements-spark.txt for Spark/Delta/Databricks/PostgreSQL
cp .env.example .env
python -m scripts.generate_sample_data     # optional: regenerates data/sample (already included)
streamlit run app.py
```

## GitHub
```bash
git init && git add . && git commit -m "Data Engineering Hub"
git branch -M main && git remote add origin <your-repo-url> && git push -u origin main
```
`.gitignore` excludes `.env`, logs, warehouse output, quarantine files and Streamlit secrets.

## Streamlit Community Cloud
1. Sign in at share.streamlit.io with GitHub and choose **Create app**.
2. Select the repository, branch `main` and main file `app.py`.
3. Under **Advanced settings** pick a Python version and paste secrets (TOML), for example:
   ```toml
   APP_ENV = "cloud"
   DATABRICKS_HOST = "<workspace-host>"
   DATABRICKS_HTTP_PATH = "<sql-warehouse-http-path>"
   DATABRICKS_TOKEN = "<personal-access-token>"
   ```
   Top-level secrets are also exposed to the app as environment variables, which is how `src/integrations/databricks.py` reads them.
4. Deploy. The app uses the bundled synthetic data, so no external service is required.

Notes
- The hosted filesystem is ephemeral: run history, warehouse files and quarantine output reset on restart.
- Use `requirements.txt` only for the hosted app. PySpark is not practical on the hosted tier; run Spark locally or on Databricks.
- The app can query a Databricks SQL warehouse over HTTPS (needs `databricks-sql-connector`, see `requirements-spark.txt`),
  but it cannot run Spark jobs on Databricks itself.
- Never commit `.env` or `secrets.toml`; rotate any token that is ever committed.

## Airflow
Install Airflow separately, copy `airflow/dags/data_engineering_hub_dag.py` into your dags folder and put the project root on `PYTHONPATH`.
The DAG runs the four pipelines on the sample data with 2 retries per task.
