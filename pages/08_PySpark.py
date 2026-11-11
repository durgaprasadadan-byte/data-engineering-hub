from pathlib import Path

import streamlit as st

from pipelines.ecommerce_elt import run_elt
from src.processing.spark_session import delta_available, spark_available
from src.ui.components import inject_css
from src.ui.run_panel import run_pipeline_panel
from src.ui.source_picker import pick_sources
from pipelines.ecommerce_etl import TABLES

inject_css()
st.title("⚡ PySpark Processing")
ok, why = spark_available()
c = st.columns(2)
c[0].metric("Spark runtime", "available" if ok else "not available")
c[1].metric("Delta Lake (delta-spark)", "installed" if delta_available() else "not installed")
st.caption(why)

st.markdown("""
The e-commerce ELT uses **one set of SQL statements** (`src/processing/sql_layers.py`) for Spark SQL, the SQLite fallback
and the Databricks notebook. Banking features and streaming have PySpark equivalents in `src/processing/spark_banking.py`.

Install locally: `pip install pyspark delta-spark` and a Java 17+ runtime. Delta jars download on first run (internet needed once).
""")
if not ok:
    st.info("Spark is not available in this environment, so the Spark button below is disabled. "
            "The same ELT still runs on SQLite from the E-commerce page.")
raw = pick_sources("ecommerce", TABLES, "spark")
res = run_pipeline_panel("Run ELT on Spark SQL", "ecommerce_elt_spark", lambda: run_elt(raw, engine="spark"),
                         "spark_elt", disabled=(not ok) or raw is None, retries=0)
if res:
    st.success(f"Engine: {res['engine']} · Delta written: {res['delta']} · {res['seconds']}s")
    st.dataframe(res["gold"]["gold_summary"])
with st.expander("PySpark banking and streaming code (src/processing/spark_banking.py)"):
    st.code(Path("src/processing/spark_banking.py").read_text(), language="python")
