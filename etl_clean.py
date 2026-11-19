
from pathlib import Path
import pandas as pd

folder = Path(r"C:\Users\HP\Downloads\Documents\WaterScarcityCompass")
output_folder = folder / "cleaned_data"
output_folder.mkdir(exist_ok=True)

for file in folder.glob("*.csv"):
    print(f"\nCleaning: {file.name}")

    df = pd.read_csv(file)

    # Clean column names
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace(r"\s+", "_", regex=True)
    )

    # Remove fully duplicated rows
    before = len(df)
    df = df.drop_duplicates()
    removed = before - len(df)

    # Standardize text fields without changing measurement units
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].map(
            lambda x: x.strip() if isinstance(x, str) else x
        )

    # Convert acquisition time to datetime where possible
    date_col = "Data_Acquisition_Time"
    if date_col in df.columns:
        df[date_col] = pd.to_datetime(
            df[date_col], errors="coerce"
        )

    output_file = output_folder / f"cleaned_{file.name}"
    df.to_csv(output_file, index=False)

    print("Rows after cleaning:", len(df))
    print("Duplicate rows removed:", removed)
    print("Saved to:", output_file)

print("\nETL cleaning step completed!")
