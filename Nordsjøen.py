import streamlit as st

from navigation import PAGES

st.set_page_config(page_title="Økokyst Nordsjøen og Skagerak", layout="wide")

page = st.navigation(PAGES)
page.run()
