# Data

The original DGCP CSV files are intentionally not committed because the full source/processed files are hundreds of megabytes and are not necessary for code review.

For immediate testing, use the included sample:

```text
data/sample/dgcp_secp_sample_1000.csv
```

To reproduce the full analysis, obtain the same official DGCP source used in the project and place it at:

```text
data/raw/dgcp_secp_2015_2026.csv
```

The ETL output is written to:

```text
data/processed/dgcp_secp_cleaned.csv
```

The source data is preserved conceptually through the pipeline: the ETL creates a new cleaned dataset rather than overwriting the raw file.
