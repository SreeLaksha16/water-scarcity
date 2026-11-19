
from pathlib import Path
import pandas as pd

# Your project folder
folder = Path(
    r"C:\Users\HP\Downloads\Documents\WaterScarcityCompass"
)

# Extract and inspect each CSV file
for file in folder.glob("*.csv"):
    print("\n" + "=" * 60)
    print("DATASET:", file.name)

    df = pd.read_csv(file)

    print("Rows and columns:", df.shape)
    print("\nColumn names:")
    print(df.columns.tolist())

    print("\nFirst five rows:")
    print(df.head())

# Inspect Excel files separately
for file in folder.glob("*.xlsx"):
    print("\n" + "=" * 60)
    print("EXCEL FILE:", file.name)

from pathlib import Path
import pandas as pd

folder = Path(
    r"C:\Users\HP\Downloads\Documents\WaterScarcityCompass"
)

# Read CSV datasets
for file in folder.glob("*.csv"):
    print("\n" + "=" * 60)
    print("DATASET:", file.name)

    df = pd.read_csv(file)

    print("Shape:", df.shape)
    print("Columns:", df.columns.tolist())
    print(df.head(3).to_string(index=False))

# Read Excel datasets
for file in folder.glob("*.xlsx"):
    print("\n" + "=" * 60)
    print("EXCEL FILE:", file.name)

    try:
        sheets = pd.read_excel(
            file, sheet_name=None
        )

        for sheet_name, df in sheets.items():
            print("\nSheet:", sheet_name)
            print("Shape:", df.shape)
            print("Columns:", df.columns.tolist())
            print(df.head(3).to_string(index=False))

    except Exception as e:
        print("Could not read Excel file:", e)

    excel = pd.ExcelFile(file)
    print("Sheets:", excel.sheet_names)

    for sheet in excel.sheet_names:
        df = pd.read_excel(file, sheet_name=sheet)
        print("\nSheet:", sheet)
        print("Rows and columns:", df.shape)
        print("Columns:", df.columns.tolist())
        print(df.head())
s