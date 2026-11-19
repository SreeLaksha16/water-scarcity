"""
WaterScarcity Compass - Regional Water Status page.

Groundwater:
- Reads the existing cleaned_groundwater.csv (read-only).
- Stores user-entered observations in a separate user_observations.db.
- Uses the newest observation no more than 30 days old for the current-status display.
- Clearly labels user-entered readings as user-supplied and unverified.

Weather:
- Retrieves a 7-day rainfall forecast from Open-Meteo when internet is available.

Important:
This page is a preliminary water-stress screening tool, not a drinking-water
quality test, a guarantee of household supply, or a validated scarcity forecast.
"""
from pathlib import Path
import sqlite3
from datetime import date, datetime, timedelta

import pandas as pd
import requests
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
GROUNDWATER_FILE = BASE_DIR / "cleaned_groundwater.csv"
OBSERVATIONS_DB = BASE_DIR / "user_observations.db"

GW_LEVEL = "Groundwater Level Quarterly Manual (meter)"
DATE_COL = "Data Acquisition Time"
MAX_AGE_DAYS = 30


# ---------------------------------------------------------------------
# User-observation database (separate from the existing data warehouse)
# ---------------------------------------------------------------------
def init_observations_db():
    with sqlite3.connect(OBSERVATIONS_DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_groundwater_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                state TEXT NOT NULL,
                district TEXT NOT NULL,
                station TEXT,
                observation_date TEXT NOT NULL,
                groundwater_depth_m REAL NOT NULL,
                entered_by TEXT,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def save_user_observation(
    state: str,
    district: str,
    station: str,
    observation_date: date,
    groundwater_depth_m: float,
    entered_by: str,
    notes: str,
):
    init_observations_db()
    with sqlite3.connect(OBSERVATIONS_DB) as conn:
        conn.execute(
            """
            INSERT INTO user_groundwater_observations
            (state, district, station, observation_date,
             groundwater_depth_m, entered_by, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                state.strip(),
                district.strip(),
                station.strip(),
                observation_date.isoformat(),
                float(groundwater_depth_m),
                entered_by.strip(),
                notes.strip(),
            ),
        )
        conn.commit()


@st.cache_data(show_spinner=False, ttl=60)
def load_user_observations():
    init_observations_db()
    with sqlite3.connect(OBSERVATIONS_DB) as conn:
        return pd.read_sql_query(
            """
            SELECT id, state, district, station, observation_date,
                   groundwater_depth_m, entered_by, notes, created_at
            FROM user_groundwater_observations
            """,
            conn,
        )


# ---------------------------------------------------------------------
# Historical cleaned dataset
# ---------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_groundwater():
    if not GROUNDWATER_FILE.exists():
        raise FileNotFoundError(
            "cleaned_groundwater.csv was not found in the project folder."
        )

    df = pd.read_csv(GROUNDWATER_FILE, low_memory=False)
    df.columns = df.columns.str.strip()

    required = {"State", "District", GW_LEVEL, DATE_COL}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            "The cleaned groundwater CSV is missing these columns: "
            + ", ".join(sorted(missing))
        )

    df[GW_LEVEL] = pd.to_numeric(df[GW_LEVEL], errors="coerce")
    df["_date"] = pd.to_datetime(
        df[DATE_COL], dayfirst=True, errors="coerce"
    )
    df = df.dropna(subset=["State", "District", GW_LEVEL, "_date"]).copy()
    df["State"] = df["State"].astype(str).str.strip()
    df["District"] = df["District"].astype(str).str.strip()
    return df


def get_combined_observations(state: str, district: str) -> pd.DataFrame:
    """Combine selected-district CSV rows with user-entered rows."""
    historical = load_groundwater()
    historical = historical[
        (historical["State"].str.casefold() == state.casefold())
        & (historical["District"].str.casefold() == district.casefold())
    ].copy()

    historical_rows = pd.DataFrame({
        "Observation date": historical["_date"].dt.date,
        "Groundwater depth (m below ground)": historical[GW_LEVEL],
        "Record type": "Existing cleaned CSV",
        "Station": (
            historical["Station"].fillna("").astype(str)
            if "Station" in historical.columns
            else ""
        ),
        "Entered by": "",
        "Notes": "",
    })

    user = load_user_observations()
    if not user.empty:
        user = user[
            (user["state"].str.casefold() == state.casefold())
            & (user["district"].str.casefold() == district.casefold())
        ].copy()
    if user.empty:
        user_rows = pd.DataFrame(columns=historical_rows.columns)
    else:
        user_rows = pd.DataFrame({
            "Observation date": pd.to_datetime(
                user["observation_date"], errors="coerce"
            ).dt.date,
            "Groundwater depth (m below ground)": pd.to_numeric(
                user["groundwater_depth_m"], errors="coerce"
            ),
            "Record type": "User-supplied (unverified)",
            "Station": user["station"].fillna("").astype(str),
            "Entered by": user["entered_by"].fillna("").astype(str),
            "Notes": user["notes"].fillna("").astype(str),
        })

    combined = pd.concat(
        [historical_rows, user_rows], ignore_index=True
    )
    combined = combined.dropna(
        subset=["Observation date", "Groundwater depth (m below ground)"]
    )
    if not combined.empty:
        combined = combined.sort_values(
            "Observation date", ascending=False
        ).reset_index(drop=True)
    return combined


# ---------------------------------------------------------------------
# Weather forecast
# ---------------------------------------------------------------------
@st.cache_data(ttl=1800, show_spinner=False)
def get_weather_forecast(latitude: float, longitude: float):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "precipitation_sum,precipitation_probability_max",
        "forecast_days": 7,
        "timezone": "Asia/Kolkata",
    }
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    daily = response.json().get("daily", {})
    if not daily.get("time"):
        raise ValueError("The weather service returned no daily forecast.")

    return pd.DataFrame({
        "Date": daily.get("time", []),
        "Forecast rainfall (mm)": daily.get("precipitation_sum", []),
        "Rain probability (%)": daily.get(
            "precipitation_probability_max", []
        ),
    })


def get_district_coordinates(state: str, district: str):
    """Use station coordinates from the existing CSV if available."""
    df = load_groundwater()
    selected = df[
        (df["State"].str.casefold() == state.casefold())
        & (df["District"].str.casefold() == district.casefold())
    ]
    if {"Latitude", "Longitude"}.issubset(selected.columns):
        coords = selected.copy()
        coords["Latitude"] = pd.to_numeric(
            coords["Latitude"], errors="coerce"
        )
        coords["Longitude"] = pd.to_numeric(
            coords["Longitude"], errors="coerce"
        )
        coords = coords.dropna(subset=["Latitude", "Longitude"])
        if not coords.empty:
            return (
                float(coords["Latitude"].median()),
                float(coords["Longitude"].median()),
            )
    return None, None


# ---------------------------------------------------------------------
# Current-status selection and transparent screening indicator
# ---------------------------------------------------------------------
def select_recent_observation(combined: pd.DataFrame):
    if combined.empty:
        return None, None

    today = date.today()
    fresh = combined[
        combined["Observation date"].apply(
            lambda d: 0 <= (today - d).days <= MAX_AGE_DAYS
        )
    ].copy()

    if fresh.empty:
        return None, None

    fresh = fresh.sort_values("Observation date", ascending=False)
    latest_date = fresh.iloc[0]["Observation date"]
    latest_on_date = fresh[fresh["Observation date"] == latest_date]

    # If multiple readings share the latest date, use their average for
    # district-level display; retain individual rows in the observation table.
    latest_value = float(
        latest_on_date["Groundwater depth (m below ground)"].mean()
    )
    record_types = sorted(latest_on_date["Record type"].unique())
    return {
        "date": latest_date,
        "depth": latest_value,
        "record_types": record_types,
        "age_days": (today - latest_date).days,
        "number_of_readings": len(latest_on_date),
    }, fresh


def calculate_trend(combined: pd.DataFrame):
    """Compare mean of newest three dates with previous three dates."""
    if combined.empty:
        return None

    daily = (
        combined.groupby("Observation date")[
            "Groundwater depth (m below ground)"
        ]
        .mean()
        .sort_index()
    )
    if len(daily) < 2:
        return None

    recent = daily.iloc[-3:]
    previous = daily.iloc[-6:-3]
    if previous.empty:
        return None
    return float(recent.mean() - previous.mean())


def assess_status(latest, trend, rainfall_7d):
    """
    Preliminary signal only. No universal groundwater-depth threshold is
    applied because safe/sustainable levels differ by aquifer and location.
    """
    if latest is None:
        return (
            "Insufficient recent groundwater data",
            "No groundwater observation for this district is dated within "
            "the last 30 days. Enter a new measured reading or connect an "
            "official recent monitoring source.",
            None,
        )

    score = 0
    reasons = []

    if trend is None:
        reasons.append(
            "Not enough dated readings to calculate a groundwater trend."
        )
    elif trend >= 1.0:
        score += 40
        reasons.append(
            "Groundwater depth has increased substantially; a deeper water "
            "table can indicate worsening conditions."
        )
    elif trend >= 0.25:
        score += 25
        reasons.append(
            "Groundwater depth has increased; monitor for a declining trend."
        )
    elif trend > -0.25:
        score += 12
        reasons.append("Groundwater depth is broadly stable.")
    else:
        reasons.append(
            "Groundwater depth has decreased, indicating an improving "
            "recent trend at the measured locations."
        )

    if rainfall_7d is None:
        reasons.append("Rainfall forecast is unavailable.")
    elif rainfall_7d < 5:
        score += 30
        reasons.append("Forecast rainfall over the next 7 days is very low.")
    elif rainfall_7d < 20:
        score += 20
        reasons.append("Forecast rainfall over the next 7 days is limited.")
    elif rainfall_7d < 50:
        score += 10
        reasons.append("Forecast rainfall is moderate.")
    else:
        reasons.append(
            "Forecast rainfall is relatively high; this does not guarantee "
            "groundwater recharge."
        )

    if score >= 55:
        label = "High stress signal"
    elif score >= 30:
        label = "Moderate stress signal"
    else:
        label = "Lower stress signal"

    return label, " ".join(reasons), score


# ---------------------------------------------------------------------
# Streamlit page
# ---------------------------------------------------------------------
def render_live_water_status():
    st.title("Regional Water Status")
    st.caption(
        "Select a district, add a recent measured groundwater reading, "
        "and review the latest available regional status."
    )

    st.info(
        "Only groundwater readings dated within the last 30 days are used "
        "for the current groundwater status. Older CSV records remain visible "
        "as historical context but are not presented as current. User-entered "
        "readings are labelled unverified."
    )

    try:
        groundwater = load_groundwater()
    except Exception as exc:
        st.error(f"Could not load groundwater data: {exc}")
        st.stop()

    states = sorted(groundwater["State"].dropna().unique().tolist())
    if not states:
        st.warning("No states were found in the groundwater dataset.")
        st.stop()

    state = st.selectbox(
        "Select state", states, key="regional_water_state"
    )
    state_data = groundwater[
        groundwater["State"].str.casefold() == state.casefold()
    ]
    districts = sorted(state_data["District"].dropna().unique().tolist())
    if not districts:
        st.warning("No districts were found for this state.")
        st.stop()

    district = st.selectbox(
        "Select district", districts, key="regional_water_district"
    )

    # Input form: date defaults to today; future dates are rejected.
    st.subheader("Add a new groundwater observation")
    st.write(
        "Enter a measured reading from a field instrument, borewell log, "
        "or official monitoring report. Do not guess a value."
    )

    with st.form("new_groundwater_observation", clear_on_submit=True):
        observation_date = st.date_input(
            "Observation date",
            value=date.today(),
            max_value=date.today(),
            help="Defaults to today's date. Future observation dates are not allowed.",
        )
        depth = st.number_input(
            "Groundwater depth (metres below ground level)",
            min_value=0.0,
            max_value=500.0,
            value=10.0,
            step=0.1,
            format="%.2f",
            help=(
                "Enter the measured depth below ground level (mbgl), "
                "not water-level elevation above mean sea level."
            ),
        )
        station = st.text_input(
            "Monitoring station / village / locality (optional)"
        )
        entered_by = st.text_input(
            "Observer name or organisation (optional)"
        )
        notes = st.text_area(
            "Notes / measurement source (optional)",
            placeholder="Example: measured using a water-level meter; station name..."
        )
        confirmed = st.checkbox(
            "I confirm this is an actual measured observation, not an estimate."
        )
        submitted = st.form_submit_button(
            "Save groundwater observation",
            use_container_width=True,
        )

    if submitted:
        if observation_date > date.today():
            st.error("Future observation dates cannot be saved.")
        elif not confirmed:
            st.error(
                "Please confirm that this is an actual measured observation."
            )
        else:
            try:
                save_user_observation(
                    state=state,
                    district=district,
                    station=station,
                    observation_date=observation_date,
                    groundwater_depth_m=depth,
                    entered_by=entered_by,
                    notes=notes,
                )
                load_user_observations.clear()
                st.success(
                    "Observation saved. The district status has been refreshed."
                )
                st.rerun()
            except Exception as exc:
                st.error(f"Could not save the observation: {exc}")

    # Combine original CSV and user entries, then choose the latest fresh reading.
    combined = get_combined_observations(state, district)
    latest, fresh_rows = select_recent_observation(combined)

    st.subheader(f"Groundwater status: {district}, {state}")

    if latest is None:
        st.warning(
            "No recent groundwater observation available for this district "
            "within the last 30 days."
        )
        if not combined.empty:
            most_recent = combined.iloc[0]
            st.caption(
                "Last historical reading: "
                f"{most_recent['Observation date'].strftime('%d %b %Y')} "
                f"({most_recent['Record type']}). This is not used as current status."
            )
    else:
        st.metric(
            "Latest groundwater depth",
            f"{latest['depth']:.2f} m below ground",
            help="Average of readings on the latest eligible observation date.",
        )
        st.metric(
            "Observation date",
            latest["date"].strftime("%d %b %Y"),
        )
        st.metric("Observation age", f"{latest['age_days']} day(s)")
        st.caption(
            "Latest reading source: " + ", ".join(latest["record_types"])
            + f". Number of readings on this date: {latest['number_of_readings']}."
        )
        if "User-supplied (unverified)" in latest["record_types"]:
            st.warning(
                "The latest reading includes user-supplied data. It has not "
                "been independently verified."
            )

    # Show historical and fresh readings together, clearly labelled.
    st.subheader("Groundwater observation history")
    if combined.empty:
        st.info("No groundwater observations are available for this district.")
    else:
        display = combined.copy()
        display["Observation date"] = display["Observation date"].astype(str)
        st.dataframe(display, use_container_width=True, hide_index=True)

    # Weather forecast uses approximate district coordinates from CSV stations.
    st.subheader("Live 7-day rainfall forecast")
    latitude, longitude = get_district_coordinates(state, district)
    rainfall_total = None

    if latitude is None or longitude is None:
        st.warning(
            "Station coordinates are unavailable, so a district rainfall "
            "forecast cannot be requested."
        )
    else:
        try:
            forecast = get_weather_forecast(latitude, longitude)
            rainfall_total = float(
                forecast["Forecast rainfall (mm)"].fillna(0).sum()
            )
            st.metric(
                "Forecast rainfall over next 7 days",
                f"{rainfall_total:.1f} mm",
            )
            st.dataframe(
                forecast, use_container_width=True, hide_index=True
            )
            st.caption(
                "Weather source: Open-Meteo forecast API. Forecast is cached "
                "for 30 minutes and is not a groundwater measurement."
            )
        except Exception as exc:
            st.warning(f"Could not retrieve the rainfall forecast: {exc}")

    # Calculate trend only from recent readings, not stale historical values.
    recent_trend = None
    if fresh_rows is not None and not fresh_rows.empty:
        recent_trend = calculate_trend(fresh_rows)

    st.subheader("Preliminary regional water-stress assessment")
    label, explanation, score = assess_status(
        latest, recent_trend, rainfall_total
    )

    if score is None:
        st.warning(label)
    else:
        st.metric("Screening category", label)
        st.progress(min(score / 70, 1.0))
        st.caption(f"Prototype indicator score: {score}/70")

    st.write(explanation)

    st.caption(
        "Important: this is a prototype screening indicator, not a validated "
        "scarcity prediction. A groundwater depth in metres below ground level "
        "cannot be classified as safe or unsafe using one universal threshold. "
        "Actual household water availability also depends on aquifer conditions, "
        "reservoir storage, supply infrastructure, demand and water quality. "
        "User-entered readings are not independently verified."
    )
