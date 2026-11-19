
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# --------------------------------------------------
# 1. PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="WaterScarcity Compass",
    page_icon="💧",
    layout="wide"
)

folder = Path(__file__).parent

# --------------------------------------------------
# 2. CUSTOM DESIGN
# --------------------------------------------------

st.markdown("""
<style>
.stApp {
    background-color: #F3F7FC;
}
[data-testid="stSidebar"] {
    background-color: #102B46;
}
[data-testid="stSidebar"] * {
    color: white;
}
.main-title {
    background: linear-gradient(110deg, #075985, #0891B2, #2563EB);
    padding: 25px;
    border-radius: 15px;
    color: white;
    margin-bottom: 20px;
}
.main-title h1 {
    color: white;
}
.main-title p {
    color: #E0F2FE;
}
.metric-card {
    background: white;
    padding: 20px;
    border-radius: 12px;
    border-left: 5px solid #0891B2;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.section-title {
    color: #075985;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 3. LOAD DATASET
# --------------------------------------------------

@st.cache_data
def load_groundwater():
    path = folder / "cleaned_groundwater.csv"

    if not path.exists():
        return pd.DataFrame()

    data = pd.read_csv(path, low_memory=False)
    data.columns = data.columns.str.strip()
    return data


@st.cache_data
def load_reservoir():
    path = folder / "cleaned_reservoir.csv"

    if not path.exists():
        return pd.DataFrame()

    data = pd.read_csv(path, low_memory=False)
    data.columns = data.columns.str.strip()
    return data


df = load_groundwater()
reservoir_df = load_reservoir()

LEVEL = "Groundwater Level Quarterly Manual (meter)"
DATE = "Data Acquisition Time"

if df.empty:
    st.error(
        "Groundwater dataset not found or empty. "
        "Please check cleaned_groundwater.csv."
    )
    st.stop()

if LEVEL not in df.columns:
    st.error(f"Required column not found: {LEVEL}")
    st.write("Available columns:", df.columns.tolist())
    st.stop()

if "State" not in df.columns or "District" not in df.columns:
    st.error("State or District column is missing.")
    st.write("Available columns:", df.columns.tolist())
    st.stop()

df[LEVEL] = pd.to_numeric(df[LEVEL], errors="coerce")
df = df.dropna(subset=["State", "District", LEVEL]).copy()

# --------------------------------------------------
# 4. SIDEBAR NAVIGATION
# --------------------------------------------------

st.sidebar.markdown(
    "<h1 style='text-align:center;'>💧</h1>",
    unsafe_allow_html=True
)

st.sidebar.markdown(
    "<h2 style='text-align:center;'>WaterScarcity<br>Compass</h2>",
    unsafe_allow_html=True
)

st.sidebar.caption("Monitor • Analyse • Predict • Prevent")
st.sidebar.divider()

page = st.sidebar.radio(
    "NAVIGATION",
    [
        "Home Dashboard",
        "Groundwater Analysis",
        "OLAP Cube",
        "Dataset Explorer",
        "Reservoir Analysis",
        "About Project"
    ]
)

# --------------------------------------------------
# 5. COMMON HEADER
# --------------------------------------------------

st.markdown("""
<div class="main-title">
    <h1>💧 WaterScarcity Compass</h1>
    <p>Water Intelligence and Data Warehouse Dashboard</p>
    <p>Monitor • Analyse • Predict • Prevent</p>
</div>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 6. HOME DASHBOARD
# --------------------------------------------------

if page == "Home Dashboard":

    st.subheader("📊 Overall Water Resource Overview")

    total_records = len(df)
    total_states = df["State"].nunique()
    total_districts = df["District"].nunique()
    average_level = df[LEVEL].mean()

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Groundwater Records", f"{total_records:,}")
    c2.metric("Average Water Level", f"{average_level:.2f} m")
    c3.metric("States Covered", total_states)
    c4.metric("Districts Covered", total_districts)

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("State-wise Groundwater Level")

        state_summary = (
            df.groupby("State")[LEVEL]
            .mean()
            .reset_index()
            .sort_values(LEVEL, ascending=False)
        )

        fig = px.bar(
            state_summary,
            x="State",
            y=LEVEL,
            color=LEVEL,
            color_continuous_scale="Tealgrn",
            title="Average Groundwater Level by State"
        )

        fig.update_layout(
            template="plotly_white",
            xaxis_tickangle=-45
        )

        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Groundwater Level Distribution")

        fig = px.histogram(
            df,
            x=LEVEL,
            nbins=30,
            color_discrete_sequence=["#0891B2"],
            title="Distribution of Groundwater Measurements"
        )

        fig.update_layout(template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Recent Groundwater Records")
    st.dataframe(df.head(20), use_container_width=True)

# --------------------------------------------------
# 7. GROUNDWATER ANALYSIS
# --------------------------------------------------

elif page == "Groundwater Analysis":

    st.subheader("🌊 Groundwater Analytics")

    states = sorted(df["State"].dropna().astype(str).unique())

    selected_state = st.selectbox(
        "Select State",
        ["All States"] + states
    )

    filtered = df.copy()

    if selected_state != "All States":
        filtered = filtered[
            filtered["State"].astype(str) == selected_state
        ]

    districts = sorted(
        filtered["District"].dropna().astype(str).unique()
    )

    selected_district = st.selectbox(
        "Select District",
        ["All Districts"] + districts
    )

    if selected_district != "All Districts":
        filtered = filtered[
            filtered["District"].astype(str) == selected_district
        ]

    a, b, c = st.columns(3)

    a.metric("Average Level", f"{filtered[LEVEL].mean():.2f} m")
    b.metric("Total Records", f"{len(filtered):,}")
    c.metric("Districts", filtered["District"].nunique())

    st.divider()

    district_summary = (
        filtered.groupby("District")[LEVEL]
        .mean()
        .reset_index()
        .sort_values(LEVEL, ascending=False)
    )

    fig = px.bar(
        district_summary,
        x="District",
        y=LEVEL,
        color=LEVEL,
        color_continuous_scale="Blues",
        title="District-wise Average Groundwater Level"
    )

    fig.update_layout(
        template="plotly_white",
        xaxis_tickangle=-45
    )

    st.plotly_chart(fig, use_container_width=True)

    if DATE in filtered.columns:
        time_df = filtered.copy()
        time_df[DATE] = time_df[DATE].astype(str)

        time_summary = (
            time_df.groupby(DATE)[LEVEL]
            .mean()
            .reset_index()
        )

        fig = px.line(
            time_summary,
            x=DATE,
            y=LEVEL,
            markers=True,
            title="Groundwater Level Over Time"
        )

        fig.update_layout(template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Groundwater Data")
    st.dataframe(filtered, use_container_width=True)

# --------------------------------------------------
# 8. OLAP CUBE
# --------------------------------------------------

elif page == "OLAP Cube":

    st.subheader("🧊 Interactive OLAP Cube")
    st.write(
        "Analyse groundwater measurements using "
        "Slice, Dice, Roll-up, Drill-down and Pivot operations."
    )

    st.markdown("### OLAP Filters")

    c1, c2, c3 = st.columns(3)

    states = sorted(df["State"].dropna().astype(str).unique())

    with c1:
        state = st.selectbox(
            "Slice: Select State",
            ["All States"] + states
        )

    filtered = df.copy()

    if state != "All States":
        filtered = filtered[filtered["State"].astype(str) == state]

    districts = sorted(
        filtered["District"].dropna().astype(str).unique()
    )

    with c2:
        district = st.selectbox(
            "Dice: Select District",
            ["All Districts"] + districts
        )

    if district != "All Districts":
        filtered = filtered[
            filtered["District"].astype(str) == district
        ]

    with c3:
        if DATE in filtered.columns:
            periods = sorted(
                filtered[DATE].dropna().astype(str).unique()
            )
            period = st.selectbox(
                "Select Period",
                ["All Periods"] + periods
            )
        else:
            period = "All Periods"

    if period != "All Periods" and DATE in filtered.columns:
        filtered = filtered[
            filtered[DATE].astype(str) == period
        ]

    st.divider()

    st.subheader("OLAP Measures")

    m1, m2, m3, m4 = st.columns(4)

    m1.metric("Average Level", f"{filtered[LEVEL].mean():.2f} m")
    m2.metric("Minimum Level", f"{filtered[LEVEL].min():.2f} m")
    m3.metric("Maximum Level", f"{filtered[LEVEL].max():.2f} m")
    m4.metric("Record Count", f"{len(filtered):,}")

    st.divider()

    # --------------------------------------------------
    # OLAP OPERATIONS
    # --------------------------------------------------

    operation = st.selectbox(
        "Choose OLAP Operation",
        [
            "Slice",
            "Dice",
            "Roll-up",
            "Drill-down",
            "Pivot"
        ]
    )

    if operation == "Slice":
        st.info(
            "Slice selects one value from a dimension, "
            "such as one State."
        )
        st.write("Selected State:", state)

        result = filtered.groupby("State").agg(
            Average_Level=(LEVEL, "mean"),
            Record_Count=(LEVEL, "count")
        ).reset_index()

    elif operation == "Dice":
        st.info(
            "Dice selects a smaller sub-cube using "
            "multiple dimension filters."
        )

        result = filtered.groupby(
            ["State", "District"]
        ).agg(
            Average_Level=(LEVEL, "mean"),
            Record_Count=(LEVEL, "count")
        ).reset_index()

    elif operation == "Roll-up":
        st.info(
            "Roll-up aggregates detailed records into "
            "a higher geographical level."
        )

        result = (
            filtered.groupby("State")
            .agg(
                Average_Level=(LEVEL, "mean"),
                Minimum_Level=(LEVEL, "min"),
                Maximum_Level=(LEVEL, "max"),
                Record_Count=(LEVEL, "count")
            )
            .reset_index()
        )

    elif operation == "Drill-down":
        st.info(
            "Drill-down moves from a higher level "
            "to a more detailed geographical level."
        )

        available_dimensions = [
            col for col in ["State", "District", "Block", "Tehsil"]
            if col in filtered.columns
        ]

        drill_dimension = st.selectbox(
            "Select Drill-down Dimension",
            available_dimensions
        )

        result = (
            filtered.groupby(drill_dimension)
            .agg(
                Average_Level=(LEVEL, "mean"),
                Record_Count=(LEVEL, "count")
            )
            .reset_index()
        )

    else:
        st.info(
            "Pivot changes the arrangement of rows and columns "
            "for multidimensional analysis."
        )

        if DATE in filtered.columns:
            pivot_data = filtered.copy()
            pivot_data[DATE] = pivot_data[DATE].astype(str)

            result = pd.pivot_table(
                pivot_data,
                index="District",
                columns=DATE,
                values=LEVEL,
                aggfunc="mean"
            ).reset_index()
        else:
            result = filtered.pivot_table(
                index="State",
                columns="District",
                values=LEVEL,
                aggfunc="mean"
            ).reset_index()

    st.subheader(f"📊 {operation} Result")
    st.dataframe(result, use_container_width=True)

    # --------------------------------------------------
    # 3D OLAP VISUALIZATION
    # --------------------------------------------------

    st.divider()
    st.subheader("🌐 3D OLAP Visualization")

    if not filtered.empty:

        chart_data = filtered.copy()

        if DATE in chart_data.columns:
            chart_data["Period"] = chart_data[DATE].astype(str)
        else:
            chart_data["Period"] = "All Periods"

        cube_data = (
            chart_data.groupby(
                ["District", "Period"],
                as_index=False
            )
            .agg(
                Average_Level=(LEVEL, "mean"),
                Record_Count=(LEVEL, "count")
            )
        )

        fig = px.scatter_3d(
            cube_data,
            x="District",
            y="Period",
            z="Average_Level",
            color="Average_Level",
            size="Record_Count",
            hover_name="District",
            color_continuous_scale="Turbo",
            title="District and Period-wise Groundwater Cube"
        )

        fig.update_traces(marker=dict(symbol="square", opacity=0.9))

        fig.update_layout(
            height=650,
            template="plotly_white",
            scene=dict(
                xaxis_title="District Dimension",
                yaxis_title="Time Dimension",
                zaxis_title="Average Groundwater Level (m)"
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            key="olap_3d_cube"
        )

    else:
        st.warning("No data available for the selected filters.")

    st.download_button(
        "⬇ Download OLAP Results",
        data=result.to_csv(index=False).encode("utf-8"),
        file_name="olap_cube_results.csv",
        mime="text/csv"
    )

# --------------------------------------------------
# 9. DATASET EXPLORER
# --------------------------------------------------

elif page == "Dataset Explorer":

    st.subheader("📂 Groundwater Dataset Explorer")

    c1, c2, c3 = st.columns(3)

    c1.metric("Rows", f"{len(df):,}")
    c2.metric("Columns", len(df.columns))
    c3.metric("Missing Values", int(df.isna().sum().sum()))

    st.divider()

    st.subheader("Dataset Preview")

    st.dataframe(df, use_container_width=True)

    st.subheader("Column Information")

    column_info = pd.DataFrame({
        "Column Name": df.columns,
        "Data Type": df.dtypes.astype(str).values,
        "Missing Values": df.isna().sum().values,
        "Unique Values": df.nunique().values
    })

    st.dataframe(column_info, use_container_width=True)

    st.subheader("Statistical Summary")
    st.dataframe(
        df.describe(include="all").T,
        use_container_width=True
    )

    st.download_button(
        "⬇ Download Groundwater Dataset",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="groundwater_dataset.csv",
        mime="text/csv"
    )

# --------------------------------------------------
# 10. RESERVOIR ANALYSIS
# --------------------------------------------------

elif page == "Reservoir Analysis":

    st.subheader("🏞️ Reservoir Analytics")

    if reservoir_df.empty:
        st.warning(
            "Reservoir dataset is not available. "
            "Check cleaned_reservoir.csv in the project folder."
        )
    else:
        st.metric("Reservoir Dataset Records", f"{len(reservoir_df):,}")

        st.subheader("Reservoir Dataset Preview")
        st.dataframe(reservoir_df, use_container_width=True)

        numeric_columns = reservoir_df.select_dtypes(
            include="number"
        ).columns.tolist()

        if numeric_columns:
            selected_column = st.selectbox(
                "Select Numeric Measure",
                numeric_columns
            )

            fig = px.histogram(
                reservoir_df,
                x=selected_column,
                title=f"Distribution of {selected_column}",
                color_discrete_sequence=["#0891B2"]
            )

            fig.update_layout(template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

        st.download_button(
            "⬇ Download Reservoir Dataset",
            data=reservoir_df.to_csv(index=False).encode("utf-8"),
            file_name="reservoir_dataset.csv",
            mime="text/csv"
        )

# --------------------------------------------------
# 11. ABOUT PROJECT
# --------------------------------------------------

elif page == "About Project":

    st.subheader("📘 About WaterScarcity Compass")

    st.write("""
    WaterScarcity Compass is a Data Warehouse and Data Mining
    project designed to analyse groundwater and reservoir
    information and support early identification of local
    water stress.

    The system uses historical water resource datasets,
    data preprocessing, multidimensional analysis and
    visualization to support water resource monitoring.
    """)

    st.subheader("Project Objectives")

    st.markdown("""
    - Analyse historical groundwater information.
    - Monitor reservoir water measurements.
    - Organise data for multidimensional analysis.
    - Implement OLAP operations.
    - Identify geographical and temporal patterns.
    - Develop and evaluate a water stress prediction model.
    """)

    st.subheader("Technologies")

    st.write(
        "Python • Pandas • Streamlit • Plotly • "
        "Data Warehousing • OLAP • Machine Learning"
    )

# --------------------------------------------------
# 12. FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "WaterScarcity Compass | Data Warehouse and Data Mining Project"
)

st.caption(
    "All displayed measurements are calculated from the loaded datasets. "
    "Groundwater level is measured in metres."
)
