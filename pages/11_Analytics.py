import streamlit as st

from src.config.settings import SETTINGS
from src.loading.outputs import load_gold
from src.ui.analytics_views import banking_view, ecommerce_view, healthcare_view
from src.ui.components import inject_css

inject_css()
st.title("📊 Analytics Dashboard")
st.caption("Reads the most recent Gold tables saved by each project's pipeline (data/warehouse/<project>/gold).")
tabs = st.tabs(["E-commerce", "Banking", "Healthcare"])
for tab, project, view in zip(tabs, ["ecommerce", "banking", "healthcare"], [ecommerce_view, banking_view, healthcare_view]):
    with tab:
        saved = load_gold(project, SETTINGS.warehouse_dir)
        if not saved:
            st.info(f"No saved {project} results yet. Run its pipeline first.")
            continue
        gold, meta = saved
        st.caption(f"Source: {meta.get('pipeline')} · engine: {meta.get('engine')} · generated {meta.get('generated_at')}")
        view(gold, meta) if project == "banking" else view(gold)
