# Power BI report

`dgcp_procurement_dashboard.pbix` is the interactive reporting layer of the project.

## Model represented in Power BI

```text
Dim_Purchasing_Unit ─┐
Dim_Modality ────────┼── Fact_Procurement
Dim_Process_Status ──┘

_Measures  ← disconnected DAX measure table
```

The SQL staging table is not loaded as a reporting dimension, and `_Measures` is a Power BI calculation table rather than a relational dimension.

## Report role

The dashboard is intended to expose descriptive procurement KPIs and allow filtering by year, modality, status, purchasing unit, and related process attributes.

For monetary reporting, use the DOP-only measures documented in [`DAX_MEASURES.md`](DAX_MEASURES.md) unless a historical FX layer is introduced.
