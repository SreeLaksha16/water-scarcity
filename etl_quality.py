
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "cleaned_data"
OUTPUT_DIR.mkdir(exist_ok=True)

FILES = {
    "groundwater": {
        "input": BASE_DIR / "cleaned_groundwater.csv",
        "level": "Groundwater Level Quarterly Manual (meter)"
    },
    "reservoir": {
        "input": BASE_DIR / "cleaned_reservoir.csv",
        "level": "Manual Daily Reservoir water level (m)"
    }
}

def process_dataset(name, config):
    print(f"\nProcessing {name}...")

    df = pd.read_csv(config["input"])
    level = config["level"]

    original_rows = len(df)

    # Preserve original measurement and flag missing values
    df["measurement_missing"] = df[level].isna()

    # Parse dates without changing original date column
    df["parsed_date"] = pd.to_datetime(
        df["Data Acquisition Time"],
        dayfirst=True,
        errors="coerce"
    )

    df["date_invalid"] = df["parsed_date"].isna()

    # Identify repeated station/date/location records
    keys = [
        "Station", "District", "Latitude",
        "Longitude", "parsed_date"
    ]

    df["duplicate_review"] = df.duplicated(
        subset=keys, keep=False
    )

    # Flag unusual groundwater readings for review.
    # Do not automatically delete negative or high values.
    if name == "groundwater":
        df["unusual_value_review"] = (
            (df[level] < 0) | (df[level] > 50)
        )
    else:
        df["unusual_value_review"] = False

    # Save all records; no automatic row deletion
    output_file = OUTPUT_DIR / f"{name}_etl.csv"
    df.to_csv(output_file, index=False)

    # Create data quality summary
    report = pd.DataFrame({
        "Metric": [
            "Original rows",
            "Missing measurements",
            "Invalid dates",
            "Duplicate records for review",
            "Unusual values for review"
        ],
        "Count": [
            original_rows,
            int(df["measurement_missing"].sum()),
            int(df["date_invalid"].sum()),
            int(df["duplicate_review"].sum()),
            int(df["unusual_value_review"].sum())
        ]
    })

    report_file = OUTPUT_DIR / f"{name}_quality_report.csv"
    report.to_csv(report_file, index=False)

    print(report.to_string(index=False))
    print("Saved:", output_file)
    print("Saved:", report_file)


if __name__ == "__main__":
    for name, config in FILES.items():
        if config["input"].exists():
            process_dataset(name, config)
        else:
            print("Missing input:", config["input"])
