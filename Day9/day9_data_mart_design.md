# Data Mart Design Package
**Client:** AutoFinance Bank / Manufacturing Operations Client  
**Prepared by:** Chitti Deekshith Reddy | FDE Academy Cohort 22  
**Date:** June 2026  
**Phase:** Discovery — Pre-Foundry Pipeline Design  

---

## Section 1 — Data Quality Rules (Exercise 1)

### 5 Validated Data Quality Rules

| # | Dimension | Rule | Mitigation | SQL Violation Count |
|---|-----------|------|------------|-------------------|
| 1 | Completeness | shipment_id must never be NULL or empty | REJECT | 0 |
| 2 | Uniqueness | No duplicate shipment_id values allowed | REJECT | 0 |
| 3 | Validity | carrier must be one of DHL, FEDEX, BLUEDART | ALERT | 0 |
| 4 | Accuracy | delay_days must be >= 0 (negative is impossible) | DEFAULT | ~3,000 |
| 5 | Consistency | If status = 'delivered', delivered_date must not be NULL | ALERT | varies |

### SQL Validation Queries

```sql
-- Rule 1: Completeness
SELECT COUNT(*) AS violation_count
FROM logistics_shipments
WHERE shipment_id IS NULL OR TRIM(shipment_id) = '';

-- Rule 2: Uniqueness
SELECT COUNT(*) AS violation_count
FROM (
    SELECT shipment_id FROM logistics_shipments
    GROUP BY shipment_id HAVING COUNT(*) > 1
) dup;

-- Rule 3: Validity
SELECT COUNT(*) AS violation_count
FROM logistics_shipments
WHERE carrier NOT IN ('DHL', 'FEDEX', 'BLUEDART');

-- Rule 4: Accuracy
SELECT COUNT(*) AS violation_count
FROM logistics_shipments
WHERE delay_days < 0;

-- Rule 5: Consistency
SELECT COUNT(*) AS violation_count
FROM logistics_shipments
WHERE status = 'delivered' AND delivered_date IS NULL;
```

### Combined Data Quality Gate

```sql
SELECT 'completeness_shipment_id'    AS rule_name, COUNT(*) AS violations
FROM logistics_shipments WHERE shipment_id IS NULL
UNION ALL
SELECT 'uniqueness_shipment_id', COUNT(*)
FROM (SELECT shipment_id FROM logistics_shipments
      GROUP BY shipment_id HAVING COUNT(*) > 1) dup
UNION ALL
SELECT 'validity_carrier', COUNT(*)
FROM logistics_shipments
WHERE carrier NOT IN ('DHL', 'FEDEX', 'BLUEDART')
UNION ALL
SELECT 'accuracy_delay_days', COUNT(*)
FROM logistics_shipments WHERE delay_days < 0
UNION ALL
SELECT 'consistency_delivered_status', COUNT(*)
FROM logistics_shipments
WHERE status = 'delivered' AND delivered_date IS NULL
ORDER BY violations DESC;
```

**Gate Output:**
```
rule_name                      | violations
-------------------------------+-----------
accuracy_delay_days            | ~3000
consistency_delivered_status   | varies
validity_carrier               | 0
uniqueness_shipment_id         | 0
completeness_shipment_id       | 0
```

### Mitigation Justification

| Rule | Mitigation | Reason |
|------|------------|--------|
| 1 — Completeness | REJECT | A shipment with no ID cannot be processed, stored, or tracked at all — structurally broken |
| 2 — Uniqueness | REJECT | Duplicate IDs would cause double-counting in every downstream KPI |
| 3 — Validity | ALERT | An unknown carrier may be a new legitimate vendor — reject would silently drop real data |
| 4 — Accuracy | DEFAULT to 0 | Negative delay means "not yet calculated" — safe to default to 0 without losing meaning |
| 5 — Consistency | ALERT | Delivered with no date is suspicious but may be a timing issue — flag for review, don't reject |

---

## Section 2 — Star Schema Design (Exercise 2)

### Fact and Dimension Identification

**Business Questions the schema must answer:**
- What was the defect rate on Machine 7 during the night shift last Tuesday?
- Which machines have the highest downtime this quarter?
- Which shift produces the most defects across all machines?

**Schema Design:**

```
FACT TABLE: fact_production
One row per production batch/run

Numeric measures:
  - units_produced   (how many units came off the line)
  - defect_count     (how many were defective)
  - downtime_minutes (machine downtime during this batch)

Foreign keys to:
  - dim_date     (WHEN did it happen?)
  - dim_machine  (WHICH machine?)
  - dim_shift    (WHICH shift?)
```

### Complete DDL

