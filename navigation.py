import streamlit as st

HOME_PAGE = st.Page(
    "pages/0_Hjem.py",
    title="Hjem",
    icon="🏠",
    default=True,
)
HYDRO_PAGE = st.Page(
    "pages/1_Hydrografisk_data.py",
    title="Hydrografisk data",
    icon="📊",
)
BIOTA_PAGE = st.Page(
    "pages/2_Biota_data.py",
    title="Biota data",
    icon="🦠",
)

PAGES = [HOME_PAGE, HYDRO_PAGE, BIOTA_PAGE]
