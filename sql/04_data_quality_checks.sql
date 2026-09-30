/*
    DGCP Public Procurement Analytics
    Step 4 - Data quality and reconciliation checks.
*/
USE DGCP_Procurement;
GO

-- 1. Row-count reconciliation.
SELECT
    (SELECT COUNT(*) FROM dbo.Staging_Procurement) AS Staging_Rows,
    (SELECT COUNT(*) FROM dbo.Fact_Procurement) AS Fact_Rows,
    (SELECT COUNT(*) FROM dbo.Staging_Procurement)
      - (SELECT COUNT(*) FROM dbo.Fact_Procurement) AS Row_Difference;
GO

-- 2. Orphan foreign-key checks.
SELECT COUNT(*) AS Orphan_Units
FROM dbo.Fact_Procurement AS f
LEFT JOIN dbo.Dim_Purchasing_Unit AS u ON f.Unit_Key = u.Unit_Key
WHERE u.Unit_Key IS NULL;

SELECT COUNT(*) AS Orphan_Modalities
FROM dbo.Fact_Procurement AS f
LEFT JOIN dbo.Dim_Modality AS m ON f.Modality_Key = m.Modality_Key
WHERE m.Modality_Key IS NULL;

SELECT COUNT(*) AS Orphan_Statuses
FROM dbo.Fact_Procurement AS f
LEFT JOIN dbo.Dim_Process_Status AS s ON f.Status_Key = s.Status_Key
WHERE s.Status_Key IS NULL;
GO

-- 3. Business-key uniqueness.
SELECT
    COUNT(*) AS Total_Fact_Rows,
    COUNT(DISTINCT Process_Code) AS Unique_Process_Codes,
    COUNT(*) - COUNT(DISTINCT Process_Code) AS Duplicate_Process_Codes
FROM dbo.Fact_Procurement;
GO

-- 4. Financial validity checks.
SELECT
    SUM(CASE WHEN Estimated_Amount < 0 THEN 1 ELSE 0 END) AS Negative_Amounts,
    SUM(CASE WHEN Estimated_Amount = 0 THEN 1 ELSE 0 END) AS Zero_Amounts,
    SUM(CASE WHEN Estimated_Amount IS NULL THEN 1 ELSE 0 END) AS Null_Amounts
FROM dbo.Fact_Procurement;
GO

-- 5. Date validity and range.
SELECT
    SUM(CASE WHEN Publication_Date IS NULL THEN 1 ELSE 0 END) AS Null_Dates,
    MIN(Publication_Date) AS First_Publication_Date,
    MAX(Publication_Date) AS Last_Publication_Date
FROM dbo.Fact_Procurement;
GO

-- 6. Currency distribution. Never sum these totals across currencies without FX conversion.
SELECT
    Currency,
    COUNT(*) AS Process_Count,
    SUM(Estimated_Amount) AS Total_Amount_In_Source_Currency,
    AVG(Estimated_Amount) AS Average_Amount_In_Source_Currency
FROM dbo.Fact_Procurement
GROUP BY Currency
ORDER BY Process_Count DESC;
GO

-- 7. DOP-only financial reconciliation used by executive KPIs.
SELECT
    COUNT(*) AS DOP_Process_Count,
    SUM(Estimated_Amount) AS Total_DOP_Amount,
    AVG(Estimated_Amount) AS Average_DOP_Amount
FROM dbo.Fact_Procurement
WHERE Currency = N'DOP';
GO

-- 8. Analytical profile metrics used to reconcile Python / SQL / Power BI.
SELECT
    COUNT(DISTINCT Unit_Key) AS Purchasing_Units,
    COUNT(DISTINCT Modality_Key) AS Modalities,
    COUNT(DISTINCT Status_Key) AS Process_Statuses
FROM dbo.Fact_Procurement;
GO

SELECT
    SUM(CASE WHEN Is_MiPymes = 1 THEN 1 ELSE 0 END) AS MiPyMEs_Processes,
    CAST(100.0 * SUM(CASE WHEN Is_MiPymes = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) AS DECIMAL(10, 2)) AS MiPyMEs_Share_Pct,
    SUM(CASE WHEN Is_MiPymes_Women = 1 THEN 1 ELSE 0 END) AS MiPyMEs_Women_Processes,
    CAST(100.0 * SUM(CASE WHEN Is_MiPymes_Women = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) AS DECIMAL(10, 2)) AS MiPyMEs_Women_Share_Pct,
    SUM(CASE WHEN Is_Green_Purchase = 1 THEN 1 ELSE 0 END) AS Green_Purchase_Processes,
    CAST(100.0 * SUM(CASE WHEN Is_Green_Purchase = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) AS DECIMAL(10, 2)) AS Green_Purchase_Share_Pct,
    SUM(CASE WHEN Is_Joint_Purchase = 1 THEN 1 ELSE 0 END) AS Joint_Purchase_Processes,
    CAST(100.0 * SUM(CASE WHEN Is_Joint_Purchase = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) AS DECIMAL(10, 2)) AS Joint_Purchase_Share_Pct
FROM dbo.Fact_Procurement;
GO

-- 9. DOP median and mean/median ratio.
WITH DOP AS (
    SELECT Estimated_Amount
    FROM dbo.Fact_Procurement
    WHERE Currency = N'DOP'
),
DOP_Median AS (
    SELECT DISTINCT
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY Estimated_Amount) OVER () AS Median_Amount
    FROM DOP
),
DOP_Avg AS (
    SELECT AVG(Estimated_Amount) AS Average_Amount
    FROM DOP
)
SELECT
    DOP_Avg.Average_Amount,
    DOP_Median.Median_Amount,
    CASE
        WHEN DOP_Median.Median_Amount IS NULL OR DOP_Median.Median_Amount = 0 THEN NULL
        ELSE DOP_Avg.Average_Amount / DOP_Median.Median_Amount
    END AS Mean_to_Median_Ratio
FROM DOP_Avg
CROSS JOIN DOP_Median;
GO
