
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "water_scarcity_warehouse.db"

st.set_page_config(
    page_title="WaterScarcity Compass",
    page_icon="💧",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg,#edf7fa,#f5fbff);
}
h1,h2,h3 {color:#075985;}
[data-testid="stMetric"] {
    background:white;
    padding:18px;
    border-radius:12px;
    box-shadow:0 2px 8px #00000012;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    with sqlite3.connect(DB) as conn:
        return pd.read_sql_query(
            "SELECT * FROM Fact_Water_Level", conn
        )

if not DB.exists():
    st.error("Warehouse database not found. Run schema_design.py")
    st.stop()

df = load_data()

st.title("💧 WaterScarcity Compass")
st.caption("Water Resource Monitoring | DWDM | Analytics & Decision Support")

st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Select Module",
    [
        "Overview",
        "Dataset Explorer",
        "Groundwater Analytics",
        "Reservoir Analytics",
        "OLAP Operations",
        "Prediction",
        "Reports"
    ]
)

# OVERVIEW
if page == "Overview":
    st.header("Water Resource Dashboard")

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Records",f"{len(df):,}")
    c2.metric("Groundwater Records",f"{(df.Water_Source=='Groundwater').sum():,}")
    c3.metric("Reservoir Records",f"{(df.Water_Source=='Reservoir').sum():,}")
    c4.metric("Stations",df.Station.nunique())

    st.subheader("Water Source Distribution")
    counts = df.Water_Source.value_counts().reset_index()
    counts.columns = ["Water Source","Records"]
    fig = px.pie(counts,names="Water Source",
                 values="Records",hole=.45)
    st.plotly_chart(fig,use_container_width=True)

    st.subheader("Dataset Preview")
    st.dataframe(df.head(15),use_container_width=True)

# DATASET EXPLORER
elif page == "Dataset Explorer":
    st.header("Dataset Explorer")

    source = st.selectbox(
        "Choose dataset",
        ["All","Groundwater","Reservoir"]
    )

    data = df if source=="All" else df[df.Water_Source==source]

    st.write("Records:",len(data))
    st.dataframe(data,use_container_width=True)

    st.download_button(
        "Download Dataset CSV",
        data=data.to_csv(index=False).encode("utf-8"),
        file_name="water_dataset.csv",
        mime="text/csv"
    )

# GROUNDWATER
elif page == "Groundwater Analytics":
    st.header("Groundwater Analytics")

    data = df[df.Water_Source=="Groundwater"].copy()
    data["Water_Level"] = pd.to_numeric(data.Water_Level,errors="coerce")

    district = st.selectbox(
        "Select District",
        ["All"]+sorted(data.District.dropna().unique().tolist())
    )

    if district!="All":
        data=data[data.District==district]

    a,b,c = st.columns(3)
    a.metric("Records",len(data))
    b.metric("Average Level",f"{data.Water_Level.mean():.2f} m")
    c.metric("Minimum Level",f"{data.Water_Level.min():.2f} m")

    chart=data.groupby("District",as_index=False).Water_Level.mean()
    chart=chart.sort_values("Water_Level")

    fig=px.bar(chart,x="District",y="Water_Level",
               title="Average Groundwater Level by District")
    st.plotly_chart(fig,use_container_width=True)

    st.dataframe(data,use_container_width=True)

# RESERVOIR
elif page == "Reservoir Analytics":
    st.header("Reservoir Analytics")

    data=df[df.Water_Source=="Reservoir"].copy()

    a,b,c=st.columns(3)
    a.metric("Records",len(data))
    b.metric("Average Level",f"{data.Water_Level.mean():.2f} m")
    c.metric("Maximum Level",f"{data.Water_Level.max():.2f} m")

    fig=px.line(
        data.sort_values("Measurement_Date"),
        x="Measurement_Date",y="Water_Level",
        title="Reservoir Water Level Trend"
    )
    st.plotly_chart(fig,use_container_width=True)
    st.dataframe(data,use_container_width=True)

# OLAP
elif page == "OLAP Operations":
    st.header("Interactive OLAP Analysis")

    operation=st.selectbox(
        "Select OLAP Operation",
        ["Slice","Dice","Roll-up","Drill-down"]
    )

    if operation=="Slice":
        dimension=st.selectbox(
            "Dimension",["Water_Source","State","District","Basin"]
        )
        values=sorted(df[dimension].dropna().unique().tolist())
        selected=st.selectbox("Choose value",values)
        result=df[df[dimension]==selected]

    elif operation=="Dice":
        source=st.multiselect(
            "Water Source",
            sorted(df.Water_Source.dropna().unique()),
            default=sorted(df.Water_Source.dropna().unique())
        )
        states=st.multiselect(
            "State",
            sorted(df.State.dropna().unique())
        )
        result=df[df.Water_Source.isin(source)]
        if states:
            result=result[result.State.isin(states)]

    elif operation=="Roll-up":
        level=st.selectbox(
            "Aggregation level",["State","District","Station"]
        )
        result=df.groupby(level,as_index=False).Water_Level.agg(
            ["count","mean","min","max"]
        ).reset_index()

    else:
        state=st.selectbox(
            "Select State",
            sorted(df.State.dropna().unique())
        )
        result=df[df.State==state]
        level=st.selectbox(
            "Drill-down level",["District","Station","Basin"]
        )
        result=result.groupby(level,as_index=False).Water_Level.agg(
            ["count","mean","min","max"]
        ).reset_index()

    st.success(f"{operation} completed")
    st.metric("Result Records",len(result))
    st.dataframe(result,use_container_width=True)

    if "Water_Level" in result.columns:
        fig=px.histogram(result,x="Water_Level",
                         title="OLAP Result Distribution")
        st.plotly_chart(fig,use_container_width=True)

# PREDICTION
elif page == "Prediction":
    st.header("Water Stress Prediction")
    st.warning(
        "Prediction module is under validation. "
        "No unvalidated prediction is presented as a real forecast."
    )
    st.info(
        "Groundwater and reservoir datasets currently have "
        "different geographic and temporal coverage. "
        "A validated forecasting model will be added after "
        "data quality and time-series validation."
    )

# REPORTS
elif page == "Reports":
    st.header("Download Analytics Report")

    st.write("Water Resource Dataset Summary")
    st.dataframe(
        df.groupby("Water_Source").Water_Level.agg(
            ["count","mean","min","max"]
        ).reset_index()
    )

    st.download_button(
        "Download Report Data (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="water_scarcity_report.csv",
        mime="text/csv"
    )
