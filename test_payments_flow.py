# test_payments_flow.py - اختبار اعتماد/إكمال/إلغاء الدفعات
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

print("=" * 60)
print("LOGIN")
r = client.post("/api/auth/login", json={"username": "admin", "password": "Admin@123"})
body = r.json()
headers = {}
if r.status_code == 200:
    headers = {"Authorization": f"Bearer {body['access_token']}"}
check("login", r.status_code == 200 and headers)

rand = str(uuid.uuid4().int)[:6]

print("=" * 60)
print("CUSTOMER")
cust_code = "C" + rand
r = client.post("/api/customers", headers=headers, json={
    "code": cust_code, "name": "عميل اختبار", "email": "c@example.com",
})
cust_id = r.json().get("data", {}).get("id") if r.status_code in (200, 201) else None
check("customer create", bool(cust_id))

print("=" * 60)
print("FUND")
acct_code = "9" + rand
r = client.post("/api/funds", headers=headers, json={
    "code": "F" + rand, "name": "صندوق اختبار", "type": "main",
    "currency": "USD", "opening_balance": "0", "account_code": acct_code,
})
fund_id = r.json().get("data", {}).get("id") if r.status_code in (200, 201) else None
check("fund create", bool(fund_id))

print("=" * 60)
print("CREATE PAYMENT (receive, cash)")
r = client.post("/api/payments", headers=headers, json={
    "payment_type": "receive", "payment_method": "cash", "amount": "150.00",
    "currency": "USD", "customer_id": cust_id, "fund_id": fund_id,
    "description": "قبض اختباري",
})
pb = r.json()
print("  create:", r.status_code, pb.get("message", pb))
pay_id = pb.get("data", {}).get("id") if r.status_code in (200, 201) else None
check("payment create", bool(pay_id))

print("=" * 60)
print("SUBMIT PAYMENT")
r = client.post(f"/api/payments/{pay_id}/submit", headers=headers)
body = r.json()
print("  submit:", r.status_code, body.get("message", body))
check("payment submit", body.get("success") is True, f"status={body.get('data', {}).get('status')}")

print("=" * 60)
print("APPROVE PAYMENT")
r = client.post(f"/api/payments/{pay_id}/approve", headers=headers)
body = r.json()
print("  approve:", r.status_code, body.get("message", body))
check("payment approve", body.get("success") is True, f"status={body.get('data', {}).get('status')}")

print("=" * 60)
print("COMPLETE PAYMENT")
r = client.post(f"/api/payments/{pay_id}/complete", headers=headers)
body = r.json()
print("  complete:", r.status_code, body.get("message", body))
je = body.get("data", {}).get("journal_entry_id") if body.get("success") else None
check("payment complete", body.get("success") is True and bool(je), f"je={je}")
check("payment status completed", body.get("data", {}).get("status") == "completed")

print("=" * 60)
print("DB VERIFY - fund + journal")
import psycopg2
c = psycopg2.connect(host='localhost', dbname='erpya', user='postgres', password='postgres')
cur = c.cursor()
if je:
    cur.execute("SELECT is_posted FROM journal_entries WHERE id = %s", (je,))
    row = cur.fetchone()
    check("je posted", row and row[0] is True)
    cur.execute("SELECT COUNT(*) FROM journal_lines WHERE journal_entry_id = %s", (je,))
    check("je lines = 2", cur.fetchone()[0] == 2)
if fund_id:
    cur.execute("SELECT balance FROM funds WHERE id::text = %s", (fund_id,))
    fb = cur.fetchone()
    print("  fund balance:", fb)
    check("fund balance = 150", fb and float(fb[0]) == 150.0, f"balance={fb}")
c.close()

print("=" * 60)
print("CANCEL PAYMENT")
r = client.post("/api/payments", headers=headers, json={
    "payment_type": "pay", "payment_method": "cash", "amount": "50.00",
    "currency": "USD", "fund_id": fund_id, "description": "دفع للإلغاء",
})
pb = r.json()
pay2 = pb.get("data", {}).get("id") if r.status_code in (200, 201) else None
check("payment2 create", bool(pay2))
if pay2:
    r = client.post(f"/api/payments/{pay2}/cancel", headers=headers, json={"reason": "خطأ في الإدخال"})
    body = r.json()
    print("  cancel:", r.status_code, body.get("message", body))
    check("payment cancel", body.get("success") is True, f"status={body.get('data', {}).get('status')}")

print("=" * 60)
print(f"RESULT: {PASS} passed, {FAIL} failed")