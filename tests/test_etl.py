import pandas as pd
import pytest

from src.etl import MAX_REASONABLE_AMOUNT, clean_procurement_data


@pytest.fixture
def base_row():
    return {
        "CODIGO_PROCESO": "P-001",
        "CODIGO_UNIDAD_COMPRA": 10,
        "UNIDAD_COMPRA": " Unidad 1 ",
        "MODALIDAD": "Contratación Menor",
        "TIPO_EXCEPCION": None,
        "CARATULA": "Proceso",
        "ESTADO_PROCESO": "Publicado",
        "MONEDA": "DOP",
        "MONTO_ESTIMADO": 1000,
        "FECHA_PUBLICACION": "2026-01-15",
        "HORA_PUBLICACION": "08:00",
        "DIRIGIDO_MIPYMES": "SÍ",
        "DIRIGIDO_MIPYMES_MUJERES": "NO",
        "OBJETO_PROCESO": "Bienes",
        "DECRETO_PRESIDENCIAL": None,
        "COMPRA_VERDE": "NO",
        "COMPRA_CONJUNTA": "SI",
        "URL": "https://example.com",
    }


def test_negative_and_extreme_amounts_are_removed(base_row):
    rows = [
        {**base_row, "CODIGO_PROCESO": "P-001", "MONTO_ESTIMADO": 0},
        {**base_row, "CODIGO_PROCESO": "P-002", "MONTO_ESTIMADO": -10},
        {
            **base_row,
            "CODIGO_PROCESO": "P-003",
            "MONTO_ESTIMADO": MAX_REASONABLE_AMOUNT,
        },
        {**base_row, "CODIGO_PROCESO": "P-004", "MONTO_ESTIMADO": 2500},
    ]
    cleaned = clean_procurement_data(pd.DataFrame(rows))

    assert set(cleaned["CODIGO_PROCESO"]) == {"P-001", "P-004"}
    assert (cleaned["MONTO_ESTIMADO"] >= 0).all()


def test_zero_amounts_are_retained(base_row):
    cleaned = clean_procurement_data(
        pd.DataFrame([{**base_row, "MONTO_ESTIMADO": 0}])
    )
    assert len(cleaned) == 1
    assert cleaned.iloc[0]["MONTO_ESTIMADO"] == 0


def test_booleans_and_dates_are_standardized(base_row):
    cleaned = clean_procurement_data(pd.DataFrame([base_row]))
    row = cleaned.iloc[0]

    assert bool(row["DIRIGIDO_MIPYMES"]) is True
    assert bool(row["DIRIGIDO_MIPYMES_MUJERES"]) is False
    assert bool(row["COMPRA_CONJUNTA"]) is True
    assert row["YEAR"] == 2026
    assert row["MONTH"] == 1
    assert row["QUARTER"] == 1


def test_missing_text_values_are_not_literal_nan(base_row):
    row = {**base_row, "UNIDAD_COMPRA": None}
    cleaned = clean_procurement_data(pd.DataFrame([row]))
    assert pd.isna(cleaned.iloc[0]["UNIDAD_COMPRA"])
    assert str(cleaned.iloc[0]["UNIDAD_COMPRA"]) != "nan"


def test_missing_required_source_columns_raise_validation_error(base_row):
    from src.etl import DataValidationError, REQUIRED_COLUMNS, validate_source_schema

    df = pd.DataFrame([base_row]).drop(columns=[REQUIRED_COLUMNS[0]])

    with pytest.raises(DataValidationError, match="missing required columns"):
        validate_source_schema(df)


def test_unexpected_boolean_values_become_na(base_row):
    row = {**base_row, "DIRIGIDO_MIPYMES": "DESCONOCIDO"}
    cleaned = clean_procurement_data(pd.DataFrame([row]))

    assert pd.isna(cleaned.iloc[0]["DIRIGIDO_MIPYMES"])