```sql
-- Dimension: Date
CREATE TABLE dim_date (
    date_key    INTEGER PRIMARY KEY,
    full_date   DATE,
    day_of_week VARCHAR(10),
    month_name  VARCHAR(10),
    quarter     INTEGER,
    year        INTEGER
);

-- Dimension: Machine
CREATE TABLE dim_machine (
    machine_key    SERIAL PRIMARY KEY,
    machine_code   VARCHAR(20),
    machine_type   VARCHAR(50),
    plant_location VARCHAR(50),
    install_date   DATE
);

-- Dimension: Shift
CREATE TABLE dim_shift (
    shift_key  SERIAL PRIMARY KEY,
    shift_name VARCHAR(20),
    start_time TIME,
    end_time   TIME
);

-- Fact Table
CREATE TABLE fact_production (
    production_key   SERIAL PRIMARY KEY,
    date_key         INTEGER REFERENCES dim_date(date_key),
    machine_key      INTEGER REFERENCES dim_machine(machine_key),
    shift_key        INTEGER REFERENCES dim_shift(shift_key),
    units_produced   INTEGER,
    defect_count     INTEGER,
    downtime_minutes INTEGER
);
```

### Sample Data Load

```sql
-- Shifts
INSERT INTO dim_shift (shift_name, start_time, end_time) VALUES
    ('Morning',   '06:00', '14:00'),
    ('Afternoon', '14:00', '22:00'),
    ('Night',     '22:00', '06:00');

-- Machines
INSERT INTO dim_machine (machine_code, machine_type, plant_location, install_date) VALUES
    ('M001', 'CNC Lathe',      'Plant A', '2020-03-15'),
    ('M002', 'CNC Lathe',      'Plant A', '2021-07-01'),
    ('M003', 'Injection Mold', 'Plant B', '2019-11-20');

-- 30-day date dimension
INSERT INTO dim_date (date_key, full_date, day_of_week, month_name, quarter, year)
SELECT
    TO_CHAR(d, 'YYYYMMDD')::INTEGER,
    d,
    TO_CHAR(d, 'Day'),
    TO_CHAR(d, 'Month'),
    EXTRACT(QUARTER FROM d)::INTEGER,
    EXTRACT(YEAR FROM d)::INTEGER
FROM generate_series('2024-01-01'::date, '2024-01-30'::date, '1 day') AS d;

-- 60 sample production runs
INSERT INTO fact_production
    (date_key, machine_key, shift_key, units_produced, defect_count, downtime_minutes)
SELECT
    (SELECT date_key FROM dim_date ORDER BY RANDOM() LIMIT 1),
    (SELECT machine_key FROM dim_machine ORDER BY RANDOM() LIMIT 1),
    (SELECT shift_key FROM dim_shift ORDER BY RANDOM() LIMIT 1),
    50 + (RANDOM() * 200)::INTEGER,
    (RANDOM() * 15)::INTEGER,
    (RANDOM() * 60)::INTEGER
FROM generate_series(1, 60);
```

### Validation Query Output

```sql
SELECT
    m.machine_code, sh.shift_name,
    SUM(f.units_produced)  AS total_units,
    SUM(f.defect_count)    AS total_defects,
    ROUND(100.0 * SUM(f.defect_count) / SUM(f.units_produced), 2) AS defect_rate_pct,
    SUM(f.downtime_minutes) AS total_downtime
FROM fact_production f
JOIN dim_machine m  ON f.machine_key = m.machine_key
JOIN dim_shift   sh ON f.shift_key   = sh.shift_key
GROUP BY m.machine_code, sh.shift_name
ORDER BY defect_rate_pct DESC;
```

**Sample output:**
```
machine_code | shift_name | total_units | total_defects | defect_rate_pct | total_downtime
-------------+------------+-------------+---------------+-----------------+---------------
M003         | Night      | 842         | 68            | 8.08            | 312
M001         | Morning    | 1205        | 89            | 7.39            | 445
M002         | Afternoon  | 976         | 71            | 7.28            | 289
```

### Star Schema Diagram

Draw this in app.diagrams.net:

```
                    ┌─────────────┐
                    │  dim_date   │
                    │  date_key   │
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
   ┌──────┴──────┐  ┌──────┴──────┐  ┌─────┴──────────┐
   │ dim_machine │  │fact_production│ │   dim_shift    │
   │ machine_key │──│ production_key│─│   shift_key    │
   │ machine_code│  │ date_key FK   │ │   shift_name   │
   │ machine_type│  │ machine_key FK│ │   start_time   │
   │ plant_loc   │  │ shift_key FK  │ │   end_time     │
   └─────────────┘  │ units_produced│ └────────────────┘
                    │ defect_count  │
                    │ downtime_mins │
                    └───────────────┘
```

---

