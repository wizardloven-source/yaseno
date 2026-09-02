# test_api2.py - ط§ط®طھط¨ط§ط± ظ†ظ‚ط§ط· ط§ظ„ظ†ظ‡ط§ظٹط© ط§ظ„ط¬ط¯ظٹط¯ط© (Products, Suppliers, PO, Payments, Funds, Reports)
import os
import sys
import uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient

import api

client = TestClient(api.app)

PASS = 0
FAIL = 0

def check(label, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [OK] {label} {extra}")
    else:
        FAIL += 1
        print(f"  [XX] {label} {extra}")


def check_created(label, r, extra=""):
    global PASS, FAIL
    ok = r.status_code in (200, 201) and r.json().get("success") is True
    if ok:
        PASS += 1
        print(f"  [OK] {label} {extra}")
    else:
        FAIL += 1
        print(f"  [XX] {label} status={r.status_code} body={r.json()}")

print("=" * 60)
print("LOGIN")
r = client.post("/api/auth/login", json={"username": "admin", "password": "Admin@123"})
body = r.json()
headers = {}
if r.status_code == 200:
    headers = {"Authorization": f"Bearer {body['access_token']}"}
check("login", r.status_code == 200 and headers, f"status={r.status_code}")

rand = str(uuid.uuid4().int)[:6]

print("=" * 60)
print("PRODUCTS")
prod_code = "PR" + rand
r = client.post("/api/products", headers=headers, json={
    "code": prod_code, "name": "ظ…ظ†طھط¬ ط§ط®طھط¨ط§ط±", "unit_price": "25.50",
    "tax_rate": "10", "category": "test", "stock_quantity": 100,
    "low_stock_threshold": 5,
})
pb = r.json()
print("  create:", r.status_code, pb.get("message", pb))
check_created("product create", r)
prod_id = pb.get("data", {}).get("id")

r = client.get("/api/products", headers=headers)
print("  list:", r.status_code, "count:", len(r.json().get("data", {}).get("items", [])))
check("products list", r.status_code == 200)

if prod_id:
    r = client.get(f"/api/products/{prod_id}", headers=headers)
    print("  get:", r.status_code)
    check("product get", r.status_code == 200 and r.json().get("data", {}).get("code") == prod_code)

print("=" * 60)
print("SUPPLIERS")
sup_code = "SU" + rand
r = client.post("/api/suppliers", headers=headers, json={
    "code": sup_code, "name": "ظ…ظˆط±ط¯ ط§ط®طھط¨ط§ط±", "email": "s@example.com",
    "phone": "01123456", "city": "Beirut", "tax_number": "TAX123",
    "credit_limit": "5000", "notes": "note",
})
sb = r.json()
print("  create:", r.status_code, sb.get("message", sb))
check_created("supplier create", r)
sup_id = sb.get("data", {}).get("id")

r = client.get("/api/suppliers", headers=headers)
print("  list:", r.status_code, "count:", len(r.json().get("data", {}).get("items", [])))
check("suppliers list", r.status_code == 200)

if sup_id:
    r = client.get(f"/api/suppliers/{sup_id}", headers=headers)
    print("  get:", r.status_code)
    check("supplier get", r.status_code == 200 and r.json().get("data", {}).get("code") == sup_code)

print("=" * 60)
print("PURCHASE ORDERS")
r = client.get("/api/purchase-orders", headers=headers)
print("  list:", r.status_code, "count:", len(r.json().get("data", {}).get("items", [])))
check("po list", r.status_code == 200)

if sup_id:
    r = client.post("/api/purchase-orders", headers=headers, json={
        "supplier_id": sup_id, "currency": "USD", "notes": "ط£ظ…ط± ط´ط±ط§ط، ط§ط®طھط¨ط§ط±ظٹ",
        "lines": [
            {"product_code": prod_code, "product_name": "ظ…ظ†طھط¬ ط§ط®طھط¨ط§ط±", "quantity": "2", "unit_price": "25.50"}
        ]
    })
    pob = r.json()
    print("  create:", r.status_code, pob.get("message", pob))
    check_created("po create", r)
    po_id = pob.get("data", {}).get("id")
    if po_id:
        r = client.get(f"/api/purchase-orders/{po_id}", headers=headers)
        print("  get:", r.status_code)
        check("po get", r.status_code == 200 and r.json().get("data", {}).get("status") == "draft")

print("=" * 60)
print("FUNDS")
acct_code = "5" + rand
r = client.post("/api/accounts", headers=headers, json={
    "code": acct_code, "name": "ط­ط³ط§ط¨ طµظ†ط¯ظˆظ‚", "account_type": "asset",
    "currency": "USD", "is_active": True
})
print("  account:", r.status_code, r.json().get("message", r.json()))

fund_code = "FN" + rand
r = client.post("/api/funds", headers=headers, json={
    "code": fund_code, "name": "طµظ†ط¯ظˆظ‚ ط±ط¦ظٹط³ظٹ", "account_code": acct_code,
    "fund_type": "main", "currency": "USD", "opening_balance": "1000",
})
fb = r.json()
print("  create:", r.status_code, fb.get("message", fb))
check_created("fund create", r)
fund_id = fb.get("data", {}).get("id")

r = client.get("/api/funds", headers=headers)
print("  list:", r.status_code, "count:", len(r.json().get("data", {}).get("items", [])))
check("funds list", r.status_code == 200)

if fund_id:
    r = client.get(f"/api/funds/{fund_id}", headers=headers)
    print("  get:", r.status_code)
    check("fund get", r.status_code == 200)
    r = client.get(f"/api/funds/{fund_id}/balance", headers=headers)
    print("  balance:", r.status_code, r.json())
    check("fund balance", r.status_code == 200)

print("=" * 60)
print("PAYMENTS")
r = client.get("/api/payments", headers=headers)
print("  list:", r.status_code, "count:", len(r.json().get("data", {}).get("items", [])))
check("payments list", r.status_code == 200)

payload = {
    "payment_type": "receive",
    "payment_method": "cash",
    "amount": "150",
    "currency": "USD",
    "fund_id": fund_id or "",
    "description": "ظ‚ط¨ط¶ ظ†ظ‚ط¯ظٹ",
}
r = client.post("/api/payments", headers=headers, json=payload)
pbb = r.json()
print("  create:", r.status_code, pbb.get("message", pbb))
check_created("payment create", r)
pay_id = pbb.get("data", {}).get("id")
if pay_id:
    r = client.get(f"/api/payments/{pay_id}", headers=headers)
    print("  get:", r.status_code)
    check("payment get", r.status_code == 200)

print("=" * 60)
print("REPORTS")
r = client.get("/api/reports/trial-balance", headers=headers, params={"as_of_date": "2026-12-31"})
print("  trial-balance:", r.status_code, "total:", len(r.json().get("data", {}).get("items", [])))
check("trial-balance", r.status_code == 200)

r = client.get("/api/reports/accounts", headers=headers)
print("  accounts:", r.status_code, "total:", len(r.json().get("data", {}).get("items", [])))
check("accounts report", r.status_code == 200)

print("=" * 60)
print(f"RESULT: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
