
from pathlib import Path
import pandas as pd
import sqlite3

# Project folders
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "cleaned_data"
DB_PATH = BASE_DIR / "water_scarcity_warehouse.db"

# ETL cleaned datasets
groundwater_path = DATA_DIR / "groundwater_etl.csv"
reservoir_path = DATA_DIR / "reservoir_etl.csv"

if not groundwater_path.exists() or not reservoir_path.exists():
    raise FileNotFoundError(
        "ETL files missing. Run etl_quality.py first."
    )

groundwater = pd.read_csv(groundwater_path)
reservoir = pd.read_csv(reservoir_path)

# Combine datasets into one fact table
groundwater["Water_Source"] = "Groundwater"
reservoir["Water_Source"] = "Reservoir"

groundwater = groundwater.rename(columns={
    "Groundwater Level Quarterly Manual (meter)": "Water_Level"
})

reservoir = reservoir.rename(columns={
    "Manual Daily Reservoir water level (m)": "Water_Level"
})

groundwater["Measurement_Date"] = pd.to_datetime(
    groundwater["parsed_date"], errors="coerce"
)
reservoir["Measurement_Date"] = pd.to_datetime(
    reservoir["parsed_date"], errors="coerce"
)

common_columns = [
    "Station", "Agency", "State", "District", "Block",
    "Village", "River", "Basin", "Latitude", "Longitude",
    "Measurement_Date", "Water_Level", "Water_Source"
]

fact = pd.concat(
    [
        groundwater.reindex(columns=common_columns),
        reservoir.reindex(columns=common_columns)
    ],
    ignore_index=True
)

# Dimension tables
dim_station = pd.concat([
    groundwater[["Station", "Agency", "Water_Source"]],
    reservoir[["Station", "Agency", "Water_Source"]]
]).drop_duplicates().reset_index(drop=True)

dim_geography = fact[
    ["State", "District", "Block", "Village", "River", "Basin",
     "Latitude", "Longitude"]
].drop_duplicates().reset_index(drop=True)

valid_dates = fact["Measurement_Date"].dropna()

dim_date = pd.DataFrame({
    "Full_Date": valid_dates.dt.strftime("%Y-%m-%d").unique()
})
dim_date["Year"] = pd.to_datetime(dim_date["Full_Date"]).dt.year
dim_date["Month"] = pd.to_datetime(dim_date["Full_Date"]).dt.month
dim_date["Quarter"] = pd.to_datetime(
    dim_date["Full_Date"]
).dt.quarter

# Create warehouse database
with sqlite3.connect(DB_PATH) as connection:
    fact.to_sql("Fact_Water_Level", connection,
                if_exists="replace", index=False)
    dim_station.to_sql("Dim_Station", connection,
                       if_exists="replace", index=False)
    dim_geography.to_sql("Dim_Geography", connection,
                         if_exists="replace", index=False)
    dim_date.to_sql("Dim_Date", connection,
                    if_exists="replace", index=False)

print("\nDATA WAREHOUSE CREATED SUCCESSFULLY!")
print("------------------------------------")
print("Fact table rows:", len(fact))
print("Station dimension rows:", len(dim_station))
print("Geography dimension rows:", len(dim_geography))
print("Date dimension rows:", len(dim_date))
print("Database:", DB_PATH)
