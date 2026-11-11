from pathlib import Path

import streamlit as st

from src.ui.components import inject_css

inject_css()
st.title("📚 Documentation & GitHub")
docs = {"README": Path("README.md"), "Deployment": Path("docs/DEPLOYMENT.md"),
        "Testing & limitations": Path("docs/TESTING.md")}
tabs = st.tabs(list(docs))
for tab, (name, path) in zip(tabs, docs.items()):
    with tab:
        st.markdown(path.read_text(encoding="utf-8") if path.exists() else f"{path} not found")
st.markdown("Repository: add your GitHub URL here after you push (this app does not know it).")
