
from pathlib import Path
import sqlite3
import pandas as pd
from itertools import combinations

BASE = Path(__file__).resolve().parent
DB = BASE / "water_scarcity_warehouse.db"

if not DB.exists():
    raise FileNotFoundError("Run schema_design.py first!")

def load_data():
    with sqlite3.connect(DB) as conn:
        return pd.read_sql_query(
            "SELECT * FROM Fact_Water_Level",
            conn
        )

def create_cube(df):
    dimensions = [
        "Water_Source",
        "State",
        "District",
        "Station",
        "Basin"
    ]

    measure = "Water_Level"
    results = []

    for size in range(1, len(dimensions) + 1):
        for dims in combinations(dimensions, size):

            grouped = (
                df.groupby(list(dims), dropna=False)[measure]
                .agg(
                    record_count="count",
                    average="mean",
                    minimum="min",
                    maximum="max"
                )
                .reset_index()
            )

            grouped["cube_dimensions"] = " + ".join(dims)
            results.append(grouped)

    return pd.concat(results, ignore_index=True)

def slice_data(df, dimension, value):
    return df[df[dimension] == value].copy()

def dice_data(df, filters):
    result = df.copy()

    for column, values in filters.items():
        if not isinstance(values, list):
            values = [values]

        result = result[result[column].isin(values)]

    return result

def roll_up(df, dimensions):
    return (
        df.groupby(dimensions, dropna=False)["Water_Level"]
        .agg(["count", "mean", "min", "max"])
        .reset_index()
    )

def drill_down(df, dimension):
    return (
        df.groupby(dimension, dropna=False)["Water_Level"]
        .agg(["count", "mean", "min", "max"])
        .reset_index()
    )

if __name__ == "__main__":

    df = load_data()

    print("DATA LOADED:", df.shape)

    cube = create_cube(df)

    output = BASE / "olap_cube_results.csv"
    cube.to_csv(output, index=False)

    print("\nOLAP CUBE CREATED SUCCESSFULLY!")
    print("Dimensions: Water_Source, State, District, Station, Basin")
    print("Measure: Water_Level")
    print("Cube rows:", len(cube))
    print("Saved:", output)

    print("\nSAMPLE CUBE:")
    print(cube.head(10).to_string(index=False))
