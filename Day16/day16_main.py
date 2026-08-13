"""
Day 16 — FastAPI Basics: All 3 Exercises in one file
Exercise 1: 5 Analytics Endpoints
Exercise 2: Background Task for Async Processing
Exercise 3: OAuth2 Bearer Token Authentication
"""
from __future__ import annotations

import time
import jwt
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import (
    BackgroundTasks, Depends, FastAPI, HTTPException, status
)
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="TechStar Shipment Analytics API",
    version="1.0.0",
    description=(
        "Logistics analytics API — Day 16 FDE Academy exercise. "
        "Covers validated endpoints, background tasks, and OAuth2 JWT auth."
    ),
)

# ─────────────────────────────────────────────────────────────────────────────
# EXERCISE 1 — DATA + MODELS
# ─────────────────────────────────────────────────────────────────────────────

shipments_db: list[dict] = [
    {"id": 1, "carrier": "BlueDart",  "ship_date": date(2026, 6, 1),
     "freight_cost": 450.0, "status": "delivered"},
    {"id": 2, "carrier": "Delhivery", "ship_date": date(2026, 6, 2),
     "freight_cost": 620.0, "status": "in_transit"},
    {"id": 3, "carrier": "BlueDart",  "ship_date": date(2026, 6, 3),
     "freight_cost": 310.0, "status": "delivered"},
]
next_id = 4


class ShipmentCreate(BaseModel):
    """Request body for creating a new shipment — no id (server assigns it)."""
    carrier: str = Field(..., min_length=1, description="Carrier name")
    ship_date: date = Field(..., description="Ship date (YYYY-MM-DD)")
    freight_cost: float = Field(..., gt=0, description="Cost in USD, must be > 0")


class ShipmentResponse(BaseModel):
    """What every shipment endpoint returns — mirrors shipments_db dict shape."""
    id: int
    carrier: str
    ship_date: date
    freight_cost: float
    status: str


class AnalyticsSummary(BaseModel):
    """Response shape for GET /analytics/summary."""
    total_shipments: int
    avg_freight_cost: float
    by_status: dict[str, int]


# ── Shared pagination dependency ──────────────────────────────────────────────
def get_pagination(skip: int = 0, limit: int = 10) -> dict:
    return {"skip": skip, "limit": min(limit, 50)}


# ─────────────────────────────────────────────────────────────────────────────
# EXERCISE 1 — 5 ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

# ENDPOINT 1 (provided): List shipments with pagination + optional carrier filter
@app.get(
    "/shipments",
    response_model=list[ShipmentResponse],
    tags=["Shipments"],
    summary="List all shipments",
)
def list_shipments(
    carrier: Optional[str] = None,
    pagination: dict = Depends(get_pagination),
):
    results = shipments_db
    if carrier:
        results = [s for s in results if s["carrier"] == carrier]
    skip = pagination["skip"]
    limit = pagination["limit"]
    return results[skip: skip + limit]


# ENDPOINT 2: Get single shipment by ID
@app.get(
    "/shipments/{shipment_id}",
    response_model=ShipmentResponse,
    tags=["Shipments"],
    summary="Get a single shipment by ID",
)
def get_shipment(shipment_id: int):
    for s in shipments_db:
        if s["id"] == shipment_id:
            return s
    raise HTTPException(
        status_code=404,
        detail=f"Shipment {shipment_id} not found",
    )


# ENDPOINT 3: Create a new shipment (protected in Exercise 3)
@app.post(
    "/shipments",
    response_model=ShipmentResponse,
    status_code=201,
    tags=["Shipments"],
    summary="Create a new shipment",
)
def create_shipment(
    payload: ShipmentCreate,
    current_user: str = Depends(lambda: None),   # placeholder, replaced Ex3
):
    global next_id
    new_shipment = {
        "id": next_id,
        "carrier": payload.carrier,
        "ship_date": payload.ship_date,
        "freight_cost": payload.freight_cost,
        "status": "pending",
    }
    shipments_db.append(new_shipment)
    next_id += 1
    return new_shipment


# ENDPOINT 4: Analytics summary
@app.get(
    "/analytics/summary",
    response_model=AnalyticsSummary,
    tags=["Analytics"],
    summary="Get shipment KPI summary",
)
def analytics_summary():
    total = len(shipments_db)
    avg_cost = (
        round(sum(s["freight_cost"] for s in shipments_db) / total, 2)
        if total > 0 else 0.0
    )
    by_status: dict[str, int] = {}
    for s in shipments_db:
        by_status[s["status"]] = by_status.get(s["status"], 0) + 1

    return AnalyticsSummary(
        total_shipments=total,
        avg_freight_cost=avg_cost,
        by_status=by_status,
    )


