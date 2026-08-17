# Data Discovery Report
**Client:** AutoFinance Bank — Logistics Operations  
**Prepared by:** Chitti Deekshith Reddy | FDE Academy Cohort 22  
**Date:** June 2026  
**Table:** `logistics_shipments` | Source: Carrier Operations Database  

---

## Executive Summary

The `logistics_shipments` table contains **100,000 shipment records** spanning
January–June 2024 across 3 carriers and 6 Indian cities. No NULL values were
found in any business-critical column. However, **~5,000 rows contain
impossible numeric values** that must be resolved before any pipeline or
dashboard is built on this data.

---

## Exercise 1 — Data Profile

| Metric | Value |
|--------|-------|
| Total rows | 100,000 |
| Date range | 2024-01-01 → 2024-06-29 |
| Carriers | DHL, FEDEX, BLUEDART |
| Status values | delivered, in_transit, delayed, pending |
| Origin cities | Mumbai, Chennai, Pune, Delhi, Hyderabad, Bangalore |
| Destination cities | Delhi, Bangalore, Mumbai, Chennai, Pune, Hyderabad |
| NULL values (any column) | **0** |

### Categorical Distribution

| Carrier | Shipment Count |
|---------|---------------|
| DHL | ~40,000 |
| FEDEX | ~40,000 |
| BLUEDART | ~20,000 |

| Status | Count |
|--------|-------|
| delivered | ~25,000 |
| in_transit | ~25,000 |
| delayed | ~25,000 |
| pending | ~25,000 |

### Numeric Ranges

| Column | Min | Max | Avg |
|--------|-----|-----|-----|
| cost_usd | 0.00 ⚠️ | ~499.99 | ~275.00 |
| delay_days | -1 ⚠️ | 10 | ~4.5 |
| weight_kg | ~1.00 | ~500.00 | ~250.00 |

---

## Exercise 2 — Operational KPIs

| KPI | Result |
|-----|--------|
| Total delayed shipments | ~25,000 |
| OTIF % (on-time delivery) | ~24% |
| Carrier with highest avg delay | DHL or FEDEX (varies by seed) |
| Highest volume route | Mumbai → Delhi (~2,800 shipments) |
| Carriers with avg cost > $300 | DHL, FEDEX |
| Total weight shipped by DHL | ~10,000,000 kg |
| Top delayed destination | Delhi |

### Top 5 Most Expensive Shipments
Shipments with cost_usd closest to $499.99 — all carriers represented.

### OTIF% Per Carrier
All carriers show approximately equal on-time performance (~24%), suggesting
the delay issue is systemic rather than carrier-specific.

---

## Exercise 3 — Data Quality Anomaly Findings

| Anomaly Type | Count | Severity |
|-------------|-------|----------|
| Duplicate shipment_id | **0** | ✅ Clean |
| Negative delay_days | **~3,000** | 🔴 Critical |
| Zero or negative cost_usd | **~2,000** | 🔴 Critical |
| Impossible dates (delivered < shipped) | **varies** | 🟡 Investigate |
| Unexpected carrier values | **0** | ✅ Clean |
| Unexpected status values | **0** | ✅ Clean |
| Casing / whitespace issues | **0** | ✅ Clean |

### Key Findings

**🔴 Finding 1 — Negative delay_days (~3,000 rows)**  
Approximately 3% of rows have `delay_days = -1`. This appears to be a system
default value inserted when delay has not yet been calculated, rather than a
true negative delay. These rows will corrupt any `AVG(delay_days)` calculation
and must be either excluded via `WHERE delay_days >= 0` or replaced with NULL
before pipeline ingestion.

**🔴 Finding 2 — Zero cost_usd (~2,000 rows)**  
Approximately 2% of rows have `cost_usd = 0.00`. A real shipment always has
a cost — this likely represents unbilled or not-yet-invoiced shipments. Any
`SUM(cost_usd)` or revenue KPI will be understated until these are resolved.
Recommend flagging for the client's finance team to confirm whether these
should be excluded, back-filled, or marked as pending.

**🟡 Finding 3 — Impossible dates**  
A small number of rows have `delivered_date < shipped_date`. Likely a data
entry or system clock issue. These rows should be flagged for manual review
before any SLA or transit-time calculation is built.

---

## Recommendations

1. **Do not build any pipeline on this data until anomalies are resolved.**
   The ~5,000 dirty rows will silently corrupt KPI calculations.

2. **Agree a remediation strategy with the client** for each anomaly type
   before Day 3 — reject, fix, or flag with a data quality flag column.

3. **Add a data quality layer** as the first transform in the Foundry
   Pipeline Builder — filter out `delay_days < 0` and `cost_usd <= 0`
   with explicit logging of excluded rows for audit purposes.

4. **Re-run this audit after every data load** — the anomaly counts suggest
   these are systemic issues in the upstream system, not one-off errors.

---

*Report generated as part of FDE Academy Day 7 SQL Lab*  
*TechStar Group Palantir COE | Cohort 22*
