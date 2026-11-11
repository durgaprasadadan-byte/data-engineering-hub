"""Reusable Streamlit UI components."""
from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from src.diagrams.definitions import Architecture, to_mermaid

_CSS = """
<style>
.hub-card{border:1px solid #E2E8F0;border-radius:12px;padding:1rem 1.2rem;background:#fff;margin-bottom:.5rem}
.hub-card h4{margin:0 0 .3rem 0}
.hub-badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:.75rem;font-weight:600}
.hub-ok{background:#DCFCE7;color:#166534}.hub-warn{background:#FEF9C3;color:#854D0E}
.hub-bad{background:#FEE2E2;color:#991B1B}.hub-muted{background:#E2E8F0;color:#334155}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def card(title: str, body: str, badge: str | None = None, kind: str = "muted") -> None:
    badge_html = f'<span class="hub-badge hub-{kind}">{badge}</span>' if badge else ""
    st.markdown(f'<div class="hub-card"><h4>{title} {badge_html}</h4><div>{body}</div></div>',
                unsafe_allow_html=True)


def coming_soon(title: str, phase: str, planned: list[str]) -> None:
    """Honest placeholder for modules not yet implemented."""
    inject_css()
    st.title(title)
    st.info(f"Not implemented yet. Scheduled for {phase}. Nothing on this page is real output.")
    st.subheader("Planned scope")
    for item in planned:
        st.markdown(f"- {item}")


def mermaid_view(arch: Architecture, highlight: str | None = None, height: int = 260) -> None:
    """Render Mermaid in the browser (needs internet access to load the Mermaid library)."""
    code = to_mermaid(arch, highlight)
    html = f"""
    <div class="mermaid">{code}</div>
    <script type="module">
      import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.esm.min.mjs";
      mermaid.initialize({{startOnLoad: true, securityLevel: "strict"}});
    </script>"""
    components.html(html, height=height, scrolling=True)


# ---- version-tolerant wrappers (Streamlit renamed use_container_width -> width="stretch") ----
def _stretch(fn, *args, **kwargs):
    try:
        return fn(*args, width="stretch", **kwargs)
    except Exception:  # noqa: BLE001 - older Streamlit
        return fn(*args, use_container_width=True, **kwargs)


def df_view(df, **kwargs) -> None:
    _stretch(st.dataframe, df, hide_index=True, **kwargs)


def plot(fig) -> None:
    _stretch(st.plotly_chart, fig)


def graph(dot: str) -> None:
    try:
        _stretch(st.graphviz_chart, dot)
    except Exception:  # noqa: BLE001
        st.graphviz_chart(dot)


def filterable_table(df, key: str, height: int = 320) -> None:
    """Table with a column selector, a contains-filter and CSV download."""
    c1, c2 = st.columns([1, 2])
    col = c1.selectbox("Filter column", ["(all columns)"] + list(df.columns), key=f"{key}_col")
    query = c2.text_input("Contains", key=f"{key}_q")
    view = df
    if query:
        if col == "(all columns)":
            mask = df.astype(str).apply(lambda s: s.str.contains(query, case=False, na=False, regex=False)).any(axis=1)
        else:
            mask = df[col].astype(str).str.contains(query, case=False, na=False, regex=False)
        view = df[mask]
    st.caption(f"{len(view):,} of {len(df):,} rows")
    df_view(view, height=height)
    st.download_button("Download CSV", view.to_csv(index=False), file_name=f"{key}.csv", mime="text/csv", key=f"{key}_dl")


def status_badge(status: str) -> str:
    kind = {"success": "ok", "passed": "ok", "failed": "bad", "quarantined": "warn", "running": "warn"}.get(status, "muted")
    return f'<span class="hub-badge hub-{kind}">{status}</span>'
