# DAX measure notes

The Power BI file contains a dedicated `_Measures` table for DAX measures.

The report currently includes measures such as `Total Procesos`, `Monto Total Estimado`, `Monto Promedio`, and `% Procesos MiPyMEs`.

For executive monetary KPIs, the safest definitions for this dataset are DOP-only because the project does not include historical FX conversion.

## Core measures

```DAX
Total Procesos =
DISTINCTCOUNT(Fact_Procurement[Process_Code])
```

```DAX
Monto Total Estimado =
CALCULATE(
    SUM(Fact_Procurement[Estimated_Amount]),
    Fact_Procurement[Currency] = "DOP"
)
```

```DAX
Monto Promedio =
CALCULATE(
    AVERAGE(Fact_Procurement[Estimated_Amount]),
    Fact_Procurement[Currency] = "DOP"
)
```

```DAX
Monto Mediano =
CALCULATE(
    MEDIAN(Fact_Procurement[Estimated_Amount]),
    Fact_Procurement[Currency] = "DOP"
)
```

```DAX
% Procesos =
DIVIDE(
    CALCULATE(
        DISTINCTCOUNT(Fact_Procurement[Process_Code]),
        Fact_Procurement[Currency] = "DOP"
    ),
    [Total Procesos]
)
```

```DAX
% Procesos MiPyMEs =
DIVIDE(
    CALCULATE(
        DISTINCTCOUNT(Fact_Procurement[Process_Code]),
        Fact_Procurement[Is_MiPymes] = TRUE()
    ),
    [Total Procesos]
)
```

## Additional portfolio metrics

These can be added to the `_Measures` table when you want the Power BI report to expose the same analytical story already present in Python.

```DAX
Procesos MiPyMEs =
CALCULATE(
    DISTINCTCOUNT(Fact_Procurement[Process_Code]),
    Fact_Procurement[Is_MiPymes] = TRUE()
)
```

```DAX
Procesos MiPyMEs Mujeres =
CALCULATE(
    DISTINCTCOUNT(Fact_Procurement[Process_Code]),
    Fact_Procurement[Is_MiPymes_Women] = TRUE()
)
```

```DAX
Procesos Compra Verde =
CALCULATE(
    DISTINCTCOUNT(Fact_Procurement[Process_Code]),
    Fact_Procurement[Is_Green_Purchase] = TRUE()
)
```

```DAX
Procesos Compra Conjunta =
CALCULATE(
    DISTINCTCOUNT(Fact_Procurement[Process_Code]),
    Fact_Procurement[Is_Joint_Purchase] = TRUE()
)
```

> These formulas are documented portfolio measures. Validate field names in the current Power BI model before adding them manually.

## Reconciliation target

For the full cleaned dataset, Python and SQL should reconcile approximately to:

- **DOP process count:** 610,090
- **DOP total:** RD$2,995,095,263,307.73
- **DOP average:** RD$4,909,267.92
- **DOP median:** RD$133,877.04
- **DOP share:** 99.95%

The amount is a sum of source records where `Currency = "DOP"`; it is **not** a cross-currency FX-converted total.
