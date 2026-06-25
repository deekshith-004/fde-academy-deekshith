from __future__ import annotations

import asyncio
import random
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

app = FastAPI(
    title="TechStar Group — Supply Chain Status API",
    description=(
        "Internal utility API for AutoFinance Bank discovery phase "
        "data validation. Built by FDE Academy Cohort."
    ),
    version="1.0.0",
)

# ── Mock in-memory database ───────────────────────────────────────────────────

MOCK_SHIPMENTS: dict[str, dict] = {
    "SH001": {
        "shipment_id": "SH001",
        "carrier": "DHL",
        "status": "in_transit",
        "origin": "Mumbai",
        "destination": "Delhi",
        "cost_usd": 250.0,
        "created_at": "2024-01-18T10:00:00",
    },
    "SH002": {
        "shipment_id": "SH002",
        "carrier": "FEDEX",
        "status": "delivered",
        "origin": "Chennai",
        "destination": "Bangalore",
        "cost_usd": 180.5,
        "created_at": "2024-01-17T09:30:00",
    },
    "SH003": {
        "shipment_id": "SH003",
        "carrier": "BLUEDART",
        "status": "delayed",
        "origin": "Pune",
        "destination": "Hyderabad",
        "cost_usd": 320.0,
        "created_at": "2024-01-16T14:15:00",
    },
}

MOCK_CARRIERS: dict[str, dict] = {
    "DHL": {"code": "DHL", "name": "DHL Express", "sla_days": 2},
    "FEDEX": {"code": "FEDEX", "name": "FedEx India", "sla_days": 3},
    "BLUEDART": {"code": "BLUEDART", "name": "BlueDart", "sla_days": 2},
}

# ── Auth ──────────────────────────────────────────────────────────────────────

VALID_API_KEYS = {"techstar-fde-key-001", "techstar-fde-key-002"}


def verify_api_key(x_api_key: Optional[str] = Header(default=None)) -> str:
    """
    FastAPI dependency — validates the X-API-Key header.
    Raises 401 if missing, 403 if present but invalid.
    """
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="API key missing")
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key


# ── Pydantic models ───────────────────────────────────────────────────────────

class ShipmentResponse(BaseModel):
    """What every shipment endpoint returns."""

    shipment_id: str
    carrier: str
    status: str
    origin: str
    destination: str
    cost_usd: float
    created_at: str


class CarrierResponse(BaseModel):
    code: str
    name: str
    sla_days: int


class ShipmentCreateRequest(BaseModel):
    """Validates the body of POST /shipments."""

    shipment_id: str = Field(..., min_length=3, max_length=20)
    carrier: str = Field(..., min_length=2)
    origin: str = Field(..., min_length=2)
    destination: str = Field(..., min_length=2)
    cost_usd: float = Field(..., gt=0)

    @field_validator("carrier")
    @classmethod
    def validate_carrier(cls, v: str) -> str:
        v = v.upper().strip()
        if v not in {"DHL", "FEDEX", "BLUEDART"}:
            raise ValueError(f"carrier must be one of DHL, FEDEX, BLUEDART — got {v!r}")
        return v


class VendorStatus(BaseModel):
    """Unified shape — every vendor response gets normalised to this."""

    shipment_id: str
    source_vendor: str
    normalised_status: str
    raw: dict


# ── Vendor simulators ─────────────────────────────────────────────────────────

async def call_vendor_a(shipment_id: str) -> dict:
    """Vendor A: clean field names, occasionally slow."""
    await asyncio.sleep(0.1)
    return {"id": shipment_id, "current_status": "in_transit", "eta_days": 2}


async def call_vendor_b(shipment_id: str) -> dict:
    """Vendor B: different field names, occasionally raises an error."""
    await asyncio.sleep(0.15)
    if random.random() < 0.3:
        raise ConnectionError("Vendor B timeout")
    return {"shipmentRef": shipment_id, "trackingState": "DELAYED", "delayHrs": 36}


async def call_vendor_c(shipment_id: str) -> dict:
    """Vendor C: nested response shape, reliable."""
    await asyncio.sleep(0.08)
    return {
        "shipment": {
            "identifier": shipment_id,
            "state": {"code": "DELIVERED", "confidence": 0.95},
        }
    }


# ── Normaliser functions ──────────────────────────────────────────────────────

