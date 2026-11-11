import pandas as pd
import plotly.express as px
import streamlit as st

from src.config.settings import PROJECTS, ROADMAP, SETTINGS
from src.monitoring.run_registry import load_runs, summarize
from src.ui.components import card, df_view, inject_css, plot

inject_css()
st.title(f"🛠️ {SETTINGS.app_name}")
st.caption(SETTINGS.tagline)

runs = load_runs()
stats = summarize(runs)

c = st.columns(6)
c[0].metric("Projects", len(PROJECTS))
c[1].metric("Pipeline executions", stats["total"])
c[2].metric("Successful", stats["success"])
c[3].metric("Failed", stats["failed"])
c[4].metric("Data quality score", f"{stats['quality_score']}%" if stats["quality_score"] is not None else "n/a")
c[5].metric("Records processed", f"{stats['records_processed']:,}")

if stats["total"] == 0:
    st.info("No pipeline has been executed yet, so these metrics are zero. They come only from real runs "
            "recorded in logs/pipeline_runs.jsonl. Open a project page and run a pipeline.")

st.subheader("Projects")
cols = st.columns(len(PROJECTS))
for col, p in zip(cols, PROJECTS):
    with col:
        card(p["name"], p["scenario"], badge=p["status"], kind="ok")

left, right = st.columns([3, 2])
with left:
    st.subheader("Implementation roadmap")
    df_view(pd.DataFrame(ROADMAP))
with right:
    st.subheader("Executions by pipeline and status")
    actual = [r for r in runs if r.source == "actual"]
    if actual:
        df = pd.DataFrame([{"pipeline": r.pipeline_name, "status": r.status} for r in actual])
        counts = df.groupby(["pipeline", "status"]).size().reset_index(name="runs")
        plot(px.bar(counts, x="pipeline", y="runs", color="status", barmode="stack"))
    else:
        st.caption("Chart appears after the first real pipeline run.")