# ENDPOINT 5: Delete a shipment (protected in Exercise 3)
@app.delete(
    "/shipments/{shipment_id}",
    status_code=204,
    tags=["Shipments"],
    summary="Delete a shipment by ID",
)
def delete_shipment(shipment_id: int):
    for i, s in enumerate(shipments_db):
        if s["id"] == shipment_id:
            shipments_db.pop(i)
            return  # 204 No Content — return nothing
    raise HTTPException(
        status_code=404,
        detail=f"Shipment {shipment_id} not found",
    )


# ─────────────────────────────────────────────────────────────────────────────
# EXERCISE 2 — BACKGROUND TASK
# ─────────────────────────────────────────────────────────────────────────────

refresh_status: dict = {"state": "idle", "last_run": None}


def refresh_analytics() -> None:
    """
    Simulates a slow data-refresh job (Day 12 cleaning pipeline).
    Runs in the background AFTER the HTTP response is already sent.
    """
    refresh_status["state"] = "running"
    time.sleep(5)  # Simulate slow ETL work

    # Simulate recomputing — just recount records
    count = len(shipments_db)
    avg = (
        round(sum(s["freight_cost"] for s in shipments_db) / count, 2)
        if count > 0 else 0.0
    )

    refresh_status["state"] = "complete"
    refresh_status["last_run"] = datetime.utcnow().isoformat()
    refresh_status["record_count"] = count
    refresh_status["avg_cost"] = avg


@app.post(
    "/analytics/refresh",
    status_code=202,
    tags=["Analytics"],
    summary="Trigger background analytics refresh",
)
def trigger_refresh(background_tasks: BackgroundTasks):
    """
    Returns 202 IMMEDIATELY — the 5-second refresh runs in the background.
    Client polls GET /analytics/refresh-status to check completion.
    """
    background_tasks.add_task(refresh_analytics)
    return {
        "message": "Analytics refresh started. Poll /analytics/refresh-status for progress.",
        "status": "accepted",
    }


@app.get(
    "/analytics/refresh-status",
    tags=["Analytics"],
    summary="Check background refresh status",
)
def get_refresh_status():
    """Poll this endpoint to check if the background refresh has completed."""
    return refresh_status


# ─────────────────────────────────────────────────────────────────────────────
# EXERCISE 3 — OAuth2 JWT AUTHENTICATION
# ─────────────────────────────────────────────────────────────────────────────

SECRET_KEY = "training-only-secret-change-in-production"
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 30

# Hardcoded demo user — NEVER do this in production
DEMO_USER = {"username": "ops_admin", "password": "demo-password"}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Token endpoint — issues JWT on valid credentials
@app.post(
    "/token",
    tags=["Auth"],
    summary="Login and get a bearer token",
)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if (
        form_data.username != DEMO_USER["username"]
        or form_data.password != DEMO_USER["password"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    expire = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    token = jwt.encode(
        {"sub": form_data.username, "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return {"access_token": token, "token_type": "bearer"}


# Reusable auth dependency
def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """
    Validates the bearer token and returns the username.
    Raises 401 if token is missing, expired, or invalid.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise credentials_exc
        return username
    except jwt.PyJWTError:
        raise credentials_exc


# ── Override Endpoints 3 and 5 with auth protection ──────────────────────────
# Remove the unprotected versions and replace with protected ones

@app.post(
    "/shipments/protected",
    response_model=ShipmentResponse,
    status_code=201,
    tags=["Shipments (Protected)"],
    summary="Create shipment — requires auth token",
)
def create_shipment_protected(
    payload: ShipmentCreate,
    current_user: str = Depends(get_current_user),
):
    global next_id
    new_shipment = {
        "id": next_id,
        "carrier": payload.carrier,
        "ship_date": payload.ship_date,
        "freight_cost": payload.freight_cost,
        "status": "pending",
    }
    shipments_db.append(new_shipment)
    next_id += 1
    return new_shipment


@app.delete(
    "/shipments/protected/{shipment_id}",
    status_code=204,
    tags=["Shipments (Protected)"],
    summary="Delete shipment — requires auth token",
)
def delete_shipment_protected(
    shipment_id: int,
    current_user: str = Depends(get_current_user),
):
    for i, s in enumerate(shipments_db):
        if s["id"] == shipment_id:
            shipments_db.pop(i)
            return
    raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")


@app.post(
    "/analytics/refresh/protected",
    status_code=202,
    tags=["Analytics (Protected)"],
    summary="Trigger refresh — requires auth token",
)
def trigger_refresh_protected(
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
):
    background_tasks.add_task(refresh_analytics)
    return {
        "message": f"Refresh started by {current_user}. Poll /analytics/refresh-status.",
        "status": "accepted",
    }


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "TechStar Shipment Analytics API"}