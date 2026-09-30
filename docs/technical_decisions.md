# Technical Decisions

This document explains the important design choices in the project so a reviewer can understand not only **what** was built, but **why** it was built that way.

## 1. Problem framing

The source data is useful for procurement analysis, but raw records should not be treated as analysis-ready by default. The pipeline therefore separates:

```text
source inspection → quality rules → transformation → modeled data → reporting
```

The goal is reproducibility and traceability, not simply producing a visually attractive dashboard.

## 2. Why the cleaning rule removes only specific monetary anomalies

The ETL removes:

- negative estimated amounts;
- null estimated amounts;
- estimated amounts greater than or equal to 100 billion source-currency units.

Zero-valued amounts are retained because zero and missing are different states. The notebook quantifies these cases before and after cleaning so the exclusion decision can be reviewed.

The `100B` threshold is a project-specific source-quality rule identified during profiling. It is **not** a universal accounting rule and should not be interpreted as one.

## 3. Why Python and SQL are both used

Python is responsible for source-oriented work:

- profiling;
- cleaning;
- transformation;
- descriptive analytical metrics in the notebook;
- unit tests.

SQL Server is responsible for structured storage and relational modeling:

- staging;
- dimensions;
- fact table;
- relational integrity checks;
- reconciliation queries.

Power BI then consumes the modeled layer for interactive reporting.

This separation mirrors a simple analytics pipeline without introducing unnecessary orchestration infrastructure for the scope of the portfolio project.

## 4. Why a star schema

The fact table is at the grain of **one procurement process record**. Descriptive attributes are separated into dimensions so the fact table can focus on process-level measures and foreign keys.

```text
             Dim_Purchasing_Unit
                      │
                      │
Dim_Process_Status ─ Fact_Procurement ─ Dim_Modality
```

The model remains a star schema after the repository cleanup because the cardinality pattern is still:

```text
Dimension (1) ────────< Fact (many)
```

`_Measures` is a Power BI calculation table and is intentionally disconnected from the relational model. `Staging_Procurement` is a database ingestion layer and is intentionally outside the reporting star.

### Why no Date dimension?

The current model stores `Year`, `Month`, and `Quarter` on the fact table. This keeps the model compact and matches the current reporting needs. A future date dimension would make sense for richer time-intelligence features, but adding one now would require changing the existing Power BI model without a demonstrated requirement.

## 5. Why there is no FX conversion

The source contains multiple currency codes. Historical exchange rates are not part of this project, so converting all amounts to DOP would require an additional data source and a documented conversion methodology.

Instead:

```text
Operational currency analysis → preserve source currency
Executive monetary KPI        → filter Currency = DOP
```

This is more defensible than silently adding an FX assumption.

## 6. Why analytical metrics live in the notebook

The portfolio keeps analytical metric calculations in `notebooks/01_initial_exploration.ipynb` rather than adding a separate `metrics.py` module. The notebook is the exploratory/analytical layer, so keeping the calculations beside the profiling evidence makes the reasoning easier for a reviewer to follow and avoids creating a Python file whose only role would be to provide notebook helpers.

The production boundary remains clear:

- `src/etl.py` owns reusable source cleaning/transformation logic;
- the notebook owns exploratory statistics and descriptive business metrics;
- `src/load_to_db.py` owns database loading and schema checks;
- SQL owns the relational model and database-side validation.

## 7. Reproducibility decisions

The repository follows a few simple rules:

- the notebook and ETL share the same cleaning function;
- the SQL loader uses environment variables instead of a machine-specific server name;
- the loader validates the target tables and staging columns before changing staging;
- staging is truncated before a default reload, so rerunning the loader does not silently duplicate the staging dataset;
- the loader reconciles the final staging row count with the rows read from the processed CSV;
- the full raw/processed CSVs are excluded from Git because of size;
- a 1,000-row sample is included so a reviewer can run the project immediately;
- tests cover both ETL transformations and analytical metrics.

## 8. Local SQL Server configuration

`src/load_to_db.py` loads a local `.env` file using `python-dotenv`. The connection is parameterized through:

```text
SQL_SERVER
SQL_DATABASE
SQL_DRIVER
SQL_TRUSTED_CONNECTION
SQL_ENCRYPT
SQL_TRUST_SERVER_CERTIFICATE
```

The repository commits only `.env.example`; the real `.env` is ignored by Git. The default example targets a local SQL Server installation using Windows authentication and the Microsoft ODBC Driver 18. For hosted or production environments, the encryption and certificate settings should be adjusted to the organization's security requirements.

## 9. Interpretation boundaries

The project is intentionally descriptive.

For example, `DIRIGIDO_MIPYMES = True` means that the source record is marked as directed to MiPyMEs. It does not by itself establish final award outcome, supplier identity, or economic impact.

Similarly, monetary totals are estimated amounts reported by the source and should not automatically be interpreted as executed expenditure.

## 10. What a future production version could add

A larger production implementation could introduce:

- orchestration and scheduled refresh;
- a dedicated date dimension;
- historical FX conversion;
- automated CI/CD;
- data lineage and metadata documentation;
- stronger database constraints where source semantics justify them;
- incremental loading instead of full staging reloads.

Those are intentionally outside the current portfolio scope.
