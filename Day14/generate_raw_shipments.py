"""
Run this FIRST to generate raw_shipments.csv with realistic dirty data.
"""

import pandas as pd
import numpy as np
import random
from datetime import date, timedelta

random.seed(42)
np.random.seed(42)

carriers = ["DHL", "FEDEX", "BLUEDART"]
origins = ["Mumbai", "Chennai", "Pune", "Delhi", "Hyderabad"]
dests = ["Delhi", "Bangalore", "Mumbai", "Chennai", "Pune"]

# Dirty status variants to inject
status_pool = [
    "delivered",
    "Delivered",
    "DELIVERED",
    "in_transit",
    "in-transit",
    "In Transit",
    "IN_TRANSIT",
    "delayed",
    "Delayed",
    "DELAYED",
    "pending",
    "Pending",
    None,  # missing
    "",  # empty string
]

rows = []
for i in range(1, 1001):
    sid = f"SH{i:05d}"
    # inject ~2% duplicates
    if random.random() < 0.02 and i > 10:
        sid = f"SH{random.randint(1, i - 1):05d}"

    carrier = random.choice(carriers)
    origin = random.choice(origins)
    dest = random.choice([d for d in dests if d != origin])

    # ~3% bad dates, ~2% missing shipment_id
    if random.random() < 0.02:
        sid = None
    raw_date = (date(2024, 1, 1) + timedelta(days=random.randint(0, 179))).strftime(
        "%Y-%m-%d"
    )
    if random.random() < 0.03:
        raw_date = "not-a-date"

    status = random.choice(status_pool)

    # freight cost — ~1% negative, ~1% above 99th pct (outliers)
    cost = round(random.uniform(50, 500), 2)
    if random.random() < 0.01:
        cost = round(random.uniform(-50, -1), 2)
    if random.random() < 0.01:
        cost = round(random.uniform(2000, 5000), 2)

    rows.append([sid, carrier, raw_date, status, origin, dest, cost])

df = pd.DataFrame(
    rows,
    columns=[
        "shipment_id",
        "carrier",
        "ship_date",
        "status",
        "origin",
        "destination",
        "freight_cost",
    ],
)
df.to_csv("raw_shipments.csv", index=False)
print(f"Generated raw_shipments.csv — {len(df)} rows")
