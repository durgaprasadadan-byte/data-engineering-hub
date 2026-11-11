import streamlit as st

from src.ui.components import inject_css

inject_css()
st.title("Work experience")
st.caption("Professional experience across software development, data engineering, and analytics.")

with st.container(border=True):
    st.subheader("Software Developer")
    st.markdown("**Infosys** · Full-time")
    st.caption("Mar 2024 – Nov 2025 · Newark, Delaware (Hybrid)")
    st.markdown("Client-facing consulting engagement")

with st.container(border=True):
    st.subheader("Data Engineer")
    st.markdown("**PNC** · Contract")
    st.caption("Jun 2023 – Feb 2024 · Remote")

with st.container(border=True):
    st.subheader("Data Analyst")
    st.markdown("**Omnicom Health** · Full-time")
    st.caption("Oct 2020 – Jul 2021 · Hyderabad")
