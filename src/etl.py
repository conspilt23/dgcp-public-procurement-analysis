from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW_PATH = PROJECT_ROOT / "data" / "raw" / "dgcp_secp_2015_2026.csv"
DEFAULT_PROCESSED_PATH = PROJECT_ROOT / "data" / "processed" / "dgcp_secp_cleaned.csv"

BOOLEAN_COLUMNS = [
    "DIRIGIDO_MIPYMES",
    "DIRIGIDO_MIPYMES_MUJERES",
    "COMPRA_VERDE",
    "COMPRA_CONJUNTA",
]

REQUIRED_COLUMNS = [
    "CODIGO_PROCESO",
    "CODIGO_UNIDAD_COMPRA",
    "UNIDAD_COMPRA",
    "MODALIDAD",
    "TIPO_EXCEPCION",
    "CARATULA",
    "ESTADO_PROCESO",
    "MONEDA",
    "MONTO_ESTIMADO",
    "FECHA_PUBLICACION",
    "HORA_PUBLICACION",
    "DIRIGIDO_MIPYMES",
    "DIRIGIDO_MIPYMES_MUJERES",
    "OBJETO_PROCESO",
    "DECRETO_PRESIDENCIAL",
    "COMPRA_VERDE",
    "COMPRA_CONJUNTA",
    "URL",
]

# Source-data quality threshold used by the original analysis.
# It is a source-currency threshold, not an FX conversion.
MAX_REASONABLE_AMOUNT = 100_000_000_000


class DataValidationError(ValueError):
    """Raised when the source schema is not compatible with the ETL."""


def load_raw_data(file_path: str | Path) -> pd.DataFrame:
    """Load the DGCP CSV without mutating the source file."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {file_path}\n"
            "Download the source dataset and place it under data/raw/."
        )

    print(f"[ETL] Loading raw data from: {file_path}")
    df = pd.read_csv(file_path, low_memory=False)
    print(f"[ETL] Loaded {len(df):,} initial records.")
    return df


def validate_source_schema(df: pd.DataFrame) -> None:
    """Validate the columns required by the pipeline."""
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise DataValidationError(
            "Source dataset is missing required columns: " + ", ".join(missing)
        )


def _clean_string_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    for col in columns:
        # StringDtype preserves missing values as <NA> instead of the literal "nan".
        df[col] = df[col].astype("string").str.strip()


def _standardize_boolean_column(series: pd.Series, column_name: str = "") -> pd.Series:
    normalized = series.astype("string").str.strip().str.upper()
    mapping = {"SI": True, "SÍ": True, "NO": False}
    unexpected = normalized.dropna()[~normalized.dropna().isin(mapping)]
    if not unexpected.empty:
        values = ", ".join(sorted(unexpected.unique())[:10])
        print(
            f"[ETL] Warning: unexpected values in {column_name or 'boolean column'} "
            f"will become <NA>: {values}"
        )
    return normalized.map(mapping).astype("boolean")


def clean_procurement_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and transform the procurement dataset.

    Rules:
    - Trim text without converting nulls to the string 'nan'.
    - Normalize supported yes/no flags to nullable booleans.
    - Parse publication date and derive year/month/quarter.
    - Coerce estimated amounts to numeric.
    - Remove negative, null, or extreme amounts (>= 100B in source currency units).
    - Keep zero amounts as valid source observations and report them explicitly.
    """
    validate_source_schema(df)
    work = df.copy()
    print("[ETL] Cleaning and transforming data...")

    string_columns = work.select_dtypes(include=["object", "string"]).columns
    _clean_string_columns(work, string_columns)

    for col in BOOLEAN_COLUMNS:
        if col in work.columns:
            work[col] = _standardize_boolean_column(work[col], column_name=col)

    work["FECHA_PUBLICACION"] = pd.to_datetime(
        work["FECHA_PUBLICACION"], errors="coerce"
    )
    work["MONTO_ESTIMADO"] = pd.to_numeric(
        work["MONTO_ESTIMADO"], errors="coerce"
    )

    work["YEAR"] = work["FECHA_PUBLICACION"].dt.year.astype("Int64")
    work["MONTH"] = work["FECHA_PUBLICACION"].dt.month.astype("Int64")
    work["QUARTER"] = work["FECHA_PUBLICACION"].dt.quarter.astype("Int64")

    invalid_mask = (
        work["MONTO_ESTIMADO"].isna()
        | work["MONTO_ESTIMADO"].lt(0)
        | work["MONTO_ESTIMADO"].ge(MAX_REASONABLE_AMOUNT)
    )
    filtered_df = work.loc[~invalid_mask].copy()

    removed_rows = int(invalid_mask.sum())
    zero_rows = int((filtered_df["MONTO_ESTIMADO"] == 0).sum())
    print(f"[ETL] Removed {removed_rows:,} invalid amount rows (negative/null/extreme).")
    print(
        f"[ETL] Final records: {len(filtered_df):,} | "
        f"Zero-amount records retained: {zero_rows:,}"
    )
    return filtered_df


def save_processed_data(df: pd.DataFrame, output_path: str | Path) -> None:
    """Save the cleaned dataset to CSV."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"[ETL] Cleaned dataset saved to: {output_path}")


def run_etl(
    input_path: str | Path = DEFAULT_RAW_PATH,
    output_path: str | Path = DEFAULT_PROCESSED_PATH,
) -> pd.DataFrame:
    """Run the complete local ETL pipeline and return the cleaned DataFrame."""
    df_raw = load_raw_data(input_path)
    df_clean = clean_procurement_data(df_raw)
    save_processed_data(df_clean, output_path)
    return df_clean


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean the DGCP procurement CSV.")
    parser.add_argument("--input", type=Path, default=DEFAULT_RAW_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_PROCESSED_PATH)
    args = parser.parse_args()
    run_etl(args.input, args.output)


if __name__ == "__main__":
    main()
