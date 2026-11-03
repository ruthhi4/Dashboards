# -*- coding: utf-8 -*-
"""
Created on Sun Feb 15 08:24:23 2026

@author: rutvin
"""
import streamlit as st
import pandas as pd
import numpy as np
import re
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Patch
from io import BytesIO
from pathlib import Path

# =========================
# 🔧 Configuration
# =========================
DATA_DIR = Path(__file__).resolve().parents[1] / "Oekokyst"
FILE_PATH = DATA_DIR / "merge-new2.xlsx"
SIKTEDYP_FILE = DATA_DIR / "Siktedyp.xlsx"

NROWS = None  # Optional: limit rows per sheet (None = all)

st.title("Hydrografisk data")

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

try:
    with st.spinner("Loading workbook…"):
        all_sheets = load_excel_all_sheets(FILE_PATH, nrows=NROWS)
except Exception as e:
    st.error(f"Failed to load Excel: {e}")
    st.stop()

if not all_sheets:
    st.error("Workbook has no readable sheets.")
    st.stop()

depth_order = {"0m": 0, "5m": 1, "10m": 2, "20m": 3, "30m": 4}


def station_sheet_sort_key(sheet_name: str):
    station_name, _, depth = sheet_name.rpartition("_")
    station_parts = re.split(r"(\d+)", station_name.casefold())
    station_key = tuple(
        (1, int(part)) if part.isdigit() else (0, part)
        for part in station_parts
        if part
    )
    return (
        station_key,
        depth_order.get(depth.casefold(), len(depth_order)),
        depth.casefold()
    )


sheet_names = sorted(all_sheets, key=station_sheet_sort_key)
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
        return pd.to_datetime(series, errors="coerce", format="mixed")
    except Exception:
        return pd.to_datetime(pd.Series([], dtype="float64"), errors="coerce")  # empty if utterly fails

def to_numeric(series: pd.Series) -> pd.Series:

    def convert_value(value):

        if pd.isna(value):
            return np.nan

        value = str(value).strip()

        # Handle values below detection limit
        if value.startswith("<"):

            value = (
                value
                .replace("<", "")
                .replace("=", "")
                .replace(",", ".")
                .strip()
            )

            try:
                return float(value) / 2
            except ValueError:
                return np.nan

        # Handle ordinary numeric values
        value = value.replace(",", ".")

        try:
            return float(value)
        except ValueError:
            return np.nan

    return series.apply(convert_value)

st.markdown(
        """
        <nav aria-label="Plottnavigasjon" style="display:flex; flex-wrap:wrap; gap:0.5rem; margin:1rem 0 2rem;">
            <a href="#overview-plot" style="padding:0.45rem 0.75rem; border:1px solid currentColor; border-radius:4px; color:inherit; text-decoration:none;">Oversiktsplot</a>
            <a href="#year-comparison-plot" style="padding:0.45rem 0.75rem; border:1px solid currentColor; border-radius:4px; color:inherit; text-decoration:none;">Sammenligning av år</a>
            <a href="#winter-average-plot" style="padding:0.45rem 0.75rem; border:1px solid currentColor; border-radius:4px; color:inherit; text-decoration:none;">Vintermiddel</a>
            <a href="#summer-average-plot" style="padding:0.45rem 0.75rem; border:1px solid currentColor; border-radius:4px; color:inherit; text-decoration:none;">Sommermiddel</a>
            <a href="#siktedyp-plot" style="padding:0.45rem 0.75rem; border:1px solid currentColor; border-radius:4px; color:inherit; text-decoration:none;">Siktedyp</a>
            <a href="#klfa-annual-plot" style="padding:0.45rem 0.75rem; border:1px solid currentColor; border-radius:4px; color:inherit; text-decoration:none;">KLFA årsverdier</a>
        </nav>
        """,
        unsafe_allow_html=True
)






# =========================
# 📈 Plot
# =========================
st.markdown('<div id="overview-plot"></div>', unsafe_allow_html=True)
st.header("Oversiktsplot")

fig, ax = plt.subplots(figsize=(11, 5.5))

series_plotted = 0
skipped_info = []

