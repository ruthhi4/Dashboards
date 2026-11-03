# -*- coding: utf-8 -*-
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

from navigation import HYDRO_PAGE


DATA_DIR = Path(__file__).resolve().parents[1] / "Oekokyst"
STATION_MAP_PATH = DATA_DIR / "Økokyst All.png"
STATION_CODES_PATH = DATA_DIR / "Stations Nordsjøen.xlsx"


@st.cache_data(show_spinner=False)
def load_station_map(contents: bytes) -> Image.Image:
    with Image.open(BytesIO(contents)) as image:
        return image.copy()


@st.cache_data(show_spinner=False)
def load_station_codes(contents: bytes) -> pd.DataFrame:
    return pd.read_excel(BytesIO(contents), sheet_name="Koder")


st.title("Økokyst Nordsjøen og Skagerak")
st.markdown(
    "Denne siden gir en oversikt over stasjonene og vannmiljøkodene. "
    "Bruk sidemenyen for å utforske hydrografiske data og biotadata."
)

st.subheader("Om programmet")
st.write("Legg til en introduksjon og annen informasjon om programmet her.")
st.page_link(
    HYDRO_PAGE,
    label="Se alle hydrografiske figurer",
    icon="📊",
    use_container_width=True,
)

col_img, col_tbl = st.columns([2, 1], gap="medium")

with col_img:
    st.subheader("Stasjonskart")
    st.image(load_station_map(STATION_MAP_PATH.read_bytes()), width="stretch")

with col_tbl:
    st.subheader("Vannmiljøkoder")
    station_codes = load_station_codes(STATION_CODES_PATH.read_bytes())
    st.dataframe(station_codes, width="stretch", height=640)
