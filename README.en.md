# warehouse-sector-externo

*[Versión en español](README.md)*

A DuckDB warehouse for the macroeconomic panel of `sector-externo-cr-eeuu` (a
private repository while the academic review concludes), with **proof that moving
the data into SQL did not change a single number**.

```bash
pip install duckdb pandas openpyxl
python 07_pruebas.py       # rebuilds everything from scratch and verifies it
```

## Why it exists

A wide panel —one column per variable— works for estimation but not for querying:
adding a series means altering the table. Here the data is stored long, in a star
schema, and **every aggregation is derived in SQL from the finest grain
available**.

| Table | Rows | What it is |
|---|---:|---|
| `dim_serie` | 12 | the series, with frequency, provider and original title |
| `dim_fecha` | 132 | calendar with year, quarter, month and year-end |
| `fact_observacion` | 1,408 | one row per series and date |
| `fact_observacion_diaria` | 5,491 | the daily grain of the FRED series |

## The proof

`03_reconciliar.py` compares the 18 series against the validated CSVs from the
original project. Maximum tolerated difference: `1e-9`.

```
VEREDICTO: el warehouse reproduce el panel validado, dato por dato.
(VERDICT: the warehouse reproduces the validated panel, value by value.)
```

## Two things the reconciliation uncovered

**Averaging twice is not the same as averaging once.** `t2y` and `dolar` are
daily series. Aggregating day → month → quarter gives a different result from
day → quarter, because months have different numbers of days. That is why the
warehouse keeps the daily grain and derives the quarter from it: the error showed
up in the second decimal and is only visible when compared against the source.

**A carried-forward value is not a data point.** `pib_eeuu` (US GDP) is quarterly
and the monthly panel repeats it forward. That is not stored: it is rebuilt with a
`JOIN` against `DATE_TRUNC('quarter', ...)`. Storing derived values is how a
warehouse gets corrupted.

## Contents

| File | What it does |
|---|---|
| `01_esquema.sql` | star schema, with a drop order that respects dependencies |
| `02_cargar.py` | wide panel → long, plus the daily FRED grain |
| `03_reconciliar.py` | compares the 18 series against the validated CSVs |
| `04_crudo_acumulado.py` | loads the year-to-date data **untouched**, as the Central Bank publishes it |
| `05_transformar.sql` | de-accumulation, year-over-year change and moving average, with window functions |
| `06_calidad.sql` | the 7 checks |
| `07_pruebas.py` | rebuilds from scratch and asserts everything. Exits with code 1 on failure |

## De-accumulation, the case that justifies all of this

The Central Bank of Costa Rica publishes the trade balance and exports **as
year-to-date totals**: January holds January, February holds January + February.
The monthly flow is the difference from the previous month *of the same year*; in
January there is no previous month, so the year-to-date value is the flow.

```sql
valor - COALESCE(
    LAG(valor) OVER (PARTITION BY serie_id, YEAR(fecha) ORDER BY fecha),
    0
) AS flujo
```

One expression. And it reconciles with the Python pipeline to `5.7e-14`.

## The data quality engine

Seven checks that return **the rows that fail**, not a boolean: gaps in the
series, duplicates, nulls, orphan series, improbable jumps, de-accumulation
mismatches and stale series.

On this data: **0 errors and 3 warnings**, and all three warnings are real
macroeconomic shocks, not data-entry errors.

| Series | Date | Detail |
|---|---|---|
| `ffr` | 2020-03 | −0.93 = 5.4 standard deviations — the Fed's emergency cut |
| `ipi_eeuu` | 2020-04 | −12.85 = 8.7 standard deviations — COVID industrial collapse |
| `tpm` | 2022-08 | +1.74 = 5.0 standard deviations — the Central Bank's aggressive hike |

Flagging them is the right behavior: telling a real shock from a data error is the
job of someone who knows the series, not of the check.

## Data

Public: FRED (Federal Reserve Bank of St. Louis) and the Central Bank of Costa
Rica's economic indicators portal. None of it is restricted.

## dbt layer

The transformations also ship as a dbt project in [`dbt/`](dbt/): same results
—verified with `EXCEPT` in both directions, zero rows of difference— but with
lineage, documentation and the tests running inside the graph instead of in a
separate script.

```bash
cd dbt && dbt build      # PASS 23 · WARN 1 · ERROR 0
```
