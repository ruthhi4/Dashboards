from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


DATA_FILE = Path(__file__).resolve().parents[1] / "Oekokyst" / "Bløtbunn-EQR.xlsx"
TIME_COLUMN = "Tid_provetak"
INDEX_OPTIONS = [
    "nEQR_NQI1",
    "nEQR_H",
    "nEQR_ISI2018",
    "nEQR_NSI2018",
    "nEQR_ES100",
    "nEQR",
]
INDEX_BANDS = [
    (0.0, 0.2, "red"),
    (0.2, 0.4, "orange"),
    (0.4, 0.6, "yellow"),
    (0.6, 0.8, "green"),
    (0.8, 1.0, "#008cff4d"),
]


@st.cache_data(show_spinner=False)
def load_biota_data(path: Path) -> dict[str, pd.DataFrame]:
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path.resolve()}")

    sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")
    return {
        name: frame.rename(columns=lambda column: str(column).strip())
        for name, frame in sheets.items()
    }


st.title("Bløtbunnsindekser")

try:
    biota_sheets = load_biota_data(DATA_FILE)
except FileNotFoundError as error:
    st.error(f"Could not load biota data: {error}")
    st.stop()

if not biota_sheets:
    st.error(f"The workbook has no readable sheets: {DATA_FILE}")
    st.stop()

station_options = sorted(biota_sheets)
selected_stations = st.multiselect(
    "Velg stasjon(er)",
    options=station_options,
    default=["BT117"] if "BT117" in station_options else [],
)
selected_indices = st.multiselect(
    "Velg indeks(er) for y-aksen",
    options=INDEX_OPTIONS,
    default=["nEQR"],
)

if not selected_stations:
    st.warning("Velg minst én stasjon.")
    st.stop()

if not selected_indices:
    st.warning("Velg minst én indeks.")
    st.stop()

fig, ax = plt.subplots(figsize=(11, 5.5))
for lower, upper, color in INDEX_BANDS:
    ax.axhspan(lower, upper, color=color, alpha=0.25, zorder=0)

ax.set_ylim(0, 1)
ax.set_axisbelow(True)
plotted_series = 0
skipped_series = []

for station in selected_stations:
    sheet_data = biota_sheets[station]

    for selected_index in selected_indices:
        if TIME_COLUMN not in sheet_data.columns or selected_index not in sheet_data.columns:
            skipped_series.append(f"{station} ({selected_index})")
            continue

        plot_data = sheet_data[[TIME_COLUMN, selected_index]].copy()
        plot_data[TIME_COLUMN] = pd.to_datetime(plot_data[TIME_COLUMN], errors="coerce")
        plot_data[selected_index] = pd.to_numeric(plot_data[selected_index], errors="coerce")
        plot_data = plot_data.dropna(subset=[TIME_COLUMN, selected_index])
        plot_data = plot_data.sort_values(TIME_COLUMN)

        if plot_data.empty:
            skipped_series.append(f"{station} ({selected_index})")
            continue

        ax.plot(
            plot_data[TIME_COLUMN],
            plot_data[selected_index],
            marker="o",
            label=f"{station} | {selected_index}",
        )
        plotted_series += 1

if plotted_series:
    locator = mdates.AutoDateLocator()
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    ax.set_xlabel("Dato")
    ax.set_ylabel(selected_indices[0] if len(selected_indices) == 1 else "nEQR-indeks")
    ax.grid(True, alpha=0.3)
    ax.legend(title="Stasjon | indeks", frameon=False)
    fig.autofmt_xdate()
    st.pyplot(fig, width="stretch")
else:
    st.warning("No valid data were found for the selected stations and indices.")

if skipped_series:
    st.info(
        "No valid dates or index values for: " + ", ".join(skipped_series)
    )
