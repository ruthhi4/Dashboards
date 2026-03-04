# -*- coding: utf-8 -*-
"""
Created on Sun Feb 15 08:24:23 2026

@author: rutvin
"""






import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
from PIL import Image

# =========================
# 🔧 Configuration
# =========================
# Set the path to your Excel workbook here:
#   FILE_PATH = Path("data/my_workbook.xlsx")
#   FILE_PATH = Path(r"C:\path\to\your\workbook.xlsx")
#   FILE_PATH = Path("/Users/you/path/to/workbook.xlsx")
FILE_PATH = Path(r"C:\GitHub\Dashboards\Oekokyst\merge-new.xlsx")
NROWS = None  # Optional: limit rows per sheet (None = all)

st.set_page_config(page_title="Økokyst Nordsjøen", layout="wide")
st.title("Økokyst Nordsjøen")

# =========================
# 📥 Load ALL sheets
# =========================
@st.cache_data(show_spinner=False)
def load_excel_all_sheets(path: Path, nrows=None):
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"File not found: {path.resolve()}")
    sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl", nrows=nrows)
    cleaned = {}
    for name, df_ in sheets.items():
        df_ = df_.copy()
        # Normalize column names (string + trimmed)
        df_.columns = [str(c).strip() for c in df_.columns]
        cleaned[name] = df_
    return cleaned

def likely_time_candidates(df: pd.DataFrame):
    # Prefer datetime dtype columns, then common time-like names
    dt_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    if dt_cols:
        return dt_cols
    name_hits = [c for c in df.columns if str(c).lower() in {"time", "tid", "dato", "date", "datetime", "timestamp", "sampledate"}]
    return name_hits if name_hits else df.columns.tolist()

try:
    with st.spinner("Loading workbook…"):
        all_sheets = load_excel_all_sheets(FILE_PATH, nrows=NROWS)
except Exception as e:
    st.error(f"Failed to load Excel: {e}")
    st.stop()

if not all_sheets:
    st.error("Workbook has no readable sheets.")
    st.stop()

sheet_names = list(all_sheets.keys())
st.caption(f"Reading from: `{FILE_PATH}`")




# Let the user pick one or more sheets
st.sidebar.header("1) Valg av stasjon og dyp")
selected_sheets = st.sidebar.multiselect(
    "Velg en eller flere",
    options=sheet_names,
    default=sheet_names[:1]  # default to the first sheet
)

if not selected_sheets:
    st.warning("Velg minst en")
    st.stop()

# Use the first selected sheet as the reference for columns
reference_df = all_sheets[selected_sheets[0]]
all_cols = reference_df.columns.tolist()

# =========================
# 🧭 Columns (X fixed to time)
# =========================
st.sidebar.header("2) Valg av parameter")

# Auto-detect time column from the reference sheet
def likely_time_candidates(df: pd.DataFrame):
    dt_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    if dt_cols:
        return dt_cols
    name_hits = [c for c in df.columns if str(c).lower() in {
        "time", "tid", "dato", "date", "datetime", "timestamp", "sampledate"
    }]
    return name_hits if name_hits else []

time_candidates = likely_time_candidates(reference_df)
if time_candidates:
    time_col = time_candidates[0]
else:
    # Fallback to the first column and let downstream parsing try to coerce
    time_col = all_cols[0]
    # st.warning(
    #     f"Could not confidently detect a time column; using `{time_col}` as X. "
    #     "Consider renaming your time column to something like 'Date', 'Datetime', or 'Timestamp'."
    # )

## Show (not editable) which column is used for X
#st.sidebar.markdown(f"**Time column (X-axis):** `{time_col}`")

# Y columns = remaining columns (can select multiple)
y_candidates = [c for c in all_cols if c != time_col]
numeric_guess = [c for c in y_candidates if pd.api.types.is_numeric_dtype(reference_df[c])]
default_y = numeric_guess[: min(3, len(numeric_guess))] if numeric_guess else y_candidates[:1]
y_cols = st.sidebar.multiselect("Velg en eller flere", options=y_candidates, default=default_y)

if not y_cols:
    st.warning("Velg minst en")
    st.stop()




# =========================
# 🧹 Helper conversion
# =========================
def to_datetime(series: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    try:
        return pd.to_datetime(series, errors="coerce")
    except Exception:
        return pd.to_datetime(pd.Series([], dtype="float64"), errors="coerce")  # empty if utterly fails

def to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")



# ---- Row under the plot: image + table side-by-side ----
col_img, col_tbl = st.columns([1, 2], gap="medium")  # tweak ratios as you like

with col_img:
    st.subheader("Stasjonskart")
    # Load image from file (can also be a URL or bytes)
    img = Image.open(r"C:\GitHub\Dashboards\Oekokyst\Økokyst Nordsjøen.png")  # e.g., "data/photo.png"
    st.image(img, width='stretch')

    
with col_tbl:
    st.subheader("Vannmiljøkoder")
    df = pd.read_excel(r"C:\GitHub\Dashboards\Oekokyst\Stations Nordsjøen.xlsx", sheet_name='Koder')
    # df = pd.DataFrame({
    #     "Parameter": ["pH", "SO4", "EC"],
    #     "Kode": [7.2, 52.3, 440],
    #     "Enhet": ["-", "mg/L", "µS/cm"],
    # })
    # Use dataframe for scrollable, sortable table; table() for static
    st.dataframe(df, width='stretch', height=640)






# =========================
# 📈 Plot
# =========================
st.header("Plot")

fig, ax = plt.subplots(figsize=(11, 5.5))

series_plotted = 0
skipped_info = []

for sheet in selected_sheets:
    df = all_sheets[sheet].copy()
    if time_col not in df.columns:
        skipped_info.append(f"Sheet '{sheet}' missing time column '{time_col}'. Skipped.")
        continue

    # Prepare time & sort
    df[time_col] = to_datetime(df[time_col])
    df = df[df[time_col].notna()]
    if df.empty:
        skipped_info.append(f"Sheet '{sheet}' has no valid time values after parsing. Skipped.")
        continue
    df = df.sort_values(by=time_col)

    for y in y_cols:
        if y not in df.columns:
            skipped_info.append(f"Sheet '{sheet}' missing Y column '{y}'. Skipped.")
            continue

        y_series = to_numeric(df[y])
        mask = df[time_col].notna() & y_series.notna()
        if not mask.any():
            skipped_info.append(f"Sheet '{sheet}' | '{y}': no valid numeric data to plot.")
            continue

        ax.plot(df.loc[mask, time_col], y_series.loc[mask], label=f"{sheet} | {y}")
        series_plotted += 1

# X-axis formatting if datetime-like
if series_plotted > 0:
    locator = mdates.AutoDateLocator()
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    fig.autofmt_xdate()

ax.set_xlabel('Dato')
ax.set_ylabel(", ".join(y_cols) if len(y_cols) <= 3 else "Value")
ax.grid(True, alpha=0.3)

if series_plotted > 0:
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.12), ncol=3, frameon=False)
    st.pyplot(fig, width='stretch')
else:
    st.warning("Nothing to plot after parsing and validation. Check time and Y selections.")

# =========================
# 🔎 Quick previews
# =========================
with st.expander("🔎 Preview first rows of each selected sheet"):
    for sh in selected_sheets:
        st.markdown(f"**Sheet:** `{sh}`")
        st.dataframe(all_sheets[sh].head(10), width='stretch')






# =========================
# 📝 Diagnostics
# =========================
if skipped_info:
    st.info("**Notes:**\n- " + "\n- ".join(skipped_info))



    

