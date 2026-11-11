from pathlib import Path

import streamlit as st

from src.integrations import databricks as dbx
from src.ui.components import inject_css

inject_css()
st.title("🧱 Databricks Integration")
missing = dbx.missing_settings()
c = st.columns(2)
c[0].metric("Credentials", "configured" if not missing else "missing")
c[1].metric("databricks-sql-connector", "installed" if dbx.connector_installed() else "not installed")
if missing:
    st.info("Missing environment variables: " + ", ".join(missing) +
            ". Set them in `.env` locally or in Streamlit secrets when deployed. Never commit them.")

if st.button("Test connection", disabled=bool(missing)):
    ok, msg = dbx.test_connection()
    (st.success if ok else st.error)(msg)

st.subheader("Set-up")
st.markdown("""
1. Create a Databricks workspace (the free Community/Free Edition has limits; check current availability) and a SQL warehouse.
2. Upload the sample CSVs from `data/sample/ecommerce/` to a Unity Catalog volume.
3. Import `databricks/ecommerce_elt_notebook.py` into the workspace (or clone this repo as a Git folder) and run it.
   It creates Delta tables `bronze_*`, `silver_*`, `gold_*` using the same SQL as the local project.
4. To let this app query the results, set `DATABRICKS_HOST`, `DATABRICKS_HTTP_PATH` and `DATABRICKS_TOKEN`
   (a personal access token) and `pip install databricks-sql-connector`.

**Limitations.** Streamlit Community Cloud can call the Databricks SQL warehouse over HTTPS, but it has modest resources,
so run Spark itself on Databricks (or locally), not inside the hosted app. This repository does not run Databricks
jobs for you, and none of the Databricks code was executed during development because it needs your workspace.
""")
nb = Path("databricks/ecommerce_elt_notebook.py")
if nb.exists():
    st.download_button("Download Databricks notebook", nb.read_text(), file_name=nb.name)
    with st.expander("Notebook source"):
        st.code(nb.read_text(), language="python")

st.subheader("Query a table")
cfg = dbx.get_config()
q = st.text_input("Single read-only SQL statement", "SELECT * FROM gold_summary", disabled=cfg is None)
if st.button("Run query", disabled=cfg is None):
    try:
        st.dataframe(dbx.run_query(cfg, q))
    except Exception as exc:  # noqa: BLE001
        st.error(f"Query failed: {exc}")
