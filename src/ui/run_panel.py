"""Run a pipeline from the UI with tracking, and show the real result (or the real failure)."""
from __future__ import annotations

from typing import Callable

import streamlit as st

from src.monitoring.tracker import run_tracked
from src.ui.components import status_badge


def run_pipeline_panel(label: str, pipeline_name: str, fn: Callable[[], dict], state_key: str,
                       retries: int = 1, disabled: bool = False, help_text: str | None = None):
    """Button + result summary. Returns the pipeline result dict, or None if not run/failed."""
    if st.button(label, key=f"btn_{state_key}", disabled=disabled, help=help_text):
        with st.spinner(f"Running {pipeline_name}..."):
            st.session_state[state_key] = run_tracked(pipeline_name, fn, max_retries=retries)
    stored = st.session_state.get(state_key)
    if not stored:
        return None
    run, result = stored
    st.markdown(f"Execution `{run.execution_id}` {status_badge(run.status)} "
                f"validation {status_badge(run.validation_status)} · retries used: {run.retries}",
                unsafe_allow_html=True)
    if run.status == "failed":
        st.error(f"Pipeline failed: {run.error_message}")
        return None
    c = st.columns(5)
    c[0].metric("Extracted", f"{run.records_extracted:,}")
    c[1].metric("Transformed", f"{run.records_transformed:,}")
    c[2].metric("Loaded", f"{run.records_loaded:,}")
    c[3].metric("Rejected", f"{run.records_rejected:,}")
    c[4].metric("Duration", f"{run.duration_seconds:.2f}s" if run.duration_seconds is not None else "n/a")
    return result
