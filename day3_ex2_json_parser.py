import pandas as pd
from typing import Any, Dict, List

# Complete Mock API Payload from Logistics Carrier API
API_RESPONSE = {
    "meta": {"request_id": "REQ-2024-001", "total_records": 3, "page": 1},
    "shipments": [
        {
            "id": "SH-001",
            "reference": "PO-AFB-2024-441",
            "status": {
                "code": "IN_TRANSIT",
                "description": "Package in transit to destination hub",
                "updated_at": "2024-01-20T08:15:00Z",
            },
            "carrier": {
                "name": "DHL Express",
                "code": "DHL",
                "service_type": "EXPRESS",
                "contact": {"email": "ops@dhl.in", "phone": "+91-22-12345678"},
            },
            "route": {
                "origin": {"city": "Mumbai", "state": "MH", "pin": "400001"},
                "destination": {"city": "Delhi", "state": "DL", "pin": "110001"},
                "estimated_delivery": "2024-01-22",
                "distance_km": 1450,
            },
            "events": [
                {
                    "ts": "2024-01-18T10:00:00Z",
                    "location": "Mumbai Warehouse",
                    "type": "PICKUP",
                },
                {
                    "ts": "2024-01-19T06:30:00Z",
                    "location": "Nagpur Hub",
                    "type": "IN_TRANSIT",
                },
                {
                    "ts": "2024-01-20T08:15:00Z",
                    "location": "Delhi Hub",
                    "type": "ARRIVED",
                },
            ],
            "charges": {
                "base": 850.0,
                "fuel_surcharge": 127.5,
                "gst": 177.75,
                "total": 1155.25,
            },
            "delay_days": 0,
        },
        {
            "id": "SH-002",
            "reference": "PO-AFB-2024-442",
            "status": {
                "code": "DELAYED",
                "description": "Delayed due to customs clearance",
                "updated_at": "2024-01-20T07:00:00Z",
            },
            "carrier": {
                "name": "FedEx India",
                "code": "FEDEX",
                "service_type": "STANDARD",
                "contact": {"email": "support@fedex.in"},
            },
            "route": {
                "origin": {"city": "Chennai", "state": "TN", "pin": "600001"},
                "destination": {"city": "Bangalore", "state": "KA", "pin": "560001"},
                "estimated_delivery": "2024-01-21",
                "distance_km": 346,
            },
            "events": [
                {
                    "ts": "2024-01-18T14:00:00Z",
                    "location": "Chennai Port",
                    "type": "PICKUP",
                },
                {
                    "ts": "2024-01-20T07:00:00Z",
                    "location": "Customs Delhi",
                    "type": "HELD",
                },
            ],
            "charges": {
                "base": 320.0,
                "fuel_surcharge": 48.0,
                "gst": 66.24,
                "total": 434.24,
            },
            "delay_days": 3,
        },
        {
            "id": "SH-003",
            "reference": None,
            "status": {"code": "DELIVERED", "updated_at": "2024-01-19T16:00:00Z"},
            "carrier": {
                "name": "BlueDart",
                "code": "BLUEDART",
                "service_type": "ECONOMY",
            },
            "route": {
                "origin": {"city": "Pune"},
                "destination": {"city": "Hyderabad", "state": "TS", "pin": "500001"},
                "estimated_delivery": "2024-01-19",
                "distance_km": 559,
            },
            "events": [
                {
                    "ts": "2024-01-17T09:00:00Z",
                    "location": "Pune Depot",
                    "type": "PICKUP",
                },
                {
                    "ts": "2024-01-19T16:00:00Z",
                    "location": "Hyderabad Depot",
                    "type": "DELIVERED",
                },
            ],
            "charges": {"base": 180.0, "gst": 32.4, "total": 212.4},
            "delay_days": 0,
        },
    ],
}


def parse_shipment(shipment: Dict[str, Any]) -> Dict[str, Any]:
    """Flattens a single nested shipment record into a flat dictionary."""
    status_obj = shipment.get("status") or {}
    carrier_obj = shipment.get("carrier") or {}
    route_obj = shipment.get("route") or {}
    charges_obj = shipment.get("charges") or {}

    origin_obj = route_obj.get("origin") or {}
    dest_obj = route_obj.get("destination") or {}

    return {
        "shipment_id": shipment.get("id"),
        "reference": shipment.get("reference"),
        "status_code": status_obj.get("code"),
        "status_updated_at": status_obj.get("updated_at"),
        "carrier_name": carrier_obj.get("name"),
        "carrier_code": carrier_obj.get("code"),
        "service_type": carrier_obj.get("service_type"),
        "origin_city": origin_obj.get("city"),
        "origin_state": origin_obj.get("state"),
        "destination_city": dest_obj.get("city"),
        "destination_state": dest_obj.get("state"),
        "distance_km": route_obj.get("distance_km"),
        "estimated_delivery": route_obj.get("estimated_delivery"),
        "base_charge": charges_obj.get("base"),
        "fuel_surcharge": charges_obj.get("fuel_surcharge", 0.0),
        "gst_charge": charges_obj.get("gst"),
        "total_charge": charges_obj.get("total"),
        "delay_days": shipment.get("delay_days", 0),
    }


def flatten_api_response(response: Dict[str, Any]) -> pd.DataFrame:
    """Processes raw API collection and builds a flat DataFrame."""
    shipments_list = response.get("shipments") or []
    flattened_records = [parse_shipment(s) for s in shipments_list]
    return pd.DataFrame(flattened_records)


if __name__ == "__main__":
    print("🚀 Running API Parsing Sequence Engine...")
    flat_df = flatten_api_response(API_RESPONSE)

    print(f"\n✅ Flattened {len(flat_df)} payload records successfully!")

    output_filename = "shipments_flattened.csv"
    flat_df.to_csv(output_filename, index=False)
    print(f"💾 Tabular output file saved to disk as: '{output_filename}'")

    print("\n--- FLATTENED DATAFRAME VIEW ---")
    preview_cols = [
        "shipment_id",
        "carrier_code",
        "status_code",
        "origin_city",
        "total_charge",
    ]
    print(flat_df[preview_cols])
