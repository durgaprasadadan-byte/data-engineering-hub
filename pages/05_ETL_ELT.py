import streamlit as st

from src.diagrams.definitions import ARCHITECTURES, to_dot, to_mermaid
from src.ui.components import graph, inject_css, mermaid_view

inject_css()
st.title("🧭 Architecture: ETL, ELT, Lakehouse, Streaming")
st.caption("Diagrams are generated from code definitions in src/diagrams/definitions.py.")

tabs = st.tabs([a.title for a in ARCHITECTURES.values()])
for tab, arch in zip(tabs, ARCHITECTURES.values()):
    with tab:
        st.write(arch.summary)
        labels = {s.label: s for s in arch.stages}
        choice = st.selectbox("Select a component to explain", ["(none)"] + list(labels), key=f"sel_{arch.key}")
        stage = labels.get(choice)
        highlight = stage.id if stage else None
        graph(to_dot(arch, highlight))
        if stage:
            st.markdown(f"**{stage.label}** · `{stage.technology}`")
            st.write(stage.description)
        with st.expander("Mermaid version (loads from CDN, needs internet)"):
            mermaid_view(arch, highlight)
        d1, d2 = st.columns(2)
        d1.download_button("Download Mermaid (.mmd)", to_mermaid(arch), file_name=f"{arch.key}_architecture.mmd", key=f"mmd_{arch.key}")
        d2.download_button("Download Graphviz (.dot)", to_dot(arch), file_name=f"{arch.key}_architecture.dot", key=f"dot_{arch.key}")
        with st.expander("All stages"):
            for i, s in enumerate(arch.stages, 1):
                st.markdown(f"{i}. **{s.label}** (`{s.technology}`): {s.description}")
