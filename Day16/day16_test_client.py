"""
Day 16 — Test client to verify all 3 exercises
Run AFTER starting: uvicorn day16_main:app --reload --port 8000
"""
import time
import requests

BASE = "http://127.0.0.1:8000"

def sep(title: str):
    print(f"\n{'=' * 55}")
    print(f"  {title}")
    print('=' * 55)

# ─── EXERCISE 1 TESTS ─────────────────────────────────────────────────────────
sep("EXERCISE 1 — 5 ENDPOINTS")

# 1. List all shipments
r = requests.get(f"{BASE}/shipments")
print(f"\nGET /shipments → {r.status_code}")
for s in r.json():
    print(f"  {s}")

# 2. Filter by carrier
r = requests.get(f"{BASE}/shipments?carrier=BlueDart")
print(f"\nGET /shipments?carrier=BlueDart → {r.status_code} ({len(r.json())} results)")

# 3. Get single shipment
r = requests.get(f"{BASE}/shipments/1")
print(f"\nGET /shipments/1 → {r.status_code}: {r.json()}")

# 4. 404 for missing
r = requests.get(f"{BASE}/shipments/999")
print(f"\nGET /shipments/999 → {r.status_code}: {r.json()['detail']}")

# 5. POST with negative cost → 422
r = requests.post(f"{BASE}/shipments", json={
    "carrier": "DHL", "ship_date": "2026-06-10", "freight_cost": -50.0
})
print(f"\nPOST /shipments (negative cost) → {r.status_code} (expected 422)")

# 6. POST with valid data → 201
r = requests.post(f"{BASE}/shipments", json={
    "carrier": "DTDC", "ship_date": "2026-06-10", "freight_cost": 199.0
})
print(f"\nPOST /shipments (valid) → {r.status_code}: {r.json()}")

# 7. Analytics summary
r = requests.get(f"{BASE}/analytics/summary")
print(f"\nGET /analytics/summary → {r.status_code}: {r.json()}")

# 8. Delete shipment → 204
r = requests.delete(f"{BASE}/shipments/1")
print(f"\nDELETE /shipments/1 → {r.status_code} (expected 204)")
r = requests.get(f"{BASE}/shipments/1")
print(f"GET /shipments/1 after delete → {r.status_code} (expected 404)")

# ─── EXERCISE 2 TESTS ─────────────────────────────────────────────────────────
sep("EXERCISE 2 — BACKGROUND TASK")

# Trigger refresh — should return instantly
start = time.time()
r = requests.post(f"{BASE}/analytics/refresh")
elapsed = time.time() - start
print(f"\nPOST /analytics/refresh → {r.status_code} in {elapsed:.2f}s (expected <0.5s)")
print(f"  Response: {r.json()}")

# Immediate status check — should be 'running'
r = requests.get(f"{BASE}/analytics/refresh-status")
print(f"\nGET /analytics/refresh-status (immediate) → {r.json()['state']}")

# Wait 6 seconds then check again — should be 'complete'
print("  Waiting 6 seconds...")
time.sleep(6)
r = requests.get(f"{BASE}/analytics/refresh-status")
print(f"GET /analytics/refresh-status (after 6s) → {r.json()}")

# ─── EXERCISE 3 TESTS ─────────────────────────────────────────────────────────
sep("EXERCISE 3 — OAUTH2 AUTH")

# Get token with correct credentials
r = requests.post(f"{BASE}/token", data={
    "username": "ops_admin", "password": "demo-password"
})
print(f"\nPOST /token (correct creds) → {r.status_code}")
token = r.json().get("access_token", "")
print(f"  Token: {token[:40]}...")

# Try protected endpoint WITHOUT token → 401
r = requests.post(f"{BASE}/shipments/protected", json={
    "carrier": "FedEx", "ship_date": "2026-06-15", "freight_cost": 350.0
})
print(f"\nPOST /shipments/protected (no token) → {r.status_code} (expected 401)")

# Try protected endpoint WITH token → 201
headers = {"Authorization": f"Bearer {token}"}
r = requests.post(f"{BASE}/shipments/protected", json={
    "carrier": "FedEx", "ship_date": "2026-06-15", "freight_cost": 350.0
}, headers=headers)
print(f"\nPOST /shipments/protected (with token) → {r.status_code}: {r.json()}")

# Try with wrong credentials → 401
r = requests.post(f"{BASE}/token", data={
    "username": "wrong_user", "password": "wrong_pass"
})
print(f"\nPOST /token (wrong creds) → {r.status_code}: {r.json()['detail']}")

# Delete with token → 204
r = requests.delete(f"{BASE}/shipments/protected/2", headers=headers)
print(f"\nDELETE /shipments/protected/2 (with token) → {r.status_code} (expected 204)")

print("\n✓ All tests complete!")