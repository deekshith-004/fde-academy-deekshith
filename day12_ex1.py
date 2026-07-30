"""
Exercise 1 — Python Cleaning & Data Quality Report
Raw Shipments CSV → Cleaned DataFrame + DQ Report
"""

from __future__ import annotations
import pandas as pd

# ─── TASK 1: PROFILE THE RAW FILE ────────────────────────────────────────────

df_raw = pd.read_csv("raw_shipments.csv")

print("=" * 20)
print("TASK 1 — RAW FILE PROFILE")
print("=" * 20)

# Shape and dtypes
print(f"\nShape: {df_raw.shape}  ({df_raw.shape[0]} rows, {df_raw.shape[1]} cols)")
print("\nColumn dtypes:")
print(df_raw.dtypes)

# Null counts per column
print("\nNull counts per column:")
print(df_raw.isnull().sum())

# Unique status values with counts (dropna=False shows NaN too)
print("\nStatus value_counts (raw, including NaN):")
print(df_raw["status"].value_counts(dropna=False))

# Duplicate shipment_id count
dup_count = df_raw.duplicated(subset=["shipment_id"]).sum()
print(f"\nDuplicate shipment_id rows: {dup_count}")

# Min/max ship_date as raw strings (no parsing yet)
print(f"\nship_date raw min: {df_raw['ship_date'].min()}")
print(f"ship_date raw max: {df_raw['ship_date'].max()}")

# ─── TASK 2: CLEANING RULES ──────────────────────────────────────────────────

print("\n" + "=" * 60)
print("TASK 2 — CLEANING LOG")
print("=" * 60)

df = df_raw.copy()
cleaning_log: list[str] = []

# Standardise status — strip whitespace + lowercase
df["status"] = df["status"].str.strip().str.lower()

# Map all observed variants to canonical set
status_map = {
    "delivered": "delivered",
    "in transit": "in_transit",
    "in-transit": "in_transit",
    "in_transit": "in_transit",
    "delayed": "delayed",
    "pending": "pending",
    "": None,  # empty string → treat as null
}
df["status"] = df["status"].replace(status_map)
unique_after = df["status"].value_counts(dropna=False)
msg = f"Rule 1 — status normalised to {unique_after.index.tolist()}"
cleaning_log.append(msg)
print(f"\n{msg}")
print(unique_after)

#  Parse ship_date — coerce bad values to NaT, log failures
before_parse = len(df)
df["ship_date"] = pd.to_datetime(df["ship_date"], errors="coerce")
bad_dates = df["ship_date"].isnull().sum() - df_raw["ship_date"].isnull().sum()
msg = f"Rule 2 — {bad_dates} rows failed date parse (set to NaT)"
cleaning_log.append(msg)
print(f"\n{msg}")

# Drop rows with missing shipment_id or unparseable ship_date
before = len(df)
df = df.dropna(subset=["shipment_id", "ship_date"])
dropped_key_date = before - len(df)
msg = f"Rule 3 — Dropped {dropped_key_date} rows: missing shipment_id or bad ship_date"
cleaning_log.append(msg)
print(f"{msg}")

#  Drop duplicate shipment_id — keep first occurrence
before = len(df)
df = df.drop_duplicates(subset=["shipment_id"], keep="first")
dropped_dups = before - len(df)
msg = f"Rule 4 — Dropped {dropped_dups} duplicate shipment_id rows (kept first)"
cleaning_log.append(msg)
print(f"{msg}")

#  Flag (don't drop) freight_cost outliers above 99th percentile
p99 = df["freight_cost"].quantile(0.99)
df["cost_flag"] = df["freight_cost"] > p99
flagged = df["cost_flag"].sum()
msg = f"Rule 5 — Flagged {flagged} rows as cost outliers (freight_cost > £{p99:.2f})"
cleaning_log.append(msg)
print(f"{msg}")

print(f"\nCleaned DataFrame shape: {df.shape}")
print(f"\nFull cleaning log:")
for i, entry in enumerate(cleaning_log, 1):
    print(f"  {i}. {entry}")

# ─── TASK 3: AUTOMATED DATA QUALITY REPORT ───────────────────────────────────


def data_quality_report(df: pd.DataFrame) -> dict:
    report: dict = {}

    report["row_count"] = len(df)

    # Null rates — rounded to 4dp per column
    report["null_rates"] = {
        col: round(df[col].isnull().mean(), 4) for col in df.columns
    }

    # Duplicate keys
    report["duplicate_keys"] = int(df.duplicated(subset=["shipment_id"]).sum())

    # Negative costs
    report["negative_costs"] = int((df["freight_cost"] < 0).sum())

    # PASS: duplicate_keys == 0, negative_costs == 0,
    #        max null rate across all columns < 0.05
    max_null_rate = max(report["null_rates"].values())
    report["max_null_rate"] = round(max_null_rate, 4)
    report["PASS"] = (
        report["duplicate_keys"] == 0
        and report["negative_costs"] == 0
        and max_null_rate < 0.05
    )

    return report


print("\n" + "=" * 60)
print("TASK 3 — DATA QUALITY REPORT")
print("=" * 60)

report = data_quality_report(df)
print(f"\nrow_count:        {report['row_count']}")
print(f"duplicate_keys:   {report['duplicate_keys']}")
print(f"negative_costs:   {report['negative_costs']}")
print(f"max_null_rate:    {report['max_null_rate']}")
print(f"PASS:             {report['PASS']}")
print(f"\nNull rates per column:")
for col, rate in report["null_rates"].items():
    flag = " ⚠️" if rate >= 0.05 else " ✓"
    print(f"  {col:<20} {rate:.4f}{flag}")

# Save cleaned file for Exercise 2
df.to_csv("shipments_clean.csv", index=False)
print(f"\n✓ Saved shipments_clean.csv — {len(df)} rows ready for PostgreSQL load")
