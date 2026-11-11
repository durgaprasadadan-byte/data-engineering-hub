import streamlit as st

from src.ui.components import inject_css

inject_css()
st.title("Contact")
st.caption("Get in touch with Durga Prasad.")

with st.container(border=True):
    st.subheader("Durga Prasad")
    st.markdown("**Location**  \nNewark, Delaware")
    st.markdown("**Phone**  \n[+1 443 877 9272](tel:+14438779272)")
    st.markdown("**Email**  \n[durga.jinna@lindsey.edu](mailto:durga.jinna@lindsey.edu)")
