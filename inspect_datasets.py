
from pathlib import Path
import pandas as pd

# Read datasets directly from this project folder
folder = Path(__file__).parent

files = list(folder.glob("*.csv"))
files += list(folder.glob("*.xlsx"))
files += list(folder.glob("*.xls"))

if not files:
    print("No CSV or Excel files found.")

for file in files:
    print("\n" + "=" * 60)
    print("FILE:", file.name)

    try:
        if file.suffix.lower() == ".csv":
            df = pd.read_csv(file, nrows=5)
        else:
            df = pd.read_excel(file, nrows=5)

        print("\nCOLUMN NAMES:")
        print(df.columns.tolist())

        print("\nFIRST 5 ROWS:")
        print(df.to_string(index=False))

        print("\nDATA TYPES:")
        print(df.dtypes)

    except Exception as e:
        print("Error reading file:", e)
