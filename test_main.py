from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from main import app, MOCK_SHIPMENTS

client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": "techstar-fde-key-001"}


# ── Auth tests ────────────────────────────────────────────────────────────────

def test_missing_api_key_returns_401():
    response = client.get("/shipments")
    assert response.status_code == 401


def test_invalid_api_key_returns_403():
    response = client.get("/shipments", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 403


def test_health_check_no_auth_required():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ── Shipment CRUD tests ───────────────────────────────────────────────────────

def test_list_shipments_returns_all():
    response = client.get("/shipments", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert len(response.json()) == len(MOCK_SHIPMENTS)


def test_list_shipments_filters_by_status():
    response = client.get("/shipments?status=delayed", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert all(s["status"] == "delayed" for s in data)


def test_list_shipments_filters_by_carrier():
    response = client.get("/shipments?carrier=DHL", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert all(s["carrier"] == "DHL" for s in data)


def test_get_shipment_success():
    response = client.get("/shipments/SH001", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json()["shipment_id"] == "SH001"
    assert response.json()["carrier"] == "DHL"


def test_get_shipment_not_found_returns_404():
    response = client.get("/shipments/NONEXISTENT", headers=AUTH_HEADERS)
    assert response.status_code == 404
    assert "NONEXISTENT" in response.json()["detail"]


def test_create_shipment_success():
    payload = {
        "shipment_id": "SH999",
        "carrier": "dhl",
        "origin": "Mumbai",
        "destination": "Pune",
        "cost_usd": 99.0,
    }
    response = client.post("/shipments", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 201
    assert response.json()["carrier"] == "DHL"
    assert response.json()["shipment_id"] == "SH999"
    # cleanup so other tests are not affected
    MOCK_SHIPMENTS.pop("SH999", None)


def test_create_shipment_invalid_carrier_returns_422():
    payload = {
        "shipment_id": "SH998",
        "carrier": "UPS",
        "origin": "Mumbai",
        "destination": "Pune",
        "cost_usd": 99.0,
    }
    response = client.post("/shipments", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 422


def test_create_shipment_duplicate_id_returns_409():
    payload = {
        "shipment_id": "SH001",
        "carrier": "DHL",
        "origin": "Mumbai",
        "destination": "Pune",
        "cost_usd": 50.0,
    }
    response = client.post("/shipments", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 409


def test_create_shipment_negative_cost_returns_422():
    payload = {
        "shipment_id": "SH997",
        "carrier": "DHL",
        "origin": "Mumbai",
        "destination": "Pune",
        "cost_usd": -10.0,
    }
    response = client.post("/shipments", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 422


# ── Carriers tests ────────────────────────────────────────────────────────────

def test_list_carriers_returns_all():
    response = client.get("/carriers", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    codes = {c["code"] for c in data}
    assert codes == {"DHL", "FEDEX", "BLUEDART"}


# ── Vendor aggregation tests (deterministic via mocks) ────────────────────────

@patch("main.call_vendor_c", new_callable=AsyncMock)
@patch("main.call_vendor_b", new_callable=AsyncMock)
@patch("main.call_vendor_a", new_callable=AsyncMock)
def test_supply_chain_status_all_vendors_succeed(mock_a, mock_b, mock_c):
    """When all 3 vendors respond, expect all 3 normalised results."""
    mock_a.return_value = {"id": "SH001", "current_status": "in_transit", "eta_days": 2}
    mock_b.return_value = {"shipmentRef": "SH001", "trackingState": "DELAYED", "delayHrs": 36}
    mock_c.return_value = {
        "shipment": {"identifier": "SH001", "state": {"code": "DELIVERED", "confidence": 0.95}}
    }

    response = client.get("/supply-chain-status/SH001", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    vendors = {r["source_vendor"] for r in data}
    assert vendors == {"vendor_a", "vendor_b", "vendor_c"}


@patch("main.call_vendor_c", new_callable=AsyncMock)
@patch("main.call_vendor_b", new_callable=AsyncMock)
@patch("main.call_vendor_a", new_callable=AsyncMock)
def test_supply_chain_status_one_vendor_fails(mock_a, mock_b, mock_c):
    """Vendor B failing should still return 200 with 2 results."""
    mock_a.return_value = {"id": "SH001", "current_status": "in_transit", "eta_days": 2}
    mock_b.side_effect = ConnectionError("Vendor B timeout")
    mock_c.return_value = {
        "shipment": {"identifier": "SH001", "state": {"code": "DELIVERED"}}
    }

    response = client.get("/supply-chain-status/SH001", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    vendors = {r["source_vendor"] for r in data}
    assert "vendor_b" not in vendors


@patch("main.call_vendor_c", new_callable=AsyncMock)
@patch("main.call_vendor_b", new_callable=AsyncMock)
@patch("main.call_vendor_a", new_callable=AsyncMock)
def test_supply_chain_status_all_vendors_fail_returns_503(mock_a, mock_b, mock_c):
    """If every vendor fails, the endpoint must return 503."""
    mock_a.side_effect = ConnectionError("down")
    mock_b.side_effect = ConnectionError("down")
    mock_c.side_effect = ConnectionError("down")

    response = client.get("/supply-chain-status/SH001", headers=AUTH_HEADERS)
    assert response.status_code == 503


@patch("main.call_vendor_c", new_callable=AsyncMock)
@patch("main.call_vendor_b", new_callable=AsyncMock)
@patch("main.call_vendor_a", new_callable=AsyncMock)
def test_supply_chain_status_normalised_statuses_correct(mock_a, mock_b, mock_c):
    """Verify each vendor's status is correctly normalised."""
    mock_a.return_value = {"id": "SH001", "current_status": "in_transit"}
    mock_b.return_value = {"shipmentRef": "SH001", "trackingState": "DELAYED"}
    mock_c.return_value = {
        "shipment": {"identifier": "SH001", "state": {"code": "DELIVERED"}}
    }

    response = client.get("/supply-chain-status/SH001", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    status_by_vendor = {r["source_vendor"]: r["normalised_status"] for r in data}
    assert status_by_vendor["vendor_a"] == "in_transit"
    assert status_by_vendor["vendor_b"] == "delayed"
    assert status_by_vendor["vendor_c"] == "delivered"