# test_api.py - اختبار نقاط النهاية الأساسية باستخدام TestClient
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient

import api

client = TestClient(api.app)

print("=" * 50)
print("1) GET /api/health")
r = client.get("/api/health")
print(r.status_code, r.json())

print("=" * 50)
print("2) GET /api/health/db")
r = client.get("/api/health/db")
print(r.status_code, r.json())

print("=" * 50)
print("3) POST /api/auth/login (admin/admin123)")
r = client.post("/api/auth/login", json={"username": "admin", "password": "Admin@123"})
print(r.status_code)
body = r.json()
print("success:", body.get("success"), "| message:", body.get("message", "")[:60])
if r.status_code == 200:
    token = body["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
else:
    token = None
    headers = {}

print("=" * 50)
if token:
    print("4) GET /api/auth/me")
    r = client.get("/api/auth/me", headers=headers)
    print(r.status_code, r.json())

    print("=" * 50)
    print("5) GET /api/accounts")
    r = client.get("/api/accounts", headers=headers)
    print(r.status_code, "accounts count:", len(r.json().get("data", {}).get("accounts", [])))

    print("=" * 50)
    print("6) POST /api/accounts (create)")
    import uuid as _uuid
    _acct_code = "9" + str(_uuid.uuid4().int)[:4]
    r = client.post("/api/accounts", headers=headers, json={
        "code": _acct_code, "name": "حساب اختبار", "account_type": "asset",
        "currency": "USD", "is_active": True
    })
    print(r.status_code, r.json().get("message", r.json()))

    print("=" * 50)
    print("6b) POST /api/journal-entries (create)")
    r = client.post("/api/journal-entries", headers=headers, json={
        "date": "2026-08-17",
        "description": "قيد اختبار",
        "lines": [
            {"account_code": "1010", "debit": "500", "credit": "0"},
            {"account_code": "2010", "debit": "0", "credit": "500"},
        ]
    })
    print(r.status_code, r.json().get("message", r.json()))

    print("=" * 50)
    print("7) GET /api/journal-entries")
    r = client.get("/api/journal-entries", headers=headers)
    print(r.status_code, "entries:", r.json().get("data", {}).get("total"))

    print("=" * 50)
    print("8) POST /api/customers (create)")
    _cust_code = "C" + str(_uuid.uuid4().int)[:6]
    r = client.post("/api/customers", headers=headers, json={
        "code": _cust_code, "name": "شركة اختبار", "currency": "USD"
    })
    print(r.status_code, r.json().get("message", r.json()))

    print("=" * 50)
    print("9) GET /api/invoices")
    r = client.get("/api/invoices", headers=headers)
    print(r.status_code, "invoices:", len(r.json().get("data", {}).get("items", [])))
else:
    print("SKIPPING authed endpoints (login failed)")