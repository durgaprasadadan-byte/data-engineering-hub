import pandas as pd
import streamlit as st

from pipelines.ecommerce_elt import run_elt
from pipelines.ecommerce_etl import TABLES, run_etl
from src.config.settings import SETTINGS
from src.loading.outputs import load_gold
from src.processing.spark_session import spark_available
from src.processing.sql_layers import GOLD_SQL, SILVER_SQL
from src.ui.analytics_views import ecommerce_view
from src.ui.components import df_view, filterable_table, inject_css
from src.ui.run_panel import run_pipeline_panel
from src.ui.source_picker import pick_sources

inject_css()
st.title("🛒 E-commerce Data Engineering")
st.caption("Customers, orders, products, payments and inventory processed by a Pandas ETL and a SQL-based ELT.")

t_ing, t_etl, t_elt, t_ana = st.tabs(["1. Ingestion", "2. ETL (Pandas)", "3. ELT (Bronze/Silver/Gold)", "4. Analytics"])

with t_ing:
    raw = pick_sources("ecommerce", TABLES, "ecom")
    st.session_state["ecom_raw"] = raw
    if raw:
        for n, df in raw.items():
            with st.expander(f"{n}: {len(df):,} records"):
                filterable_table(df, f"ecom_raw_{n}", height=240)
raw = st.session_state.get("ecom_raw")

with t_etl:
    st.write("Extract → Staging → Transform → Validate (quarantine) → Load (Parquet/CSV + SQLite; PostgreSQL if `POSTGRES_URL` is set).")
    use_pg = st.checkbox("Also load to PostgreSQL (requires POSTGRES_URL and sqlalchemy)", value=False)
    res = run_pipeline_panel("Run ETL", "ecommerce_etl", lambda: run_etl(raw, use_postgres=use_pg), "ecom_etl",
                             disabled=raw is None, help_text=None if raw else "Load data on the Ingestion tab first")
    if res:
        st.metric("Data quality score (transformed data, before quarantine)", f"{res['quality_score']}%")
        st.subheader("Stages")
        df_view(pd.DataFrame(res["stages"]))
        st.caption(f"Storage formats: {res['storage_formats']} · PostgreSQL: {res['postgres']}")
        st.subheader("Quarantined records")
        for t, q in res["quarantined"].items():
            with st.expander(f"{t}: {len(q)} quarantined"):
                if len(q):
                    filterable_table(q, f"ecom_q_{t}", height=220)
                else:
                    st.write("None")
        st.subheader("Loaded tables")
        pick = st.selectbox("Table", list(res["tables"]), key="ecom_etl_pick")
        filterable_table(res["tables"][pick], f"ecom_clean_{pick}")

with t_elt:
    ok, why = spark_available()
    engine = st.selectbox("SQL engine", ["auto", "sqlite", "spark"], key="ecom_engine",
                          help="auto uses Spark SQL when pyspark and Java are installed, otherwise SQLite.")
    st.caption(f"Spark status: {why}. Delta Lake is written only when `delta-spark` is installed.")
    res = run_pipeline_panel("Run ELT", "ecommerce_elt", lambda: run_elt(raw, engine=engine), "ecom_elt",
                             disabled=raw is None)
    if res:
        st.success(f"Engine used: {res['engine']} · Delta written: {res['delta']} · {res['seconds']}s")
        for layer, tables in (("Bronze", res["bronze"]), ("Silver", res["silver"]), ("Gold", res["gold"])):
            with st.expander(f"{layer} layer ({len(tables)} tables)"):
                for n, df in tables.items():
                    st.markdown(f"**{n}** · {len(df):,} rows")
                    df_view(df.head(50), height=180)
    with st.expander("SQL used for Silver and Gold"):
        for name, sql in SILVER_SQL + GOLD_SQL:
            st.markdown(f"`{name}`")
            st.code(sql.strip(), language="sql")

with t_ana:
    gold = None
    for key in ("ecom_elt", "ecom_etl"):
        stored = st.session_state.get(key)
        if stored and stored[1]:
            gold, label = stored[1]["gold"], key.replace("ecom_", "").upper()
            break
    if gold is not None:
        st.caption(f"Showing results from the latest {label} run in this session.")
    else:
        saved = load_gold("ecommerce", SETTINGS.warehouse_dir)
        if saved:
            gold = saved[0]
            st.caption(f"Showing saved results from {saved[1].get('pipeline')} ({saved[1].get('generated_at')}).")
    if gold:
        ecommerce_view(gold)
    else:
        st.info("Run the ETL or ELT pipeline to see analytics.")
