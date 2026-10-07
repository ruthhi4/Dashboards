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
FILE_PATH = Path("Oekokyst/merge-new2.xlsx")

NROWS = None  # Optional: limit rows per sheet (None = all)

st.set_page_config(page_title="Økokyst Nordsjøen og Skagerak", layout="wide")
st.title("Økokyst Nordsjøen og Skagerak")

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

def to_numeric_loq(series):

    def convert_value(value):

        if pd.isna(value):
            return np.nan

        value = str(value).strip()

        if value.startswith("<"):

            value = value.replace("<", "")
            value = value.replace(",", ".")

            try:
                return float(value) / 2
            except:
                return np.nan

        value = value.replace(",", ".")

        try:
            return float(value)
        except:
            return np.nan

    return series.apply(convert_value)

# ---- Row under the plot: image + table side-by-side ----
col_img, col_tbl = st.columns([2, 1], gap="medium")  # tweak ratios as you like

with col_img:
    st.subheader("Stasjonskart")
    # Load image from file (can also be a URL or bytes)
    img = Image.open("Oekokyst/Økokyst All.png")  # e.g., "data/photo.png"
    st.image(img, width='stretch')

    
with col_tbl:
    st.subheader("Vannmiljøkoder")
    df = pd.read_excel("Oekokyst/Stations Nordsjøen.xlsx", sheet_name='Koder')
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
st.header("Oversiktsplot")

fig, ax = plt.subplots(figsize=(11, 5.5))

series_plotted = 0
skipped_info = []

for sheet in selected_sheets:
    df = all_sheets[sheet].copy()
    if time_col not in df.columns:
        skipped_info.append(f"Sheet '{sheet}' missing time column '{time_col}'. Skipped.")
        continue

    # Prepare time & sort
    #df[time_col] = to_datetime(df[time_col])

    #test
    df[time_col] = pd.to_datetime(
        df[time_col]
            .astype(str)
            .str.strip(),
        errors="coerce", format="mixed"
    )

    df = df[df[time_col].notna()].copy()

    df = df.sort_values(time_col)
             


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

# =========================
# 📆 Plot for selected years
# =========================
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

            years_text = ", ".join(
                str(year) for year in sorted(selected_years)
            )

            #ax_year.set_title(
            #    f"Sammenligning av år: {years_text}"
            #)

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
BOUNDARY_FILE = Path(
    "Oekokyst/Boundary_values.xlsx"
)

BOUNDARY_SHEET = "Sheet1"


# --------------------------------------------------
# Load boundary values
# --------------------------------------------------
@st.cache_data(show_spinner=False)
def load_boundary_values(
    path: Path,
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

    if not path.exists():
        raise FileNotFoundError(
            f"Fant ikke grenseverdifilen: "
            f"{path.resolve()}"
        )

    boundary_df = pd.read_excel(
        path,
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


try:

    boundary_values = load_boundary_values(
        BOUNDARY_FILE,
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
season_parameter = st.selectbox(
    "Parameter for sesongplot",
    options=y_candidates,
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

    if matching_limits.empty:
        return False

    matching_limits = matching_limits.sort_values(
        "Nedre"
    )

    shading_added = False

    for _, boundary in matching_limits.iterrows():

        lower_boundary = float(
            boundary["Nedre"]
        )

        upper_boundary = float(
            boundary["Ovre"]
        )

        # Class starts above visible range
        if lower_boundary >= visible_ymax:
            continue

        visible_lower = max(
            lower_boundary,
            0.0
        )

        visible_upper = min(
            upper_boundary,
            visible_ymax
        )

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