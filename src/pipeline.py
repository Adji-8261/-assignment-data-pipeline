from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_FILE = BASE_DIR / "data" / "raw" / "automobileEDA_dirty_training.csv"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "automobileEDA_processed.csv"

def load_data(filepath: str) -> pd.DataFrame:
    """Baca CSV lokal ke DataFrame."""
    df = pd.read_csv(filepath)
    print(f"[load]  {filepath} -> {len(df)} baris")
    return df

def load_dataset():
    """Extract: read the untouched source CSV."""
    if not RAW_FILE.exists():
        raise FileNotFoundError(f"Raw dataset not found: {RAW_FILE}")
    return pd.read_csv(RAW_FILE)


def inspect_dataset(df):
    """Print the initial dataset profile to the terminal."""
    print("\n========== INITIAL DATA INSPECTION ==========")
    print("\n--- First five rows ---")
    print(df.head().to_string(index=False))
    print("\n--- Dataset dimensions ---")
    print(f"Rows: {df.shape[0]} | Columns: {df.shape[1]}")
    print("\n--- Column names ---")
    print(df.columns.tolist())
    print("\n--- Data types ---")
    print(df.dtypes.to_string())
    print("\n--- Missing values per column ---")
    print(df.isna().sum().to_string())
    print(f"\n--- Duplicate records ---\n{df.duplicated().sum()}")
    print("\n--- Unique categorical values ---")
    categorical = [
        "make", "aspiration", "num-of-doors", "body-style",
        "drive-wheels", "engine-location", "engine-type",
        "num-of-cylinders", "fuel-system", "horsepower-binned"
    ]
    for col in categorical:
        if col in df.columns:
            print(f"{col}: {df[col].dropna().unique().tolist()}")


def parse_mixed_dates(series):
    """Parse known mixed date representations while retaining missing dates.

    Numeric slash dates with a first component > 12 are interpreted as
    day/month/year; other slash and numeric-hyphen dates use month/day/year.
    ISO and month-name formats are also accepted.
    """
    def parse_one(value):
        if pd.isna(value):
            return pd.NaT
        value = str(value).strip()
        try:
            if "/" in value:
                first = int(value.split("/")[0])
                fmt = "%d/%m/%Y" if first > 12 else "%m/%d/%Y"
                return pd.to_datetime(value, format=fmt, errors="coerce")
            if value.count("-") == 2:
                parts = value.split("-")
                if len(parts[0]) == 4:
                    return pd.to_datetime(value, format="%Y-%m-%d", errors="coerce")
                if parts[1].isalpha():
                    return pd.to_datetime(value, format="%d-%b-%Y", errors="coerce")
                if parts[0].isnumeric():
                    return pd.to_datetime(value, format="%m-%d-%Y", errors="coerce")
            return pd.to_datetime(value, errors="coerce")
        except (ValueError, TypeError):
            return pd.NaT
    return series.map(parse_one)


