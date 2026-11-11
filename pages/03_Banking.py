import pandas as pd
import plotly.express as px
import streamlit as st

from pipelines.banking_pipeline import TABLES, run_banking
from src.config.settings import SETTINGS
from src.loading.outputs import load_gold
from src.processing.fraud_model import simulate_stream
from src.ui.analytics_views import banking_view
from src.ui.components import df_view, filterable_table, inject_css, plot
from src.ui.run_panel import run_pipeline_panel
from src.ui.source_picker import pick_sources

inject_css()
st.title("🏦 Banking Fraud Detection Pipeline")
st.caption("Batch ETL, PySpark-ready features, a Scikit-learn classifier, and a SIMULATED streaming replay.")

t_ing, t_pipe, t_model, t_stream, t_dash = st.tabs(
    ["1. Ingestion", "2. Pipeline & quality", "3. Fraud model", "4. Simulated streaming", "5. Dashboard"])

with t_ing:
    raw = pick_sources("banking", TABLES, "bank")
    st.session_state["bank_raw"] = raw
    if raw:
        for n, df in raw.items():
            with st.expander(f"{n}: {len(df):,} records"):
                filterable_table(df, f"bank_raw_{n}", height=240)
raw = st.session_state.get("bank_raw")

with t_pipe:
    st.write("Validate (ID uniqueness, account IDs, missing/invalid amounts, timestamps, fraud labels) → features → "
             "store validated records → train model.")
    delta = st.checkbox("Also write Delta Lake (needs pyspark + delta-spark)", value=False)
    res = run_pipeline_panel("Run banking pipeline", "banking_pipeline", lambda: run_banking(raw, use_delta=delta),
                             "bank_res", disabled=raw is None)
    if res:
        st.metric("Data quality score", f"{res['quality_score']}%")
        st.caption(f"Validated records stored as {res['storage']['format']} · Delta: {res['storage']['delta']}")
        q = res["quarantined"]["transactions"]
        with st.expander(f"Quarantined transactions: {len(q)}"):
            if len(q):
                st.write(q["failed_checks"].str.split("; ").explode().value_counts().rename("records").to_frame())
                filterable_table(q, "bank_q")
        with st.expander("Validated feature table"):
            filterable_table(res["features"].head(2000), "bank_feat")
res = (st.session_state.get("bank_res") or (None, None))[1]

with t_model:
    if res:
        m = res["metrics"]
        c = st.columns(4)
        c[0].metric("Precision", m["precision"]); c[1].metric("Recall", m["recall"])
        c[2].metric("F1", m["f1"]); c[3].metric("ROC AUC", m["roc_auc"])
        st.caption(f"Random forest, stratified 75/25 split ({m['train_rows']:,} train / {m['test_rows']:,} test), "
                   f"threshold {m['threshold']}. Metrics are on held-out synthetic data and say nothing about real-world accuracy.")
        cm = m["confusion"]
        plot(px.imshow([[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]], text_auto=True, x=["pred normal", "pred fraud"],
                       y=["actual normal", "actual fraud"], title="Confusion matrix"))
        plot(px.bar(res["importances"].head(10).rename("importance").reset_index(), x="importance", y="index",
                    orientation="h", title="Top feature importances"))
    else:
        st.info("Run the pipeline first.")

with t_stream:
    st.warning("SIMULATED STREAM: held-out stored transactions are replayed in time order as micro-batches. "
               "No Kafka or live banking source is connected.")
    if res:
        c1, c2 = st.columns(2)
        size = c1.slider("Micro-batch size", 25, 300, 100, 25)
        nb = c2.slider("Batches to replay", 1, 20, 8)
        if st.button("Replay simulated stream", key="bank_stream"):
            st.session_state["bank_batches"] = list(simulate_stream(res["scored"], res["model"], size, nb))
        batches = st.session_state.get("bank_batches")
        if batches:
            bdf = pd.DataFrame(batches)
            df_view(bdf)
            plot(px.line(bdf, x="batch", y=["flagged", "actual_fraud"], markers=True, title="Flagged vs actual fraud per micro-batch (simulated)"))
    else:
        st.info("Run the pipeline first.")

with t_dash:
    saved = load_gold("banking", SETTINGS.warehouse_dir)
    if saved:
        banking_view(saved[0], saved[1])
    else:
        st.info("Run the pipeline to populate the dashboard.")
