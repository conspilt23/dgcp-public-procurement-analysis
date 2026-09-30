from __future__ import annotations

import argparse
import os
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV_PATH = PROJECT_ROOT / "data" / "processed" / "dgcp_secp_cleaned.csv"
DEFAULT_DATABASE = "DGCP_Procurement"
DEFAULT_DRIVER = "ODBC Driver 18 for SQL Server"
CHUNK_SIZE = 10_000

# Load local settings from .env when present. Existing OS environment variables take precedence.
load_dotenv(PROJECT_ROOT / ".env")

EXPECTED_COLUMNS = [
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
    "YEAR",
    "MONTH",
    "QUARTER",
]

REQUIRED_SQL_TABLES = [
    "Staging_Procurement",
    "Dim_Purchasing_Unit",
    "Dim_Modality",
    "Dim_Process_Status",
    "Fact_Procurement",
]


class DatabaseSchemaError(RuntimeError):
    """Raised when the local SQL Server schema is not ready for the loader."""


class DatabaseLoadError(RuntimeError):
    """Raised when the final staging row count does not match the expected load."""


def build_engine():
    """Create a SQL Server engine using environment variables and Windows authentication."""
    server = os.getenv("SQL_SERVER", "localhost")
    database = os.getenv("SQL_DATABASE", DEFAULT_DATABASE)
    driver = os.getenv("SQL_DRIVER", DEFAULT_DRIVER)
    trusted = os.getenv("SQL_TRUSTED_CONNECTION", "yes").lower()
    encrypt = os.getenv("SQL_ENCRYPT", "no").lower()
    trust_server_certificate = os.getenv(
        "SQL_TRUST_SERVER_CERTIFICATE", "yes"
    ).lower()

    params = [
        f"driver={quote_plus(driver)}",
        f"Encrypt={quote_plus(encrypt)}",
        f"TrustServerCertificate={quote_plus(trust_server_certificate)}",
    ]
    if trusted in {"yes", "true", "1"}:
        params.append("Trusted_Connection=yes")

    connection_string = (
        f"mssql+pyodbc://@{quote_plus(server)}/{quote_plus(database)}?"
        f"{'&'.join(params)}"
    )
    return create_engine(connection_string, fast_executemany=True)


def validate_processed_columns(columns) -> None:
    """Validate the processed CSV header before touching the SQL staging table."""
    missing = [col for col in EXPECTED_COLUMNS if col not in columns]
    if missing:
        raise ValueError(
            "Processed CSV is missing required columns: " + ", ".join(missing)
        )


def validate_processed_file(csv_file: Path) -> None:
    """Validate that the processed CSV exists and contains the expected schema."""
    if not csv_file.exists():
        raise FileNotFoundError(
            f"Processed CSV not found: {csv_file}\n"
            "Run `python src/etl.py` first."
        )

    header = pd.read_csv(csv_file, nrows=0, encoding="utf-8-sig")
    validate_processed_columns(header.columns)


def validate_target_schema(engine) -> None:
    """Check that the SQL objects required by the pipeline exist before loading."""
    inspector = inspect(engine)
    missing_tables = [
        table for table in REQUIRED_SQL_TABLES
        if not inspector.has_table(table, schema="dbo")
    ]

    if missing_tables:
        raise DatabaseSchemaError(
            "Required SQL Server tables were not found in schema dbo: "
            + ", ".join(missing_tables)
            + ".\nRun sql/01_create_database.sql and sql/02_create_tables.sql first."
        )

    actual_columns = {
        column["name"]
        for column in inspector.get_columns("Staging_Procurement", schema="dbo")
    }
    missing_columns = [
        col for col in EXPECTED_COLUMNS if col not in actual_columns
    ]

    if missing_columns:
        raise DatabaseSchemaError(
            "dbo.Staging_Procurement is missing required columns: "
            + ", ".join(missing_columns)
            + ".\nRe-run sql/02_create_tables.sql to recreate the expected schema."
        )


def count_table_rows(engine, table_name: str) -> int:
    """Return the row count for a known project table."""
    if table_name not in REQUIRED_SQL_TABLES:
        raise ValueError(f"Unsupported table name: {table_name}")

    query = text(f"SELECT COUNT(*) FROM dbo.{table_name}")
    with engine.connect() as connection:
        return int(connection.execute(query).scalar_one())


def count_csv_rows(csv_file: Path) -> int:
    with csv_file.open("r", encoding="utf-8-sig") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def load_data_to_staging(
    csv_file: str | Path = DEFAULT_CSV_PATH,
    replace_staging: bool = True,
) -> int:
    """Load the processed CSV into dbo.Staging_Procurement and reconcile row counts."""
    csv_file = Path(csv_file)
    validate_processed_file(csv_file)

    print("[DB LOAD] Connecting to SQL Server...")
    engine = build_engine()

    # Validate database structure BEFORE truncating staging.
    print("[DB LOAD] Validating target SQL schema...")
    validate_target_schema(engine)
    print("[DB LOAD] Required SQL tables and staging columns detected.")

    total_rows = count_csv_rows(csv_file)
    print(f"[DB LOAD] CSV rows detected: {total_rows:,}")

    existing_rows = count_table_rows(engine, "Staging_Procurement")

    if replace_staging:
        print("[DB LOAD] Clearing dbo.Staging_Procurement for an idempotent reload...")
        with engine.begin() as connection:
            connection.execute(text("TRUNCATE TABLE dbo.Staging_Procurement"))
        existing_rows = 0

    loaded_rows = 0
    reader = pd.read_csv(csv_file, chunksize=CHUNK_SIZE, low_memory=False)
    with tqdm(total=total_rows, unit="rows", desc="Loading SQL Server") as progress:
        for chunk in reader:
            # Keep this guard at chunk level as a defensive check in case the file changes mid-run.
            validate_processed_columns(chunk.columns)
            chunk = chunk[EXPECTED_COLUMNS]
            chunk.to_sql(
                name="Staging_Procurement",
                schema="dbo",
                con=engine,
                if_exists="append",
                index=False,
                chunksize=CHUNK_SIZE,
            )
            loaded_rows += len(chunk)
            progress.update(len(chunk))

    final_rows = count_table_rows(engine, "Staging_Procurement")
    expected_final_rows = existing_rows + loaded_rows

    if final_rows != expected_final_rows:
        raise DatabaseLoadError(
            "Staging row-count reconciliation failed: "
            f"expected {expected_final_rows:,}, found {final_rows:,}."
        )

    print(
        "[DB LOAD] Staging load completed successfully. "
        f"Loaded {loaded_rows:,} rows; staging now contains {final_rows:,} rows."
    )
    return loaded_rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load the processed DGCP CSV to SQL Server staging."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_CSV_PATH)
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to existing staging instead of truncating it first.",
    )
    args = parser.parse_args()
    load_data_to_staging(args.input, replace_staging=not args.append)


if __name__ == "__main__":
    main()
