import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(line_buffering=True)
print("START", flush=True)

import api
print("api imported", flush=True)

from fastapi.testclient import TestClient
client = TestClient(api.app)
print("client created", flush=True)

r = client.post("/api/auth/login", json={"username": "admin", "password": "Admin@123"})
headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
print("login ok", flush=True)

r = client.get("/api/journal-entries", headers=headers)
entry_id = r.json()["data"]["items"][0]["id"]
print("entry_id:", entry_id, flush=True)

print("posting...", flush=True)
r = client.post(f"/api/journal-entries/{entry_id}/post", headers=headers, timeout=30)
print("POST entry:", r.status_code, r.json().get("message"), flush=True)