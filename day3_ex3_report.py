"""
AutoFinance Bank - Daily Shipment Operations Report
FDE Academy Day 3 Exercise 3

Usage:
    python day3_ex3_report.py

Outputs:
    - Console: formatted KPI report
    - shipments_summary.csv: per-carrier aggregated KPIs
    - route_report.csv: top routes by volume
"""

import pandas as pd
from pathlib import Path

INPUT_FILE = "shipments_clean.csv"
SUMMARY_CSV = "shipments_summary.csv"
ROUTES_CSV = "route_report.csv"


# ■■ TASK 2A: compute_carrier_kpis ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
def compute_carrier_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-carrier KPIs from the cleaned shipments DataFrame.
    """
    if df.empty:
        return pd.DataFrame(
            columns=[
                "carrier",
                "total_shipments",
                "delivered",
                "in_transit",
                "otif_pct",
                "avg_delay_days",
                "max_delay_days",
                "total_revenue",
                "avg_cost_per_ship",
            ]
        )

    grouped = df.groupby("carrier")
    kpi_records = []

    for carrier, group in grouped:
        total_ships = len(group)
        # Match case-insensitively or exactly as per raw data values
        delivered_count = int(group["status"].str.lower().eq("delivered").sum())
        in_transit_count = int(group["status"].str.lower().eq("in_transit").sum())

        otif_mask = (group["delay_days"] == 0) & (
            group["status"].str.lower() == "delivered"
        )
        otif_pct = (
            round((otif_mask.sum() / total_ships) * 100, 1) if total_ships > 0 else 0.0
        )

        avg_delay = (
            round(float(group["delay_days"].mean()), 1) if total_ships > 0 else 0.0
        )
        max_delay = int(group["delay_days"].max()) if total_ships > 0 else 0

        total_rev = round(float(group["cost_usd"].sum()), 2)
        avg_cost = round(float(group["cost_usd"].mean()), 2) if total_ships > 0 else 0.0

        kpi_records.append(
            {
                "carrier": carrier,
                "total_shipments": total_ships,
                "delivered": delivered_count,
                "in_transit": in_transit_count,
                "otif_pct": otif_pct,
                "avg_delay_days": avg_delay,
                "max_delay_days": max_delay,
                "total_revenue": total_rev,
                "avg_cost_per_ship": avg_cost,
            }
        )

    kpi_df = pd.DataFrame(kpi_records)
    return kpi_df.sort_values(by="total_shipments", ascending=False).reset_index(
        drop=True
    )


# ■■ TASK 2B: compute_route_report ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
def compute_route_report(df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """
    Compute a route-level report grouped by (origin, destination) pair.
    """
    if df.empty:
        return pd.DataFrame(
            columns=[
                "route",
                "shipment_count",
                "avg_delay_days",
                "total_revenue",
                "most_used_carrier",
            ]
        )

    grouped = df.groupby(["origin", "destination"])
    route_records = []

    for (origin, destination), group in grouped:
        route_str = f"{origin} -> {destination}"
        shipment_count = len(group)
        avg_delay = round(float(group["delay_days"].mean()), 1)
        total_rev = round(float(group["cost_usd"].sum()), 2)

        most_used_carrier = (
            group["carrier"].value_counts().idxmax()
            if not group["carrier"].empty
            else "Unknown"
        )

        route_records.append(
            {
                "route": route_str,
                "shipment_count": shipment_count,
                "avg_delay_days": avg_delay,
                "total_revenue": total_rev,
                "most_used_carrier": most_used_carrier,
            }
        )

    route_df = pd.DataFrame(route_records)
    return (
        route_df.sort_values(by="shipment_count", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )


# ■■ TASK 2C: print_console_report ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
def print_console_report(
    df: pd.DataFrame, carrier_kpis: pd.DataFrame, route_report: pd.DataFrame
) -> None:
    """
    Print a formatted operations report matching the required design layout exactly.
    """
    total_shipments = len(df)
    total_revenue = df["cost_usd"].sum() if total_shipments > 0 else 0.0
    avg_delay = df["delay_days"].mean() if total_shipments > 0 else 0.0

    otif_condition = (df["delay_days"] == 0) & (df["status"].str.lower() == "delivered")
    overall_otif = (
        (otif_condition.sum() / total_shipments * 100) if total_shipments > 0 else 0.0
    )

    # [1] Header Block
    print(f"=== AutoFinance Bank – Daily Shipment Report [2024-01-20] ===")
    print(
        f"Total Shipments: {total_shipments} | Total Revenue: ${total_revenue:,.2f} | Overall OTIF: {overall_otif:.1f}% | Avg Delay: {avg_delay:.1f} days"
    )

    # [3] Carrier KPIs
    print("\n=== Carrier KPIs ===")
    print("Carrier Shipments Delivered OTIF% Avg Delay Revenue")
    for _, row in carrier_kpis.iterrows():
        print(
            f"{row['carrier']} {int(row['total_shipments'])} {int(row['delivered'])} {row['otif_pct']:.1f}% {row['avg_delay_days']:.1f} ${row['total_revenue']:.2f}"
        )

    # [4] Top Routes
    print("=== Top Routes ===")
    print("Route Count Avg Delay Revenue")
    for _, row in route_report.iterrows():
        print(
            f"{row['route']} {int(row['shipment_count'])} {row['avg_delay_days']:.1f} ${row['total_revenue']:.2f}"
        )

    # [5] Flagged Shipments List (delay_days > 3)
    print("■■ Flagged Shipments (delay > 3 days):")
    flagged_df = df[df["delay_days"] > 3]
    if flagged_df.empty:
        print("No critical shipping delays flagged.")
    else:
        for _, row in flagged_df.iterrows():
            print(
                f"{row['shipment_id']} {row['carrier']} {row['status']} delay={int(row['delay_days'])} cost=${row['cost_usd']:.2f}"
            )


# ■■ TASK 3: Main entry point ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
def main() -> None:
    """Run the full report generation pipeline."""
    if not Path(INPUT_FILE).exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE)

    # Validate Quality Gates
    required_cols = {"shipment_id", "carrier", "status", "delay_days", "cost_usd"}
    missing = required_cols - set(df.columns)
    if missing:
        print(f"ERROR: Missing required columns: {missing}")
        return

    if len(df) == 0:
        print("ERROR: Input file contains no data rows")
        return

    # Compute Summaries
    carrier_kpis = compute_carrier_kpis(df)
    route_report = compute_route_report(df, top_n=5)

    # Save CSV outputs
    carrier_kpis.to_csv(SUMMARY_CSV, index=False)
    route_report.to_csv(ROUTES_CSV, index=False)

    # Print clean report to console
    print_console_report(df, carrier_kpis, route_report)


if __name__ == "__main__":
    main()
