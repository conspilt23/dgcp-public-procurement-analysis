/*
    DGCP Public Procurement Analytics
    Step 3 - Populate dimensions and fact table from staging.
*/
USE DGCP_Procurement;
GO

TRUNCATE TABLE dbo.Fact_Procurement;
DELETE FROM dbo.Dim_Process_Status;
DELETE FROM dbo.Dim_Modality;
DELETE FROM dbo.Dim_Purchasing_Unit;
GO

INSERT INTO dbo.Dim_Purchasing_Unit (Unit_Code, Unit_Name)
SELECT
    s.CODIGO_UNIDAD_COMPRA,
    MAX(COALESCE(s.UNIDAD_COMPRA, N'No especificado'))
FROM dbo.Staging_Procurement AS s
WHERE s.CODIGO_UNIDAD_COMPRA IS NOT NULL
GROUP BY s.CODIGO_UNIDAD_COMPRA;
GO

INSERT INTO dbo.Dim_Modality (Modality_Name, Exception_Type)
SELECT DISTINCT
    COALESCE(NULLIF(s.MODALIDAD, N''), N'No especificado'),
    COALESCE(NULLIF(s.TIPO_EXCEPCION, N''), N'No especificado')
FROM dbo.Staging_Procurement AS s;
GO

INSERT INTO dbo.Dim_Process_Status (Status_Name)
SELECT DISTINCT
    COALESCE(s.ESTADO_PROCESO, N'Desconocido')
FROM dbo.Staging_Procurement AS s;
GO

IF EXISTS (
    SELECT 1
    FROM dbo.Staging_Procurement AS s
    LEFT JOIN dbo.Dim_Purchasing_Unit AS u
        ON s.CODIGO_UNIDAD_COMPRA = u.Unit_Code
    WHERE u.Unit_Key IS NULL
)
BEGIN
    THROW 50001, 'Staging contains purchasing-unit codes that cannot be mapped.', 1;
END;
GO

IF EXISTS (
    SELECT 1
    FROM dbo.Staging_Procurement AS s
    LEFT JOIN dbo.Dim_Modality AS m
        ON COALESCE(s.MODALIDAD, N'No especificado') = m.Modality_Name
        AND NULLIF(s.TIPO_EXCEPCION, N'') = m.Exception_Type
    WHERE m.Modality_Key IS NULL
)
BEGIN
    THROW 50002, 'Staging contains modality values that cannot be mapped.', 1;
END;
GO

IF EXISTS (
    SELECT 1
    FROM dbo.Staging_Procurement AS s
    LEFT JOIN dbo.Dim_Process_Status AS st
        ON COALESCE(s.ESTADO_PROCESO, N'Desconocido') = st.Status_Name
    WHERE st.Status_Key IS NULL
)
BEGIN
    THROW 50003, 'Staging contains status values that cannot be mapped.', 1;
END;
GO

INSERT INTO dbo.Fact_Procurement (
    Process_Code, Unit_Key, Modality_Key, Status_Key, Publication_Date,
    Currency, Estimated_Amount, Is_MiPymes, Is_MiPymes_Women,
    Is_Green_Purchase, Is_Joint_Purchase, Process_Object, Year, Month, Quarter
)
SELECT
    s.CODIGO_PROCESO,
    u.Unit_Key,
    m.Modality_Key,
    st.Status_Key,
    s.FECHA_PUBLICACION,
    s.MONEDA,
    s.MONTO_ESTIMADO,
    s.DIRIGIDO_MIPYMES,
    s.DIRIGIDO_MIPYMES_MUJERES,
    s.COMPRA_VERDE,
    s.COMPRA_CONJUNTA,
    s.OBJETO_PROCESO,
    s.YEAR,
    s.MONTH,
    s.QUARTER
FROM dbo.Staging_Procurement AS s
INNER JOIN dbo.Dim_Purchasing_Unit AS u
    ON s.CODIGO_UNIDAD_COMPRA = u.Unit_Code
INNER JOIN dbo.Dim_Modality AS m
    ON COALESCE(s.MODALIDAD, N'No especificado') = m.Modality_Name
    AND NULLIF(s.TIPO_EXCEPCION, N'') = m.Exception_Type
INNER JOIN dbo.Dim_Process_Status AS st
    ON COALESCE(s.ESTADO_PROCESO, N'Desconocido') = st.Status_Name;
GO

SELECT COUNT(*) AS Total_Fact_Rows FROM dbo.Fact_Procurement;
GO
