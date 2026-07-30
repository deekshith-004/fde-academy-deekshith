"""
Exercise 2 — PostgreSQL Load & SQL Transformations
Cleaned CSV → shipments_clean table → shipment_kpi_monthly table
"""

from __future__ import annotations
import pandas as pd
from sqlalchemy import create_engine, text

# ─── CONNECTION ───────────────────────────────────────────────────────────────
# Update credentials to match your PostgreSQL setup
DB_URL = "postgresql://fde_user:fde_password_2024@localhost:5432/fde_academy"
engine = create_engine(DB_URL)

# ───  LOAD CLEANED DATA ───────────────────────────────────────────────
print("=" * 60)
print("TASK 1 — LOAD shipments_clean INTO POSTGRESQL")
print("=" * 60)

df = pd.read_csv("shipments_clean.csv", parse_dates=["ship_date"])
print(f"\nPython DataFrame: {len(df)} rows")

# Load into PostgreSQL
df.to_sql(
    "shipments_clean",
    engine,
    if_exists="replace",
    index=False,
    method="multi",
    chunksize=500,
)
print("Load complete.")

# Verify: row count must match
with engine.connect() as conn:
    pg_count = conn.execute(text("SELECT COUNT(*) FROM shipments_clean")).scalar()
    print(f"PostgreSQL row count: {pg_count}")
    match = "✓ MATCH" if pg_count == len(df) else "✗ MISMATCH — check load"
    print(f"Reconciliation: {match}")

    # Spot-check: 5 rows
    print("\nSpot-check (5 rows):")
    result = conn.execute(text("SELECT * FROM shipments_clean LIMIT 5"))
    for row in result:
        print(dict(row._mapping))

# ─── TASK 2: SQL TRANSFORMATION ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("TASK 2 — CREATE shipment_kpi_monthly")
print("=" * 60)

CREATE_KPI = """
DROP TABLE IF EXISTS shipment_kpi_monthly;

CREATE TABLE shipment_kpi_monthly AS
SELECT
    carrier,
    DATE_TRUNC('month', ship_date)              AS ship_month,
    COUNT(*)                                    AS shipment_count,
    ROUND(AVG(freight_cost)::numeric, 2)        AS avg_freight_cost,
    ROUND(
        SUM(CASE WHEN status = 'delivered'
                 THEN 1 ELSE 0 END)::numeric
        / COUNT(*),
        4
    )                                           AS on_time_rate,
    COUNT(*) FILTER (WHERE cost_flag = TRUE)    AS high_cost_shipments
FROM shipments_clean
GROUP BY carrier, DATE_TRUNC('month', ship_date)
ORDER BY ship_month, carrier;
"""

with engine.connect() as conn:
    conn.execute(text(CREATE_KPI))
    conn.commit()
    print("shipment_kpi_monthly created.")

    # Preview the KPI table
    print("\nKPI table preview (first 10 rows):")
    result = conn.execute(text("SELECT * FROM shipment_kpi_monthly LIMIT 10"))
    for row in result:
        print(dict(row._mapping))

# ─── TASK 3: VALIDATE ────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("TASK 3 — VALIDATE TRANSFORMATION")
print("=" * 60)

VALIDATION = """
SELECT
    (SELECT SUM(shipment_count) FROM shipment_kpi_monthly) AS kpi_total,
    (SELECT COUNT(*) FROM shipments_clean)                 AS clean_total,
    (SELECT SUM(shipment_count) FROM shipment_kpi_monthly)
     = (SELECT COUNT(*) FROM shipments_clean)              AS counts_match
"""

with engine.connect() as conn:
    result = conn.execute(text(VALIDATION)).fetchone()
    print(f"\nKPI table total:    {result[0]}")
    print(f"Clean table total:  {result[1]}")
    print(f"Counts match:       {'✓ YES' if result[2] else '✗ NO'}")

    # Manual spot-check: pick DHL in first available month
    print("\nSpot-check — DHL on_time_rate verification:")
    spot = conn.execute(
        text("""
        SELECT
            carrier,
            ship_month,
            on_time_rate                        AS kpi_rate,
            SUM(CASE WHEN status = 'delivered'
                     THEN 1 ELSE 0 END)::float
              / COUNT(*)                        AS direct_rate
        FROM shipments_clean s
        CROSS JOIN (
            SELECT MIN(DATE_TRUNC('month', ship_date)) AS first_month
            FROM shipments_clean WHERE carrier = 'DHL'
        ) m
        WHERE carrier = 'DHL'
          AND DATE_TRUNC('month', ship_date) = m.first_month
        GROUP BY carrier, ship_month
    """)
    ).fetchall()
    for row in spot:
        print(dict(row._mapping))

print("\n✓ Exercise 2 complete. Run exercise3_kpi_report.py next.")
