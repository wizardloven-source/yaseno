# test_po_flow.py - اختبار ترحيل واستلام أمر الشراء بالكامل
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
print("PRODUCT")
prod_code = "P" + rand
r = client.post("/api/products", headers=headers, json={
    "code": prod_code, "name": "منتج اختبار", "unit_price": "25.50",
    "tax_rate": "10", "category": "test", "stock_quantity": 0,
    "low_stock_threshold": 5,
})
pb = r.json()
check_created("product create", r)
prod_id = pb.get("data", {}).get("id")

print("=" * 60)
print("SUPPLIER")
sup_code = "S" + rand
r = client.post("/api/suppliers", headers=headers, json={
    "code": sup_code, "name": "مورد اختبار", "email": "s@example.com",
    "phone": "01123456", "city": "Beirut",
})
sb = r.json()
check_created("supplier create", r)
sup_id = sb.get("data", {}).get("id")

print("=" * 60)
print("PURCHASE ORDER")
r = client.post("/api/purchase-orders", headers=headers, json={
    "supplier_id": sup_id, "currency": "USD", "notes": "أمر شراء اختباري",
    "lines": [
        {"product_code": prod_code, "product_name": "منتج اختبار", "quantity": "10", "unit_price": "7.00"}
    ]
})
pob = r.json()
print("  create:", r.status_code, pob.get("message", pob))
check_created("po create", r)
po_id = pob.get("data", {}).get("id")

print("=" * 60)
print("POST PURCHASE ORDER")
r = client.post(f"/api/purchase-orders/{po_id}/post", headers=headers)
body = r.json()
print("  post:", r.status_code, body.get("message", body))
if r.status_code == 200 and body.get("success"):
    d = body.get("data", {})
    check("po post", d.get("success") is True and d.get("journal_entry_id"), f"je={d.get('journal_entry_id')}")
    je_id = d.get("journal_entry_id")
else:
    je_id = None
    check("po post", False, f"body={body}")

print("=" * 60)
print("PO GET AFTER POST")
r = client.get(f"/api/purchase-orders/{po_id}", headers=headers)
gb = r.json()
check("po status posted", r.status_code == 200 and gb.get("data", {}).get("status") == "posted",
      f"status={gb.get('data', {}).get('status')}")

print("=" * 60)
print("RECEIVE PURCHASE ORDER")
r = client.post(f"/api/purchase-orders/{po_id}/receive", headers=headers)
body = r.json()
print("  receive:", r.status_code, body.get("message", body))
if r.status_code == 200 and body.get("success"):
    check("po receive", True, f"data={str(body.get('data', {}))[:120]}")
    recv = body.get("data", {})
    check("po fully received", recv.get("is_fully_received") is True)
else:
    check("po receive", False, f"body={body}")

print("=" * 60)
print("DB VERIFY")
import psycopg2
c = psycopg2.connect(host='localhost', dbname='erpya', user='postgres', password='postgres')
cur = c.cursor()
if je_id:
    cur.execute("SELECT is_posted FROM journal_entries WHERE id = %s", (je_id,))
    row = cur.fetchone()
    check("je posted", row and row[0] is True, f"row={row}")
    cur.execute("SELECT COUNT(*) FROM journal_lines WHERE journal_entry_id = %s", (je_id,))
    check("je lines count", cur.fetchone()[0] == 2, f"lines={cur.fetchone()[0] if False else ''}")
cur.execute("SELECT movement_type, quantity, reference_type FROM stock_movements WHERE reference_type='PurchaseOrder' ORDER BY created_at DESC LIMIT 3")
movs = cur.fetchall()
print("  stock movements:", movs)
check("stock movements created", len(movs) >= 1, f"count={len(movs)}")
c.close()

print("=" * 60)
print(f"RESULT: {PASS} passed, {FAIL} failed")