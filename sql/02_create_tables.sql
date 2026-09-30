/*
    DGCP Public Procurement Analytics
    Step 2 - Create staging, dimensions and fact table.

    This schema intentionally stays close to the original project design.
*/
USE DGCP_Procurement;
GO

-- Drop in foreign-key order so the script can be re-run during development.
IF OBJECT_ID(N'dbo.Fact_Procurement', N'U') IS NOT NULL DROP TABLE dbo.Fact_Procurement;
IF OBJECT_ID(N'dbo.Dim_Purchasing_Unit', N'U') IS NOT NULL DROP TABLE dbo.Dim_Purchasing_Unit;
IF OBJECT_ID(N'dbo.Dim_Modality', N'U') IS NOT NULL DROP TABLE dbo.Dim_Modality;
IF OBJECT_ID(N'dbo.Dim_Process_Status', N'U') IS NOT NULL DROP TABLE dbo.Dim_Process_Status;
IF OBJECT_ID(N'dbo.Staging_Procurement', N'U') IS NOT NULL DROP TABLE dbo.Staging_Procurement;
GO

CREATE TABLE dbo.Staging_Procurement (
    CODIGO_PROCESO NVARCHAR(255),
    CODIGO_UNIDAD_COMPRA INT,
    UNIDAD_COMPRA NVARCHAR(500),
    MODALIDAD NVARCHAR(255),
    TIPO_EXCEPCION NVARCHAR(500),
    CARATULA NVARCHAR(MAX),
    ESTADO_PROCESO NVARCHAR(255),
    MONEDA NVARCHAR(50),
    MONTO_ESTIMADO DECIMAL(18, 2),
    FECHA_PUBLICACION DATE,
    HORA_PUBLICACION NVARCHAR(50),
    DIRIGIDO_MIPYMES BIT,
    DIRIGIDO_MIPYMES_MUJERES BIT,
    OBJETO_PROCESO NVARCHAR(255),
    DECRETO_PRESIDENCIAL NVARCHAR(255),
    COMPRA_VERDE BIT,
    COMPRA_CONJUNTA BIT,
    URL NVARCHAR(MAX),
    YEAR INT,
    MONTH INT,
    QUARTER INT
);
GO

CREATE TABLE dbo.Dim_Purchasing_Unit (
    Unit_Key INT IDENTITY(1,1) PRIMARY KEY,
    Unit_Code INT UNIQUE NOT NULL,
    Unit_Name NVARCHAR(500) NOT NULL
);
GO

CREATE TABLE dbo.Dim_Modality (
    Modality_Key INT IDENTITY(1,1) PRIMARY KEY,
    Modality_Name NVARCHAR(255) NOT NULL,
    Exception_Type NVARCHAR(500) NOT NULL
);
GO

CREATE TABLE dbo.Dim_Process_Status (
    Status_Key INT IDENTITY(1,1) PRIMARY KEY,
    Status_Name NVARCHAR(255) UNIQUE NOT NULL
);
GO

CREATE TABLE dbo.Fact_Procurement (
    Fact_ID INT IDENTITY(1,1) PRIMARY KEY,
    Process_Code NVARCHAR(255) NOT NULL,
    Unit_Key INT FOREIGN KEY REFERENCES dbo.Dim_Purchasing_Unit(Unit_Key),
    Modality_Key INT FOREIGN KEY REFERENCES dbo.Dim_Modality(Modality_Key),
    Status_Key INT FOREIGN KEY REFERENCES dbo.Dim_Process_Status(Status_Key),
    Publication_Date DATE,
    Currency NVARCHAR(50),
    Estimated_Amount DECIMAL(18, 2),
    Is_MiPymes BIT,
    Is_MiPymes_Women BIT,
    Is_Green_Purchase BIT,
    Is_Joint_Purchase BIT,
    Process_Object NVARCHAR(255),
    Year INT,
    Month INT,
    Quarter INT
);
GO
