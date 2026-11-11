import pandas as pd
import plotly.express as px
import streamlit as st

from src.config.settings import SETTINGS
from src.ui.components import df_view, filterable_table, inject_css, plot
from src.ui.source_picker import pick_sources
from src.validation.dq import (append_history, build_report, load_history, report_to_csv, report_to_json,
                               report_to_markdown, write_quarantine)
from src.validation.rules import RULESETS, validate

inject_css()
st.title("✅ Data Quality Center")
st.caption("Completeness, uniqueness, validity, consistency, accuracy, timeliness, referential integrity and schema checks.")

project = st.selectbox("Project", list(RULESETS), key="dq_project")
names = list(RULESETS[project])
raw = pick_sources(project, names, f"dq_{project}")
chosen = st.multiselect("Datasets to validate", names, default=names, key=f"dq_sel_{project}")

if st.button("Run quality checks", disabled=raw is None or not chosen):
    validators = [validate(project, d, raw[d], raw) for d in chosen]   # raw parents are the reference tables
    st.session_state["dq_run"] = (project, validators, build_report(validators))
    append_history(st.session_state["dq_run"][2], SETTINGS.dq_history_file, f"{project} (DQ center)")

stored = st.session_state.get("dq_run")
if stored and stored[0] == project:
    _, validators, report = stored
    c = st.columns(3)
    c[0].metric("Overall quality score", f"{report['overall_score']}%")
    c[1].metric("Checks passed", report["checks_passed"])
    c[2].metric("Checks failed", report["checks_failed"])
    for v in validators:
        st.subheader(f"{v.dataset} · {v.score()}%")
        rf = v.results_frame()
        rf["result"] = rf["passed"].map({True: "✅ pass", False: "❌ fail"})
        rf["pass_%"] = (rf["pass_rate"] * 100).round(2)
        df_view(rf[["dimension", "check", "result", "pass_%", "failed", "total", "blocking", "detail"]])
        failed = v.failed_records()
        with st.expander(f"Failed records ({len(failed)})"):
            if len(failed):
                filterable_table(failed, f"dq_failed_{v.dataset}", height=240)
                if st.button(f"Quarantine {v.dataset} records", key=f"dq_q_{v.dataset}"):
                    _, q = v.split()
                    path = write_quarantine(q, f"{project}_{v.dataset}", report["report_id"], SETTINGS.quarantine_dir)
                    st.success(f"Stored {len(q)} blocking-check failures at {path}" if path else "No blocking failures to store")
            else:
                st.write("No failed records")
    d1, d2, d3 = st.columns(3)
    d1.download_button("Report (JSON)", report_to_json(report), file_name="dq_report.json")
    d2.download_button("Report (CSV)", report_to_csv(report), file_name="dq_report.csv")
    d3.download_button("Report (Markdown)", report_to_markdown(report), file_name="dq_report.md")

st.subheader("Validation history")
hist = load_history(SETTINGS.dq_history_file)
if hist.empty:
    st.caption("No validation runs recorded yet.")
else:
    df_view(hist[["generated_at", "project", "overall_score", "checks_passed", "checks_failed", "report_id"]])
    plot(px.line(hist, x="generated_at", y="overall_score", color="project", markers=True, title="Quality score over time"))
