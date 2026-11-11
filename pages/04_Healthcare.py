import pandas as pd
import streamlit as st

from pipelines.healthcare_pipeline import TABLES, run_healthcare
from src.config.settings import SETTINGS
from src.loading.outputs import load_gold
from src.ui.analytics_views import healthcare_view
from src.ui.components import df_view, filterable_table, inject_css
from src.ui.run_panel import run_pipeline_panel
from src.ui.source_picker import pick_sources

inject_css()
st.title("🩺 Healthcare Claims Analytics")
st.warning("Use synthetic or de-identified data only. Do not upload protected health information (PHI). "
           "The bundled sample contains no names or real identifiers.")

t_ing, t_pipe, t_ana = st.tabs(["1. Ingestion", "2. Pipeline & quality", "3. Analytics"])
with t_ing:
    raw = pick_sources("healthcare", TABLES, "hc")
    st.session_state["hc_raw"] = raw
    if raw:
        for n, df in raw.items():
            with st.expander(f"{n}: {len(df):,} records"):
                filterable_table(df, f"hc_raw_{n}", height=240)
raw = st.session_state.get("hc_raw")

with t_pipe:
    st.write("Standardize patient/provider IDs → validate claims (IDs, diagnosis, dates, amounts, duplicates, "
             "referential integrity) → Silver (with processing times) → Gold reports.")
    res = run_pipeline_panel("Run healthcare pipeline", "healthcare_pipeline", lambda: run_healthcare(raw),
                             "hc_res", disabled=raw is None)
    if res:
        st.metric("Data quality score", f"{res['quality_score']}%")
        q = res["quarantined"]["claims"]
        with st.expander(f"Quarantined claims: {len(q)}"):
            if len(q):
                st.write(q["failed_checks"].str.split("; ").explode().value_counts().rename("claims").to_frame())
                filterable_table(q, "hc_q")
        with st.expander("Silver claims (with processing_days)"):
            filterable_table(res["silver"]["claims"], "hc_silver")

with t_ana:
    saved = load_gold("healthcare", SETTINGS.warehouse_dir)
    if saved:
        st.caption(f"Saved results generated {saved[1].get('generated_at')}")
        healthcare_view(saved[0])
    else:
        st.info("Run the pipeline to see analytics.")
