import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
import api

client = TestClient(api.app)
r = client.post("/api/auth/login", json={"username": "admin", "password": "Admin@123"})
headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

r = client.get("/api/accounts", headers=headers)
data = r.json().get("data", {})
accounts = data.get("accounts", [])
print("total:", data.get("total"))
for a in accounts[:20]:
    print(a.get("code"), "-", a.get("name"))