for sheet in selected_sheets:
    df = all_sheets[sheet].copy()
    if time_col not in df.columns:
        skipped_info.append(f"Sheet '{sheet}' missing time column '{time_col}'. Skipped.")
        continue

    df[time_col] = to_datetime(df[time_col].astype(str).str.strip())
    df = df[df[time_col].notna()].copy()
    if df.empty:
        skipped_info.append(f"Sheet '{sheet}' has no valid time values after parsing. Skipped.")
        continue
    df = df.sort_values(time_col)

    for y in y_cols:
        if y not in df.columns:
            skipped_info.append(f"Sheet '{sheet}' missing Y column '{y}'. Skipped.")
            continue

        y_series = to_numeric(df[y])
        mask = y_series.notna()
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

# =========================
# 📆 Plot for selected years
# =========================
st.markdown('<div id="year-comparison-plot"></div>', unsafe_allow_html=True)
st.markdown('<div id="year-comparison-plot"></div>', unsafe_allow_html=True)
st.header("Sammenligning av valgte år")

# Find available years for the selected stations
available_years = set()

for sheet in selected_sheets:
    df_years = all_sheets[sheet].copy()

    if time_col not in df_years.columns:
        continue


    dates = to_datetime(df_years[time_col])

    available_years.update(
        dates.dropna().dt.year.astype(int).tolist()
    )

available_years = sorted(available_years, reverse=True)

if not available_years:
    st.warning("Fant ingen gyldige år for de valgte stasjonene.")

else:
    # Select one or more years
    selected_years = st.multiselect(
        "Velg ett eller flere år",
        options=available_years,
        default=available_years[:1]
    )

    if not selected_years:
        st.warning("Velg minst ett år.")

    else:
        fig_year, ax_year = plt.subplots(figsize=(11, 5.5))

        series_plotted_year = 0
        skipped_year = []

        for sheet in selected_sheets:
            df_year = all_sheets[sheet].copy()

            if time_col not in df_year.columns:
                skipped_year.append(
                    f"Sheet '{sheet}' mangler "
                    f"datokolonnen '{time_col}'."
                )
                continue

            # Convert date column
            df_year[time_col] = to_datetime(
                df_year[time_col]
            )

            # Keep rows from selected years
            df_year = df_year[
                df_year[time_col].notna()
                & df_year[time_col].dt.year.isin(
                    selected_years
                )
            ].copy()

            if df_year.empty:
                skipped_year.append(
                    f"Sheet '{sheet}' har ingen data "
                    f"for de valgte årene."
                )
                continue

            # Save the original year
            df_year["plot_year"] = (
                df_year[time_col].dt.year
            )

            # Create a common X-axis using the year 2000.
            # Year 2000 is used because it supports 29 February.
            df_year["plot_date"] = pd.to_datetime({
                "year": 2000,
                "month": df_year[time_col].dt.month,
                "day": df_year[time_col].dt.day
            })

            df_year = df_year.sort_values("plot_date")

            for y in y_cols:
                if y not in df_year.columns:
                    skipped_year.append(
                        f"Sheet '{sheet}' mangler "
                        f"parameteren '{y}'."
                    )
                    continue

                df_year[y] = to_numeric(df_year[y])

                for year in selected_years:
                    year_data = df_year[
                        df_year["plot_year"] == year
                    ].copy()

                    mask = (
                        year_data["plot_date"].notna()
                        & year_data[y].notna()
                    )

                    if not mask.any():
                        skipped_year.append(
                            f"Sheet '{sheet}' | '{y}': "
                            f"ingen gyldige data for {year}."
                        )
                        continue

                    ax_year.plot(
                        year_data.loc[mask, "plot_date"],
                        year_data.loc[mask, y],
                        marker="o",
                        linewidth=1.5,
                        markersize=5,
                        label=f"{sheet} | {y} | {year}"
                    )

                    series_plotted_year += 1

        if series_plotted_year > 0:
            # Show months on the X-axis
            ax_year.xaxis.set_major_locator(
                mdates.MonthLocator()
            )

            ax_year.xaxis.set_major_formatter(
                mdates.DateFormatter("%b")
            )

            # Always show the complete year
            ax_year.set_xlim(
                pd.Timestamp("2000-01-01"),
                pd.Timestamp("2000-12-31")
            )

            ax_year.set_xlabel("Måned")

            ax_year.set_ylabel(
                ", ".join(y_cols)
                if len(y_cols) <= 3
                else "Verdi"
            )

            ax_year.grid(True, alpha=0.3)

            ax_year.legend(
                loc="upper center",
                bbox_to_anchor=(0.5, 1.18),
                ncol=3,
                frameon=False
            )

            fig_year.tight_layout()

            st.pyplot(
                fig_year,
                width="stretch"
            )

            plt.close(fig_year)

        else:
            plt.close(fig_year)

            st.warning(
                "Ingen gyldige data å plotte "
                "for de valgte årene."
            )

        if skipped_year:
            with st.expander(
                "Merknader for valgte år"
            ):
                for message in skipped_year:
                    st.write(f"- {message}")