def clean_dataset(df):
    """Transform: clean missing data, duplicates, text, and data types."""
    result = df.copy()
    before_rows = len(result)
    before_missing = int(result.isna().sum().sum())
    changed_columns = []

    # Normalize whitespace and case for text fields; categories are lowercase.
    text_cols = result.select_dtypes(include=["object"]).columns.tolist()
    for col in text_cols:
        if col == "transaction_date":
            continue
        cleaned = result[col].map(
            lambda x: x.strip().lower() if isinstance(x, str) else x
        )
        if not cleaned.equals(result[col]):
            changed_columns.append(col)
        result[col] = cleaned

    # Parse mixed transaction date strings into a proper datetime dtype.
    if "transaction_date" in result.columns:
        result["transaction_date"] = parse_mixed_dates(result["transaction_date"])
        changed_columns.append("transaction_date")

    # Remove exact duplicate rows after text normalization.
    duplicate_count = int(result.duplicated().sum())
    result = result.drop_duplicates().copy()

    # Fill categorical missing values with the mode (most frequent category).
    categorical_fill = ["make", "num-of-doors", "horsepower-binned"]
    for col in categorical_fill:
        if col in result.columns and result[col].isna().any():
            mode = result[col].mode(dropna=True)
            if not mode.empty:
                result[col] = result[col].fillna(mode.iloc[0])
                changed_columns.append(col)

    # Numeric missing values are imputed with the median, which is less
    # sensitive to extreme values than the mean.
    numeric_fill = ["normalized-losses", "stroke", "horsepower", "price"]
    for col in numeric_fill:
        if col in result.columns and result[col].isna().any():
            result[col] = result[col].fillna(result[col].median())
            changed_columns.append(col)

    # Dates are not fabricated: retain missing dates as NaT and report them.
    # This avoids inventing transaction timestamps unsupported by the source.

    # Ensure numeric columns remain numeric.
    for col in result.columns:
        if col not in ["transaction_date"] and result[col].dtype == "object":
            # Only convert if all non-null values can be parsed numerically.
            converted = pd.to_numeric(result[col], errors="coerce")
            if result[col].notna().sum() and converted.notna().sum() == result[col].notna().sum():
                result[col] = converted
                changed_columns.append(col)

    report = {
        "rows_before": before_rows,
        "rows_after": len(result),
        "missing_before": before_missing,
        "missing_after": int(result.isna().sum().sum()),
        "duplicates_removed": duplicate_count,
        "changed_columns": sorted(set(changed_columns)),
    }
    print("\n========== CLEANING SUMMARY ==========")
    print(f"Rows before / after: {report['rows_before']} / {report['rows_after']}")
    print(f"Missing values before / after: {report['missing_before']} / {report['missing_after']}")
    print(f"Duplicate records removed: {report['duplicates_removed']}")
    print(f"Columns changed: {report['changed_columns']}")
    print("\nMissing values after cleaning:")
    print(result.isna().sum().to_string())
    return result, report


def transform_dataset(df):
    """Transform: add Min-Max scaled price and one-hot body-style features."""
    result = df.copy()
    examples = {}

    if "price" in result.columns:
        min_value = result["price"].min()
        max_value = result["price"].max()
        if pd.notna(min_value) and pd.notna(max_value) and max_value != min_value:
            result["price_minmax"] = (result["price"] - min_value) / (max_value - min_value)
            examples["price"] = {
                "before": float(result["price"].iloc[0]),
                "after": float(result["price_minmax"].iloc[0]),
                "min": float(min_value),
                "max": float(max_value),
            }

    if "body-style" in result.columns:
        encoded = pd.get_dummies(
            result["body-style"], prefix="body_style", dtype=int
        )
        result = pd.concat([result, encoded], axis=1)
        examples["body-style"] = {
            "before": str(df["body-style"].iloc[0]),
            "after_columns": encoded.columns.tolist(),
        }

    print("\n========== TRANSFORMATION SUMMARY ==========")
    if "price" in examples:
        item = examples["price"]
        print(f"price: {item['before']} -> price_minmax: {item['after']:.6f}")
    if "body-style" in examples:
        print(f"body-style: {examples['body-style']['before']} -> one-hot columns: "
              f"{examples['body-style']['after_columns']}")
    return result, examples


def save_dataset(df):
    """Load: write the processed dataset to a new file, never overwrite raw."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nProcessed dataset saved to: {OUTPUT_FILE}")


def run_pipeline():
    raw_df = load_dataset()
    inspect_dataset(raw_df)
    cleaned_df, cleaning_report = clean_dataset(raw_df)
    transformed_df, transformation_examples = transform_dataset(cleaned_df)
    save_dataset(transformed_df)
    print("\n========== PIPELINE COMPLETED ==========")
    return cleaning_report, transformation_examples


if __name__ == "__main__":
    run_pipeline()