def normalise_vendor_a(raw: dict) -> VendorStatus:
    return VendorStatus(
        shipment_id=raw["id"],
        source_vendor="vendor_a",
        normalised_status=raw.get("current_status", "unknown"),
        raw=raw,
    )


def normalise_vendor_b(raw: dict) -> VendorStatus:
    status_map = {
        "IN_TRANSIT": "in_transit",
        "DELAYED": "delayed",
        "DELIVERED": "delivered",
    }
    tracking_state = raw.get("trackingState", "UNKNOWN").upper()
    return VendorStatus(
        shipment_id=raw.get("shipmentRef", "unknown"),
        source_vendor="vendor_b",
        normalised_status=status_map.get(tracking_state, "unknown"),
        raw=raw,
    )


def normalise_vendor_c(raw: dict) -> VendorStatus:
    shipment = raw.get("shipment", {})
    state = shipment.get("state", {})
    code = state.get("code", "UNKNOWN").upper()
    status_map = {
        "IN_TRANSIT": "in_transit",
        "DELAYED": "delayed",
        "DELIVERED": "delivered",
    }
    return VendorStatus(
        shipment_id=shipment.get("identifier", "unknown"),
        source_vendor="vendor_c",
        normalised_status=status_map.get(code, "unknown"),
        raw=raw,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check() -> dict:
    """Health check — no auth required."""
    return {"status": "ok", "service": "supply-chain-status-api"}


@app.get("/shipments", response_model=list[ShipmentResponse])
def list_shipments(
    status: Optional[str] = None,
    carrier: Optional[str] = None,
    api_key: str = Depends(verify_api_key),
) -> list[dict]:
    """
    GET /shipments
    GET /shipments?status=delayed
    GET /shipments?carrier=DHL&status=in_transit
    """
    results = list(MOCK_SHIPMENTS.values())
    if status:
        results = [s for s in results if s["status"] == status.lower()]
    if carrier:
        results = [s for s in results if s["carrier"] == carrier.upper()]
    return results


@app.get("/shipments/{shipment_id}", response_model=ShipmentResponse)
def get_shipment(
    shipment_id: str,
    api_key: str = Depends(verify_api_key),
) -> dict:
    """GET /shipments/SH001 — 404 if shipment_id not found."""
    if shipment_id not in MOCK_SHIPMENTS:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")
    return MOCK_SHIPMENTS[shipment_id]


@app.post("/shipments", response_model=ShipmentResponse, status_code=201)
def create_shipment(
    payload: ShipmentCreateRequest,
    api_key: str = Depends(verify_api_key),
) -> dict:
    """POST /shipments — 409 Conflict if shipment_id already exists."""
    if payload.shipment_id in MOCK_SHIPMENTS:
        raise HTTPException(
            status_code=409,
            detail=f"Shipment {payload.shipment_id} already exists",
        )
    record = {
        "shipment_id": payload.shipment_id,
        "carrier": payload.carrier,
        "origin": payload.origin,
        "destination": payload.destination,
        "cost_usd": payload.cost_usd,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
    }
    MOCK_SHIPMENTS[payload.shipment_id] = record
    return record


@app.get("/carriers", response_model=list[CarrierResponse])
def list_carriers(api_key: str = Depends(verify_api_key)) -> list[dict]:
    """GET /carriers — returns all known carrier configs."""
    return list(MOCK_CARRIERS.values())


@app.get("/supply-chain-status/{shipment_id}", response_model=list[VendorStatus])
async def get_supply_chain_status(
    shipment_id: str,
    api_key: str = Depends(verify_api_key),
) -> list[VendorStatus]:
    """
    Call all 3 vendors CONCURRENTLY for the given shipment_id.
    A failing vendor is omitted from the result, not crashing the request.
    Raises 503 only if ALL THREE vendors fail.
    """
    vendor_calls = [
        call_vendor_a(shipment_id),
        call_vendor_b(shipment_id),
        call_vendor_c(shipment_id),
    ]
    normalisers = [normalise_vendor_a, normalise_vendor_b, normalise_vendor_c]

    results = await asyncio.gather(*vendor_calls, return_exceptions=True)

    statuses: list[VendorStatus] = []
    for raw, normalise_fn in zip(results, normalisers):
        if isinstance(raw, Exception):
            continue
        statuses.append(normalise_fn(raw))

    if not statuses:
        raise HTTPException(status_code=503, detail="All vendor systems unreachable")

    return statuses