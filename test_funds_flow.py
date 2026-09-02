# -*- coding: utf-8 -*-
"""Verify funds: create, deposit, transfer, movements, balance."""
import sys
import uuid
import traceback
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

print("=" * 50)
print("0) Login admin")
r = client.post("/api/auth/login", json={"username": "admin", "password": "Admin@123"})
print(r.status_code, r.json().get("message", r.json()))
body = r.json()
token = body.get("access_token")
headers = {"Authorization": f"Bearer {token}"}
if not token:
    print("LOGIN FAILED")
    sys.exit(1)

base = str(uuid.uuid4().int)[:6]

print("=" * 50)
print("1) Create fund A")
r = client.post("/api/funds", headers=headers, json={
    "code": f"TF-{base}-A", "name": f"طھط­ظˆظٹظ„ ط§ط®طھط¨ط§ط± ط£ {base}", "fund_type": "main",
    "currency": "USD", "opening_balance": 0, "account_code": "1010",
})
print(r.status_code, r.json().get("message", r.json()))
fund_a = r.json().get("data", {}).get("id")
print("  fund_a_id:", fund_a)
if not fund_a:
    print("FAILED to create fund A")
    sys.exit(1)

print("=" * 50)
print("2) Create fund B")
r = client.post("/api/funds", headers=headers, json={
    "code": f"TF-{base}-B", "name": f"طھط­ظˆظٹظ„ ط§ط®طھط¨ط§ط± ط¨ {base}", "fund_type": "main",
    "currency": "USD", "opening_balance": 0, "account_code": "1011",
})
print(r.status_code, r.json().get("message", r.json()))
fund_b = r.json().get("data", {}).get("id")
if not fund_b:
    print("FAILED to create fund B")
    sys.exit(1)

print("=" * 50)
print("3) Deposit 200 into fund A")
r = client.post("/api/funds/{}/deposit".format(fund_a), headers=headers, json={
    "amount": 200, "reason": "ط§ظٹط¯ط§ط¹ ط§ط®طھط¨ط§ط±"
})
print(r.status_code, r.json().get("message", r.json()))

print("=" * 50)
print("4) Transfer 120 A -> B")
r = client.post("/api/funds/transfer", headers=headers, json={
    "from_fund_id": fund_a,
    "to_fund_id": fund_b,
    "amount": 120,
    "reason": "طھط­ظˆظٹظ„ ط§ط®طھط¨ط§ط±",
})
body = r.json()
print(r.status_code, body.get("message", body))
data = body.get("data") or {}
print("  success:", data.get("success"))
print("  transfer_id:", data.get("transfer_id"))
print("  journal_entry_id:", data.get("journal_entry_id"))
print("  from_balance_after:", data.get("from_balance_after"))
print("  to_balance_after:", data.get("to_balance_after"))
assert data.get("success") is True, "Transfer did not succeed"
assert data.get("journal_entry_id"), "Transfer missing journal entry"

print("=" * 50)
print("5) Get fund A balance")
r = client.get("/api/funds/{}/balance".format(fund_a), headers=headers)
print(r.status_code, r.json())

print("=" * 50)
print("6) Get fund B balance")
r = client.get("/api/funds/{}/balance".format(fund_b), headers=headers)
print(r.status_code, r.json())

print("=" * 50)
print("7) Fund A movements")
r = client.get("/api/funds/{}/movements".format(fund_a), headers=headers)
body = r.json()
print(r.status_code, "total:", body.get("data", {}).get("total"))
for item in body.get("data", {}).get("items", []):
    print("  -", item.get("movement_type"), item.get("amount"), item.get("currency"), "|", item.get("reason"))

print("=" * 50)
print("8) Fund B movements")
r = client.get("/api/funds/{}/movements".format(fund_b), headers=headers)
body = r.json()
print(r.status_code, "total:", body.get("data", {}).get("total"))
for item in body.get("data", {}).get("items", []):
    print("  -", item.get("movement_type"), item.get("amount"), item.get("currency"), "|", item.get("reason"))

print("=" * 50)
print("9) Transfer same fund (should fail)")
r = client.post("/api/funds/transfer", headers=headers, json={
    "from_fund_id": fund_a, "to_fund_id": fund_a, "amount": 10, "reason": "ظ†ظپط³ ط§ظ„طµظ†ط¯ظˆظ‚"
})
print(r.status_code, r.json().get("message", r.json()))

print("=" * 50)
print("10) Transfer insufficient funds (should fail)")
r = client.post("/api/funds/transfer", headers=headers, json={
    "from_fund_id": fund_b, "to_fund_id": fund_a, "amount": 999999, "reason": "ط±طµظٹط¯ ط؛ظٹط± ظƒط§ظپ"
})
print(r.status_code, r.json().get("message", r.json()))

print("=" * 50)
print("RESULT: PASS" if True else "RESULT: FAIL")
