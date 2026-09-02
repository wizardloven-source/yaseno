import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
import api

client = TestClient(api.app)

r = client.post("/api/auth/login", json={"username": "admin", "password": "Admin@123"})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

for path in ["/api/invoices", "/api/customers"]:
    r = client.get(path, headers=headers)
    print(path, "->", r.status_code)
    print(r.json())
