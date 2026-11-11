"""Data Engineering Hub: entry point and navigation.

Run locally:  streamlit run app.py
"""
import streamlit as st

from src.config.settings import SETTINGS

st.set_page_config(page_title=SETTINGS.app_name, page_icon="🛠️", layout="wide")

navigation = st.navigation(
    {
        "Hub": [
            st.Page("pages/01_Home.py", title="Home Dashboard", icon="🏠", default=True),
            st.Page("pages/05_ETL_ELT.py", title="Architecture (ETL / ELT)", icon="🧭"),
            st.Page("pages/11_Analytics.py", title="Analytics Dashboard", icon="📊"),
        ],
        "Projects": [
            st.Page("pages/02_Ecommerce.py", title="E-commerce", icon="🛒"),
            st.Page("pages/03_Banking.py", title="Banking Fraud", icon="🏦"),
            st.Page("pages/04_Healthcare.py", title="Healthcare Claims", icon="🩺"),
        ],
        "Platform": [
            st.Page("pages/06_Data_Quality.py", title="Data Quality", icon="✅"),
            st.Page("pages/07_Monitoring.py", title="Monitoring", icon="📈"),
            st.Page("pages/08_PySpark.py", title="PySpark Processing", icon="⚡"),
            st.Page("pages/09_Databricks.py", title="Databricks", icon="🧱"),
            st.Page("pages/10_Docs.py", title="Docs & GitHub", icon="📚"),
        ],
    }
)
st.sidebar.caption(f"{SETTINGS.app_name} · env: {SETTINGS.env}")
navigation.run()
