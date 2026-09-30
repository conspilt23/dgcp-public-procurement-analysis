from unittest.mock import patch

import pytest

from src.load_to_db import (
    DatabaseSchemaError,
    EXPECTED_COLUMNS,
    REQUIRED_SQL_TABLES,
    build_engine,
    validate_processed_columns,
    validate_target_schema,
)


def test_build_engine_uses_environment_connection_settings(monkeypatch):
    monkeypatch.setenv("SQL_SERVER", "localhost")
    monkeypatch.setenv("SQL_DATABASE", "DGCP_Procurement")
    monkeypatch.setenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server")
    monkeypatch.setenv("SQL_TRUSTED_CONNECTION", "yes")
    monkeypatch.setenv("SQL_ENCRYPT", "no")
    monkeypatch.setenv("SQL_TRUST_SERVER_CERTIFICATE", "yes")

    with patch("src.load_to_db.create_engine") as create_engine:
        create_engine.return_value = "mock-engine"
        result = build_engine()

    assert result == "mock-engine"
    connection_string = create_engine.call_args.args[0]
    assert "localhost/DGCP_Procurement" in connection_string
    assert "Trusted_Connection=yes" in connection_string
    assert "Encrypt=no" in connection_string
    assert "TrustServerCertificate=yes" in connection_string


class FakeInspector:
    def __init__(self, tables, columns):
        self.tables = set(tables)
        self.columns = list(columns)

    def has_table(self, table_name, schema=None):
        return table_name in self.tables and schema == "dbo"

    def get_columns(self, table_name, schema=None):
        return [{"name": column} for column in self.columns]


def test_target_schema_validation_passes_when_required_objects_exist():
    fake = FakeInspector(
        REQUIRED_SQL_TABLES,
        EXPECTED_COLUMNS,
    )

    with patch("src.load_to_db.inspect", return_value=fake):
        assert validate_target_schema("mock-engine") is None


def test_target_schema_validation_warns_with_actionable_error_when_tables_are_missing():
    fake = FakeInspector([], EXPECTED_COLUMNS)

    with patch("src.load_to_db.inspect", return_value=fake):
        with pytest.raises(DatabaseSchemaError, match="Run sql/01_create_database.sql"):
            validate_target_schema("mock-engine")


def test_target_schema_validation_detects_missing_staging_columns():
    fake = FakeInspector(
        REQUIRED_SQL_TABLES,
        EXPECTED_COLUMNS[:-1],
    )

    with patch("src.load_to_db.inspect", return_value=fake):
        with pytest.raises(DatabaseSchemaError, match="missing required columns"):
            validate_target_schema("mock-engine")


def test_processed_file_schema_is_validated_before_loading():
    validate_processed_columns(EXPECTED_COLUMNS)

    with pytest.raises(ValueError, match="missing required columns"):
        validate_processed_columns(EXPECTED_COLUMNS[:-1])
