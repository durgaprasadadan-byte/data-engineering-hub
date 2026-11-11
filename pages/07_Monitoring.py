import pandas as pd
import plotly.express as px
import streamlit as st

from src.monitoring.run_registry import PipelineRun, append_run, load_runs, summarize
from src.ui.components import df_view, inject_css, plot
from datetime import datetime, timedelta, timezone

inject_css()
st.title("📈 Pipeline Monitoring")
st.caption("Execution history from logs/pipeline_runs.jsonl. 'actual' = produced by a real pipeline run; "
           "'sample' = labelled demonstration rows.")

with st.sidebar:
    include_sample = st.checkbox("Include sample demonstration runs", value=False)
    if st.button("Add labelled sample demo runs"):
        now = datetime.now(timezone.utc)
        for i, (st_, err) in enumerate([("success", None), ("success", None), ("failed", "ConnectionError: demo failure")]):
            start = now - timedelta(minutes=10 - i)
            append_run(PipelineRun("demo_pipeline", st_, source="sample", start_time=start.isoformat(),
                                   end_time=(start + timedelta(seconds=12 + i)).isoformat(), records_extracted=1000,
                                   records_transformed=950, records_loaded=940, records_rejected=60,
                                   validation_status="passed" if st_ == "success" else "failed",
                                   quality_score=94.0, error_message=err, retries=1 if err else 0))
        st.rerun()

runs = [r for r in load_runs() if include_sample or r.source == "actual"]
if not runs:
    st.info("No executions recorded yet. Run a pipeline from a project page.")
    st.stop()

s = summarize(runs, include_sample)
c = st.columns(5)
c[0].metric("Executions", s["total"]); c[1].metric("Succeeded", s["success"]); c[2].metric("Failed", s["failed"])
c[3].metric("Records loaded", f"{s['records_processed']:,}")
c[4].metric("Avg quality", f"{s['quality_score']}%" if s["quality_score"] is not None else "n/a")

df = pd.DataFrame([{**r.__dict__, "duration_s": r.duration_seconds} for r in runs])
f1, f2 = st.columns(2)
pipes = f1.multiselect("Pipeline", sorted(df["pipeline_name"].unique()), default=sorted(df["pipeline_name"].unique()))
stat = f2.multiselect("Status", sorted(df["status"].unique()), default=sorted(df["status"].unique()))
view = df[df["pipeline_name"].isin(pipes) & df["status"].isin(stat)].sort_values("start_time", ascending=False)
df_view(view[["pipeline_name", "execution_id", "source", "start_time", "end_time", "duration_s", "records_extracted",
              "records_transformed", "records_loaded", "records_rejected", "validation_status", "status", "retries"]])

fails = view[view["status"] == "failed"]
if len(fails):
    st.subheader("Failure messages")
    df_view(fails[["pipeline_name", "execution_id", "start_time", "retries", "error_message"]])

left, right = st.columns(2)
with left:
    plot(px.bar(view, x="start_time", y="duration_s", color="pipeline_name", title="Duration by run (s)"))
with right:
    flow = view.melt(id_vars=["execution_id", "pipeline_name"],
                     value_vars=["records_extracted", "records_loaded", "records_rejected"])
    plot(px.bar(flow, x="pipeline_name", y="value", color="variable", barmode="group", title="Records per pipeline"))