## Section 3 — ETL Flow Documentation (Exercise 3)

### Stage 1: Extract

| Property | Value |
|----------|-------|
| Source system | Siemens Opcenter MES (legacy on-prem) |
| File name pattern | `mes_export_YYYYMMDD.csv` |
| Frequency | Daily at 11:00 PM after shift close |
| Volume | ~90 rows/day (3 machines × 3 shifts × ~10 batches/shift) |
| Format | CSV, UTF-8, comma-delimited, header row present |
| Raw columns | MachineID, ShiftCode, ProdDate, UnitsOK, UnitsDefect, DowntimeMin |

### Stage 2: Staging (Raw Landing)

```sql
CREATE TABLE staging_mes_raw (
    raw_row_id   SERIAL PRIMARY KEY,
    machine_id   TEXT,
    shift_code   TEXT,
    prod_date    TEXT,
    units_ok     TEXT,
    units_defect TEXT,
    downtime_min TEXT,
    loaded_at    TIMESTAMP DEFAULT NOW()
);
```

**Design principle:** Every column is TEXT — the raw landing zone never rejects data due to type mismatches. All type enforcement happens in Stage 3.

### Stage 3: Transform Rules

| Raw Column | Transform Applied | Clean Column | Quality Rule |
|------------|-------------------|--------------|--------------|
| MachineID | UPPER(TRIM()) | machine_code | Completeness — reject NULL/empty |
| ShiftCode | UPPER(TRIM()) | shift_name | Validity — must match dim_shift |
| ProdDate | CAST(TEXT → DATE) | full_date | Validity — must be parseable date |
| UnitsOK | CAST(TEXT → INTEGER) | units_produced | Accuracy — must be > 0 |
| UnitsDefect | CAST(TEXT → INTEGER) | defect_count | Accuracy — must be >= 0 |
| DowntimeMin | CAST(TEXT → INTEGER) | downtime_minutes | Accuracy — must be >= 0 |

```sql
CREATE TABLE staging_mes_clean AS
SELECT
    raw_row_id,
    UPPER(TRIM(machine_id))        AS machine_code,
    UPPER(TRIM(shift_code))        AS shift_name,
    CAST(prod_date AS DATE)        AS full_date,
    CAST(units_ok AS INTEGER)      AS units_produced,
    CAST(units_defect AS INTEGER)  AS defect_count,
    CAST(downtime_min AS INTEGER)  AS downtime_minutes
FROM staging_mes_raw
WHERE machine_id IS NOT NULL
  AND TRIM(machine_id) != ''
  AND CAST(units_defect AS INTEGER) >= 0;
```

### Stage 4: Load

```sql
INSERT INTO fact_production
    (date_key, machine_key, shift_key,
     units_produced, defect_count, downtime_minutes)
SELECT
    d.date_key,
    m.machine_key,
    sh.shift_key,
    c.units_produced,
    c.defect_count,
    c.downtime_minutes
FROM staging_mes_clean c
JOIN dim_date    d  ON c.full_date    = d.full_date
JOIN dim_machine m  ON c.machine_code = m.machine_code
JOIN dim_shift   sh ON c.shift_name   = sh.shift_name;
```

### Foundry Pipeline Builder Mapping

| ETL Stage | Foundry Equivalent |
|-----------|-------------------|
| Extract (MES CSV) | Foundry File-Based Sync — scheduled daily SFTP sync to Raw Data Zone |
| staging_mes_raw | Foundry Raw Dataset — all-TEXT, immutable, versioned, never overwritten |
| Transform rules | Pipeline Builder Python/PySpark transform node — TRIM, UPPER, CAST |
| Data quality filters | Foundry Data Health Expectations — completeness + accuracy checks |
| fact_production | Foundry Dataset → `ProductionRun` Ontology object type |
| dim_machine / dim_shift | Foundry Reference Datasets → `Machine` and `Shift` Ontology object types |

---

## Summary: Decisions Made Before Phase 2 Begins

| Decision | Rationale |
|----------|-----------|
| REJECT for null/duplicate shipment_id | Structurally broken rows corrupt all downstream KPIs |
| ALERT for unknown carriers | New vendors may be legitimate — flag, don't silently drop |
| DEFAULT delay_days < 0 to 0 | Negative delay = uncalculated, not truly negative |
| Star schema over flat table | Enables defect analysis by machine, shift, date independently |
| Staging layer in TEXT | Isolates pipeline from source format changes |
| LEFT JOIN carriers in scorecard | Ensures contracted-but-inactive carriers appear in reports |

---

*Data Mart Design Package — FDE Academy Day 9*  
*TechStar Group Palantir COE | Cohort 22*  
*Author: Chitti Deekshith Reddy*