# =========================
# ❄️☀️ Seasonal averages with boundary shading
# =========================
st.header("Sesongmiddel")


# --------------------------------------------------
# Boundary file configuration
# --------------------------------------------------
BOUNDARY_FILE = DATA_DIR / "Boundary_values.xlsx"
CHLA_BOUNDARY_FILE = DATA_DIR / "Boundary_values_Chla.xlsx"
WATER_TYPES_FILE = DATA_DIR / "Water_types.xlsx"

BOUNDARY_SHEET = "Sheet1"


# --------------------------------------------------
# Load boundary values
# --------------------------------------------------
@st.cache_data(show_spinner=False)
def load_boundary_values(
    workbook_contents: bytes,
    sheet_name: str
) -> pd.DataFrame:

    required_columns = {
        "Parameter",
        "Sesong",
        "Klasse",
        "Nedre",
        "Ovre",
        "Farge"
    }

    boundary_df = pd.read_excel(
        BytesIO(workbook_contents),
        sheet_name=sheet_name,
        engine="openpyxl"
    )

    # Clean column names
    boundary_df.columns = [
        str(column).strip()
        for column in boundary_df.columns
    ]

    missing_columns = (
        required_columns
        - set(boundary_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Følgende kolonner mangler i "
            "grenseverdifilen: "
            + ", ".join(sorted(missing_columns))
        )

    # Clean text columns
    text_columns = [
        "Parameter",
        "Sesong",
        "Klasse",
        "Farge"
    ]

    for column in text_columns:
        boundary_df[column] = (
            boundary_df[column]
            .astype("string")
            .str.strip()
        )

    # Convert decimal commas if necessary
    for column in ["Nedre", "Ovre"]:

        boundary_df[column] = (
            boundary_df[column]
            .astype("string")
            .str.replace(",", ".", regex=False)
        )

        boundary_df[column] = pd.to_numeric(
            boundary_df[column],
            errors="coerce"
        )

    # Remove rows without complete boundaries
    boundary_df = boundary_df.dropna(
        subset=[
            "Parameter",
            "Sesong",
            "Nedre",
            "Ovre"
        ]
    ).copy()

    # Remove invalid ranges
    boundary_df = boundary_df[
        boundary_df["Nedre"]
        < boundary_df["Ovre"]
    ].copy()

    return boundary_df


@st.cache_data(show_spinner=False)
def load_chla_boundaries(workbook_contents: bytes) -> pd.DataFrame:
    boundary_df = pd.read_excel(
        BytesIO(workbook_contents),
        sheet_name=BOUNDARY_SHEET,
        engine="openpyxl"
    )
    boundary_df.columns = [
        str(column).strip()
        for column in boundary_df.columns
    ]

    required_columns = {
        "Region",
        "Klasse",
        "Nedre",
        "Ovre",
        "Farge"
    }
    missing_columns = required_columns - set(boundary_df.columns)
    if missing_columns:
        raise ValueError(
            "Følgende kolonner mangler i "
            "Chla-grenseverdifilen: "
            + ", ".join(sorted(missing_columns))
        )

    for column in ["Region", "Klasse", "Farge"]:
        boundary_df[column] = (
            boundary_df[column]
            .astype("string")
            .str.strip()
        )

    for column in ["Nedre", "Ovre"]:
        boundary_df[column] = pd.to_numeric(
            boundary_df[column]
            .astype("string")
            .str.replace(",", ".", regex=False),
            errors="coerce"
        )

    boundary_df = boundary_df.dropna(
        subset=["Region", "Klasse", "Nedre", "Ovre"]
    ).copy()
    return boundary_df[boundary_df["Nedre"] < boundary_df["Ovre"]].copy()


@st.cache_data(show_spinner=False)
def load_water_type_map(workbook_contents: bytes) -> dict[str, str]:
    water_types = pd.read_excel(
        BytesIO(workbook_contents),
        sheet_name=BOUNDARY_SHEET,
        engine="openpyxl"
    )
    water_types.columns = [
        str(column).strip()
        for column in water_types.columns
    ]

    required_columns = {"Station", "Vanntype"}
    missing_columns = required_columns - set(water_types.columns)
    if missing_columns:
        raise ValueError(
            "Følgende kolonner mangler i "
            "Water_types.xlsx: "
            + ", ".join(sorted(missing_columns))
        )

    for column in ["Station", "Vanntype"]:
        water_types[column] = (
            water_types[column]
            .astype("string")
            .str.strip()
        )

    return (
        water_types
        .dropna(subset=["Station", "Vanntype"])
        .drop_duplicates(subset=["Station"])
        .set_index("Station")["Vanntype"]
        .to_dict()
    )


try:

    boundary_values = load_boundary_values(
        BOUNDARY_FILE.read_bytes(),
        BOUNDARY_SHEET
    )

    boundary_file_loaded = True

except Exception as error:

    boundary_values = pd.DataFrame(
        columns=[
            "Parameter",
            "Sesong",
            "Klasse",
            "Nedre",
            "Ovre",
            "Farge"
        ]
    )

    boundary_file_loaded = False

    st.warning(
        "Grenseverdiene kunne ikke leses. "
        "Plottene vises uten bakgrunnsfarger. "
        f"Detaljer: {error}"
    )


# --------------------------------------------------
# Select one parameter
# --------------------------------------------------
season_parameter_options = [
    parameter
    for parameter in ("P-TOT", "P-PO4", "N-TOT", "N-SNOX", "N-NH4")
    if parameter in y_candidates
]

season_parameter = st.selectbox(
    "Parameter for sesongplot",
    options=season_parameter_options,
    key="season_parameter"
)


# --------------------------------------------------
# Store seasonal results
# --------------------------------------------------
winter_results = {}
summer_results = {}

all_seasonal_values = []


# --------------------------------------------------
# Calculate seasonal averages
# --------------------------------------------------
for sheet in selected_sheets:

    df_season = all_sheets[sheet].copy()

    if (
        time_col not in df_season.columns
        or season_parameter not in df_season.columns
    ):
        continue

    # Convert date column
    df_season[time_col] = to_datetime(
        df_season[time_col]
    )

    df_season = df_season[
        df_season[time_col].notna()
    ].copy()

    if df_season.empty:
        continue

    # Create year and month columns
    df_season["year"] = (
        df_season[time_col].dt.year
    )

    df_season["month"] = (
        df_season[time_col].dt.month
    )

    # Convert selected parameter to numeric
    df_season[season_parameter] = to_numeric(
        df_season[season_parameter]
    )

    # ==================================
    # WINTER
    #
    # Winter 2025:
    # December 2024
    # January 2025
    # February 2025
    # ==================================
    winter_df = df_season[
        df_season["month"].isin([12, 1, 2])
    ].copy()

    if not winter_df.empty:

        winter_df["season_year"] = np.where(
            winter_df["month"] == 12,
            winter_df["year"] + 1,
            winter_df["year"]
        )

        winter_mean = (
            winter_df
            .dropna(subset=[season_parameter])
            .groupby(
                "season_year",
                as_index=False
            )[season_parameter]
            .mean()
            .sort_values("season_year")
        )

        if not winter_mean.empty:

            winter_results[sheet] = winter_mean

            all_seasonal_values.extend(
                winter_mean[
                    season_parameter
                ].tolist()
            )

    # ==================================
    # SUMMER
    #
    # June, July and August
    # in the same calendar year
    # ==================================
    summer_df = df_season[
        df_season["month"].isin([6, 7, 8])
    ].copy()

    if not summer_df.empty:

        summer_df["season_year"] = (
            summer_df["year"]
        )

        summer_mean = (
            summer_df
            .dropna(subset=[season_parameter])
            .groupby(
                "season_year",
                as_index=False
            )[season_parameter]
            .mean()
            .sort_values("season_year")
        )

        if not summer_mean.empty:

            summer_results[sheet] = summer_mean

            all_seasonal_values.extend(
                summer_mean[
                    season_parameter
                ].tolist()
            )


# --------------------------------------------------
# Calculate shared Y maximum from data only
# --------------------------------------------------
valid_seasonal_values = pd.to_numeric(
    pd.Series(
        all_seasonal_values,
        dtype="float64"
    ),
    errors="coerce"
).dropna()

if not valid_seasonal_values.empty:

    data_max = float(
        valid_seasonal_values.max()
    )

    if data_max > 0:

        # Add 10 percent headroom
        common_ymax = data_max * 1.10

    else:

        common_ymax = 1.0

else:

    data_max = 0.0
    common_ymax = 1.0


# --------------------------------------------------
# Boundary shading function
# --------------------------------------------------
def draw_visible_boundary_bands(
    ax,
    matching_limits: pd.DataFrame,
    visible_ymax: float
) -> bool:

    if matching_limits.empty:
        return False

    matching_limits = matching_limits.sort_values("Nedre")
    shading_added = False

    for _, boundary in matching_limits.iterrows():
        lower_boundary = float(boundary["Nedre"])
        upper_boundary = float(boundary["Ovre"])

        if lower_boundary >= visible_ymax:
            continue

        visible_lower = max(lower_boundary, 0.0)
        visible_upper = min(upper_boundary, visible_ymax)
        if visible_lower >= visible_upper:
            continue

        colour = boundary["Farge"]
        if pd.isna(colour) or not str(colour).strip():
            colour = "lightgrey"

        ax.axhspan(
            visible_lower,
            visible_upper,
            facecolor=str(colour),
            alpha=0.25,
            edgecolor="none",
            label=str(boundary["Klasse"]),
            zorder=0
        )
        shading_added = True

    return shading_added


def add_visible_boundary_shading(
    ax,
    limits_df: pd.DataFrame,
    parameter: str,
    season: str,
    visible_ymax: float
) -> bool:

    if limits_df.empty:
        return False

    parameter_key = str(parameter).strip().casefold()
    season_key = str(season).strip().casefold()

    matching_limits = limits_df[
        limits_df["Parameter"]
        .str.casefold()
        .eq(parameter_key)
        &
        limits_df["Sesong"]
        .str.casefold()
        .eq(season_key)
    ].copy()

    return draw_visible_boundary_bands(
        ax,
        matching_limits,
        visible_ymax
    )


def add_visible_region_shading(
    ax,
    limits_df: pd.DataFrame,
    region: str,
    visible_ymax: float
) -> bool:

    if limits_df.empty:
        return False

    region_key = str(region).strip().casefold()
    matching_limits = limits_df[
        limits_df["Region"].str.casefold().eq(region_key)
    ].copy()

    return draw_visible_boundary_bands(
        ax,
        matching_limits,
        visible_ymax
    )


# --------------------------------------------------
# Create figures
# --------------------------------------------------
fig_winter, ax_winter = plt.subplots(
    figsize=(5.5, 4.5)
)

fig_summer, ax_summer = plt.subplots(
    figsize=(5.5, 4.5)
)


# --------------------------------------------------
# Add visible boundary shading
# --------------------------------------------------
winter_has_limits = add_visible_boundary_shading(
    ax=ax_winter,
    limits_df=boundary_values,
    parameter=season_parameter,
    season="Vinter",
    visible_ymax=common_ymax
)

summer_has_limits = add_visible_boundary_shading(
    ax=ax_summer,
    limits_df=boundary_values,
    parameter=season_parameter,
    season="Sommer",
    visible_ymax=common_ymax
)


# --------------------------------------------------
# Use same station colour in both plots
# --------------------------------------------------
station_colors = {
    sheet: plt.cm.tab10(index % 10)
    for index, sheet
    in enumerate(selected_sheets)
}


# --------------------------------------------------
# Plot winter averages
# --------------------------------------------------
for sheet, winter_mean in winter_results.items():

    ax_winter.plot(
        winter_mean["season_year"],
        winter_mean[season_parameter],
        marker="o",
        linewidth=2,
        markersize=5,
        color=station_colors[sheet],
        label=sheet,
        zorder=5
    )


# --------------------------------------------------
# Plot summer averages
# --------------------------------------------------
for sheet, summer_mean in summer_results.items():

    ax_summer.plot(
        summer_mean["season_year"],
        summer_mean[season_parameter],
        marker="o",
        linewidth=2,
        markersize=5,
        color=station_colors[sheet],
        label=sheet,
        zorder=5
    )


# --------------------------------------------------
# Format axes
# --------------------------------------------------
ax_winter.set_title("Vinter")
ax_summer.set_title("Sommer")

for ax in [ax_winter, ax_summer]:

    ax.set_xlabel("År")
    ax.set_ylabel(season_parameter)

    ax.xaxis.set_major_locator(
        plt.MaxNLocator(integer=True)
    )

    ax.grid(
        True,
        alpha=0.3,
        zorder=1
    )

    # Same Y-axis on both plots.
    # Maximum comes from data, not boundary values.
    ax.set_ylim(
        0,
        common_ymax
    )


# --------------------------------------------------
# Add unique legends
# --------------------------------------------------
def add_unique_legend(ax):

    handles, labels = (
        ax.get_legend_handles_labels()
    )

    unique_items = {}

    for handle, label in zip(
        handles,
        labels
    ):

        if label not in unique_items:
            unique_items[label] = handle

    if unique_items:

        ax.legend(
            unique_items.values(),
            unique_items.keys(),
            fontsize=7,
            frameon=False,
            loc="best"
        )


add_unique_legend(ax_winter)
add_unique_legend(ax_summer)


# --------------------------------------------------
# Add message if seasonal data are absent
# --------------------------------------------------
if not winter_results:

    ax_winter.text(
        0.5,
        0.5,
        "Ingen vinterdata",
        transform=ax_winter.transAxes,
        horizontalalignment="center",
        verticalalignment="center"
    )

if not summer_results:

    ax_summer.text(
        0.5,
        0.5,
        "Ingen sommerdata",
        transform=ax_summer.transAxes,
        horizontalalignment="center",
        verticalalignment="center"
    )


fig_winter.tight_layout()
fig_summer.tight_layout()


# --------------------------------------------------
# Display side by side
# --------------------------------------------------
col_winter, col_summer = st.columns(
    [1, 1],
    gap="medium"
)

with col_winter:

    st.markdown(
        '<div id="winter-average-plot"></div>',
        unsafe_allow_html=True
    )
    st.pyplot(
        fig_winter,
        width="stretch"
    )

    if (
        boundary_file_loaded
        and not winter_has_limits
    ):
        st.caption(
            f"Ingen vintergrenser funnet for "
            f"`{season_parameter}`."
        )


with col_summer:

    st.markdown(
        '<div id="summer-average-plot"></div>',
        unsafe_allow_html=True
    )
    st.pyplot(
        fig_summer,
        width="stretch"
    )

    if (
        boundary_file_loaded
        and not summer_has_limits
    ):
        st.caption(
            f"Ingen sommergrenser funnet for "
            f"`{season_parameter}`."
        )


plt.close(fig_winter)
plt.close(fig_summer)


# =========================
# Siktedyp
# =========================
st.markdown('<div id="siktedyp-plot"></div>', unsafe_allow_html=True)
st.header("Siktedyp")

try:
    siktedyp_data = next(iter(load_excel_all_sheets(SIKTEDYP_FILE).values())).copy()
except Exception as error:
    st.error(f"Kunne ikke lese Siktedyp.xlsx: {error}")
else:
    required_columns = {"Betegnelse", "Verdi", "Tid_provetak"}
    missing_columns = required_columns - set(siktedyp_data.columns)

    if missing_columns:
        st.error(
            "Siktedyp.xlsx mangler kolonner: "
            + ", ".join(sorted(missing_columns))
        )
    else:
        siktedyp_data["Betegnelse"] = (
            siktedyp_data["Betegnelse"]
            .astype("string")
            .str.strip()
        )
        betegnelse_options = sorted(
            siktedyp_data["Betegnelse"].dropna().unique().tolist()
        )
        selected_betegnelser = st.multiselect(
            "Velg en eller flere betegnelser. Klassifisering gjeder kun for gjennomsnittet av sommermånedene (juni-august).",
            options=betegnelse_options,
            default=betegnelse_options[:1],
            key="siktedyp_betegnelser"
        )

        if not selected_betegnelser:
            st.warning("Velg minst én betegnelse for å vise siktedyp.")
        else:
            siktedyp_data["plot_date"] = to_datetime(
                siktedyp_data["Tid_provetak"]
            )
            siktedyp_data["plot_value"] = to_numeric(
                siktedyp_data["Verdi"]
            )
            selected_values = siktedyp_data.loc[
                siktedyp_data["Betegnelse"].isin(selected_betegnelser),
                "plot_value"
            ].dropna()
            visible_ymax = (
                float(selected_values.max()) * 1.1
                if not selected_values.empty and selected_values.max() > 0
                else 1.0
            )
            fig_siktedyp, ax_siktedyp = plt.subplots(figsize=(11, 5.5))
            ax_siktedyp.set_ylim(0, visible_ymax)

            if boundary_file_loaded:
                add_visible_boundary_shading(
                    ax=ax_siktedyp,
                    limits_df=boundary_values,
                    parameter="SECCI",
                    season="Sommer",
                    visible_ymax=visible_ymax
                )

            plotted_count = 0

            for betegnelse in selected_betegnelser:
                series_data = siktedyp_data[
                    siktedyp_data["Betegnelse"] == betegnelse
                ].dropna(subset=["plot_date", "plot_value"])
                series_data = series_data.sort_values("plot_date")

                if series_data.empty:
                    continue

                ax_siktedyp.plot(
                    series_data["plot_date"],
                    series_data["plot_value"],
                    label=betegnelse
                )
                plotted_count += 1

            if plotted_count:
                ax_siktedyp.set_xlabel("År")
                ax_siktedyp.set_ylabel("Siktedyp (m)")
                ax_siktedyp.grid(True, alpha=0.3)
                add_unique_legend(ax_siktedyp)
                fig_siktedyp.autofmt_xdate()
                st.pyplot(fig_siktedyp, width="stretch")
            else:
                st.warning("Ingen gyldige verdier å plotte for valgte betegnelser.")

            plt.close(fig_siktedyp)


# =========================
# Annual KLFA 90th percentile
# =========================
st.markdown('<div id="klfa-annual-plot"></div>', unsafe_allow_html=True)
st.header("KLFA årsverdier")
st.caption(
    "Årlig gjennomsnitt av 90-persentilene ved 0, 5 og 10 m, "
    "beregnet for februar–oktober."
)
st.caption(
    "Hvert panel bruker stasjonens vanntype for klassifiseringsgrensene."
)

klfa_boundary_values = pd.DataFrame(
    columns=["Region", "Klasse", "Nedre", "Ovre", "Farge"]
)
water_type_by_station = {}
try:
    klfa_boundary_values = load_chla_boundaries(
        CHLA_BOUNDARY_FILE.read_bytes()
    )
    water_type_by_station = load_water_type_map(
        WATER_TYPES_FILE.read_bytes()
    )
except Exception as error:
    st.warning(
        "Klassifiseringsgrensene for KLFA kunne ikke leses. "
        f"Plottene vises uten klassifiseringsfarger. Detaljer: {error}"
    )

target_depths = ("0m", "5m", "10m")
station_depth_sheets = {}

for sheet_name in all_sheets:
    if "_" not in sheet_name:
        continue
    station_name, depth = sheet_name.rsplit("_", 1)
    if depth in target_depths:
        station_depth_sheets.setdefault(station_name, {})[depth] = sheet_name

selected_station_names = sorted({
    sheet_name.rsplit("_", 1)[0]
    for sheet_name in selected_sheets
    if "_" in sheet_name
})
available_klfa_stations = [
    station_name
    for station_name in selected_station_names
    if any(
        depth in station_depth_sheets.get(station_name, {})
        for depth in target_depths
    )
]

if not available_klfa_stations:
    st.warning("Ingen valgte stasjoner har data ved 0, 5 og 10 m.")
else:
    annual_values_by_station = {}
    partial_depth_years = []

    for station_name in available_klfa_stations:
        depth_percentiles = {}

        for depth in target_depths:
            sheet_name = station_depth_sheets.get(station_name, {}).get(depth)
            if sheet_name is None:
                depth_percentiles[depth] = pd.Series(dtype="float64")
                continue

            depth_data = all_sheets[sheet_name]
            if not {"Tid_provetak", "KLFA"}.issubset(depth_data.columns):
                depth_percentiles[depth] = pd.Series(dtype="float64")
                continue

            sample_dates = to_datetime(depth_data["Tid_provetak"])
            in_season = sample_dates.dt.month.between(2, 10)
            values = to_numeric(depth_data["KLFA"])
            annual_data = pd.DataFrame({
                "year": sample_dates.loc[in_season].dt.year,
                "value": values.loc[in_season]
            }).dropna(subset=["year", "value"])

            depth_percentiles[depth] = annual_data.groupby("year")[
                "value"
            ].quantile(0.9)

        annual_values = pd.concat(depth_percentiles, axis=1).reindex(
            columns=list(target_depths)
        )
        depth_counts = annual_values.notna().sum(axis=1)
        for year, depth_count in depth_counts[depth_counts < len(target_depths)].items():
            if depth_count:
                partial_depth_years.append(
                    f"{station_name} {year} ({depth_count}/3 dybder)"
                )

        annual_mean = (
            annual_values.mean(axis=1)
            .where(depth_counts > 0)
            .dropna()
            .sort_index()
        )
        if annual_mean.empty:
            continue

        annual_values_by_station[station_name] = annual_mean

    if partial_depth_years:
        examples = ", ".join(partial_depth_years[:8])
        if len(partial_depth_years) > 8:
            examples += ", …"
        st.warning(
            "Ikke alle tre dybdene er representert for alle stasjonsår. "
            "Gjennomsnittet bruker tilgjengelige dybder; år uten gyldige "
            f"dybder hoppes over. Eksempler: {examples}."
        )

    if annual_values_by_station:
        stations_without_type = [
            station_name
            for station_name in annual_values_by_station
            if station_name not in water_type_by_station
        ]
        if stations_without_type:
            st.warning(
                "Vanntype mangler for: "
                + ", ".join(stations_without_type)
                + ". Disse vises uten klassifiseringsfarger."
            )

        annual_values_by_water_type = {}
        for station_name, annual_mean in annual_values_by_station.items():
            water_type = water_type_by_station.get(station_name)
            annual_values_by_water_type.setdefault(water_type, {})[
                station_name
            ] = annual_mean

        water_type_groups = sorted(
            annual_values_by_water_type.items(),
            key=lambda group: group[0] or ""
        )
        panel_columns = min(3, len(water_type_groups))
        panel_rows = int(np.ceil(len(water_type_groups) / panel_columns))
        fig_klfa, axes_klfa = plt.subplots(
            panel_rows,
            panel_columns,
            figsize=(5.5 * panel_columns, 3.8 * panel_rows),
            sharex=True,
            squeeze=False
        )
        class_legend = {}
        station_names = sorted(annual_values_by_station)
        station_colors = {
            station_name: plt.cm.tab20(index % 20)
            for index, station_name in enumerate(station_names)
        }

        for panel_index, (water_type, station_series) in enumerate(
            water_type_groups
        ):
            ax_klfa = axes_klfa.flat[panel_index]
            group_max = max(
                float(annual_mean.max())
                for annual_mean in station_series.values()
            )
            visible_ymax = max(group_max * 1.1, 1.0)
            ax_klfa.set_ylim(0, visible_ymax)

            if water_type:
                add_visible_region_shading(
                    ax=ax_klfa,
                    limits_df=klfa_boundary_values,
                    region=water_type,
                    visible_ymax=visible_ymax
                )
                region_boundaries = klfa_boundary_values[
                    klfa_boundary_values["Region"]
                    .str.casefold()
                    .eq(water_type.casefold())
                ]
                for _, boundary in region_boundaries.iterrows():
                    class_name = str(boundary["Klasse"])
                    if class_name not in class_legend:
                        class_legend[class_name] = Patch(
                            facecolor=str(boundary["Farge"]),
                            alpha=0.25,
                            edgecolor="none",
                            label=class_name
                        )

            station_handles = []
            station_labels = []
            for station_name, annual_mean in station_series.items():
                plot_dates = pd.to_datetime(
                    annual_mean.index.astype(str),
                    format="%Y"
                )
                station_line, = ax_klfa.plot(
                    plot_dates,
                    annual_mean,
                    marker="o",
                    linewidth=1.5,
                    markersize=4,
                    color=station_colors[station_name],
                    label=station_name
                )
                station_handles.append(station_line)
                station_labels.append(station_name)

            ax_klfa.set_title(
                f"Vanntype {water_type}"
                if water_type
                else "Vanntype mangler"
            )
            ax_klfa.set_xlabel("År")
            ax_klfa.set_ylabel("KLFA")
            ax_klfa.grid(True, alpha=0.3)
            ax_klfa.legend(
                handles=station_handles,
                labels=station_labels,
                frameon=False
            )

        for unused_axis in axes_klfa.flat[len(water_type_groups):]:
            unused_axis.set_visible(False)

        if class_legend:
            fig_klfa.legend(
                handles=list(class_legend.values()),
                loc="upper center",
                ncol=min(5, len(class_legend)),
                frameon=False
            )
            fig_klfa.tight_layout(rect=(0, 0, 1, 0.92))
        else:
            fig_klfa.tight_layout()

        fig_klfa.autofmt_xdate()
        st.pyplot(fig_klfa, width="stretch")
        plt.close(fig_klfa)
    else:
        st.warning("Ingen komplette KLFA-årsverdier for valgte stasjoner.")