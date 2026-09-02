import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
import api

client = TestClient(api.app)
r = client.post("/api/auth/login", json={"username": "admin", "password": "Admin@123"})
headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

r = client.get("/api/journal-entries", headers=headers)
items = r.json().get("data", {}).get("items", [])
print("entries:", len(items))
entry_id = items[0]["id"]
print("entry_id:", entry_id)

r = client.post(f"/api/journal-entries/{entry_id}/post", headers=headers)
print("POST entry:", r.status_code, r.json().get("message"))

r = client.post(f"/api/journal-entries/{entry_id}/reverse", headers=headers, params={"reason": "اختبار"})
print("REVERSE entry:", r.status_code, r.json().get("message"))

r = client.get(f"/api/journal-entries/{entry_id}", headers=headers)
print("GET entry:", r.status_code)
print("  raw:", r.json())