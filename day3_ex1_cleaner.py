"""
AutoFinance Bank - Shipment Data Quality Cleaner
FDE Academy Day 3 Exercise 1

Usage:
    python day3_ex1_cleaner.py
"""

import pandas as pd
import re
from datetime import datetime
from pathlib import Path

INPUT_FILE = (
    "shipments_raw.csv"
    if Path("shipments_raw.csv").exists()
    else "../fde-linux-lab/scripts/shipments_raw.csv"
)
CLEAN_OUTPUT = "shipments_clean.csv"
REJECTED_OUTPUT = "shipments_rejected.csv"


def validate_email(email: str) -> bool:
    """Validate email structure using a standard regex pattern."""
    if pd.isna(email) or not isinstance(email, str):
        return False
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email.strip()))


def validate_row(row: pd.Series) -> str:
    """
    Validates a single shipment row against 5 core business quality rules.
    Returns a semi-colon joined string of failed rules, or an empty string if valid.
    """
    errors = []

    # Rule 1: Missing critical identifier
    if pd.isna(row.get("shipment_id")) or str(row.get("shipment_id")).strip() == "":
        errors.append("MISSING_SHIPMENT_ID")

    # Rule 2: Invalid carrier contact email
    if not validate_email(row.get("carrier_email")):
        errors.append("INVALID_EMAIL")

    # Rule 3: Negative or extreme outlier financial bounds
    try:
        cost = float(row.get("cost_usd", 0))
        if cost < 0 or cost > 10000:
            errors.append("INVALID_COST")
    except (ValueError, TypeError):
        errors.append("INVALID_COST")

    # Rule 4: Out-of-bounds future delivery tracking timestamps
    try:
        delivery_date_str = str(row.get("est_delivery")).strip()
        # Parse standard YYYY-MM-DD format
        delivery_date = datetime.strptime(delivery_date_str, "%Y-%m-%d").date()
        if delivery_date > datetime.now().date():
            errors.append("FUTURE_DELIVERY_DATE")
    except (ValueError, TypeError):
        errors.append("INVALID_DELIVERY_DATE")

    # Rule 5: Negative tracking latency boundaries
    try:
        delay = int(row.get("delay_days", 0))
        if delay < 0:
            errors.append("NEGATIVE_DELAY")
    except (ValueError, TypeError):
        errors.append("INVALID_DELAY")

    return ";".join(errors)


def clean_shipments() -> dict:
    """
    Processes the raw shipments dataset. Splits rows into clean and rejected,
    and applies standard whitespace normalization.
    """
    # Fallback to create sample raw data if file isn't present
    if not Path(INPUT_FILE).exists():
        print(f"Creating mock raw dataset for validation testing...")
        mock_data = {
            "shipment_id": ["SH007", "SH008", "SH009", "", "SH010"],
            "carrier": ["DHL", "DHL", "DHL", "FEDEX", "FEDEX"],
            "status": [
                "delivered",
                "delivered",
                "in_transit",
                "delivered",
                "in_transit",
            ],
            "carrier_email": [
                "ops@dhl.com",
                "ops@dhl.com",
                "ops@dhl.com",
                "bad-email",
                "support@fedex.com",
            ],
            "origin": ["Mumbai", "Mumbai", "Delhi", "Chennai", "Chennai"],
            "destination": ["Delhi", "Delhi", "Mumbai", "Bangalore", "Bangalore"],
            "est_delivery": [
                "2024-01-15",
                "2024-01-16",
                "2024-01-20",
                "2024-01-18",
                "2024-01-19",
            ],
            "delay_days": [0, 0, 3, 0, 5],
            "cost_usd": [400.00, 450.00, 410.00, 180.50, 88.75],
        }
        pd.DataFrame(mock_data).to_csv("shipments_raw.csv", index=False)
        raw_path = "shipments_raw.csv"
    else:
        raw_path = INPUT_FILE

    df = pd.read_csv(raw_path)

    # Text Field Normalization Layer (Strip leading/trailing whitespaces)
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].astype(str).str.strip()

    # Apply validation rules engine row by row
    df["rejection_reasons"] = df.apply(validate_row, axis=1)

    # Split dataset based on data quality gate status
    clean_mask = df["rejection_reasons"] == ""
    clean_df = df[clean_mask].drop(columns=["rejection_reasons"])
    rejected_df = df[~clean_mask]

    # Save output artifacts
    clean_df.to_csv(CLEAN_OUTPUT, index=False)
    rejected_df.to_csv(REJECTED_OUTPUT, index=False)

    summary = {
        "total_count": len(df),
        "clean_count": len(clean_df),
        "rejected_count": len(rejected_df),
    }

    print("\n=== Data Quality Report ===")
    for key, value in summary.items():
        print(f"{key:<25} {value}")
    print(
        f"shipments_clean.csv - {summary['clean_count']} clean rows with normalised fields"
    )
    print(
        f"shipments_rejected.csv - {summary['rejected_count']} rejected rows with rejection_reasons"
    )

    return summary


if __name__ == "__main__":
    clean_shipments()
