# test_invoices.py - اختبار نقاط الفواتير الكاملة
import os, sys, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fastapi.testclient import TestClient
import api

client = TestClient(api.app)
PASS = FAIL = 0

def check(label, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [OK] {label} {extra}")
    else:
        FAIL += 1
        print(f"  [XX] {label} {extra}")

r = client.post("/api/auth/login", json={"username": "admin", "password": "Admin@123"})
h = {"Authorization": f"Bearer {r.json()['access_token']}"}
rand = str(uuid.uuid4().int)[:6]

# إنشاء عميل
c_code = "CC" + rand
r = client.post("/api/customers", headers=h, json={"code": c_code, "name": "عميل فواتير", "currency": "USD"})
cust_id = r.json().get("data", {}).get("id")
check("customer create", r.status_code == 201 and cust_id, f"status={r.status_code}")

# إنشاء منتج بكمية مخزون
p_code = "PC" + rand
r = client.post("/api/products", headers=h, json={
    "code": p_code, "name": "منتج فاتورة", "unit_price": "10", "tax_rate": "5",
    "category": "test", "stock_quantity": 500, "low_stock_threshold": 5
})
check("product create", r.status_code == 201, f"status={r.status_code}")
prod_id = r.json().get("data", {}).get("id")

# بذر مخزون وارد للبضاعة (الترحيل يعتمد على حركات المخزون)
from core.bootstrap.startup import init_bootstrap
from core.domain.inventory.services import StockMovementService
from core.domain.inventory.value_objects import EntityId, StockMovementType, Money as InvMoney
from decimal import Decimal as D
b = init_bootstrap(database_url='postgresql://postgres:postgres@localhost:5432/erpya', seed_data=False)
with b.container.scope() as scope:
    uow = scope.resolve("uow")
    with uow:
        svc = StockMovementService(uow.stock_movements)
        svc.create_inbound_movement(
            entity=EntityId(prod_id),
            quantity=D('100'),
            unit_cost=InvMoney(D('7'), 'USD'),
            movement_type=StockMovementType.PURCHASE,
            reference_type="TestSeed",
            reference_id="seed-" + rand,
            created_by="admin"
        )
        uow.commit()
check("stock seeded", True, f"product={prod_id}")

# إنشاء حساب + صندوق للدفع النقدي
acct_code = "5" + rand
r = client.post("/api/accounts", headers=h, json={
    "code": acct_code, "name": "حساب فاتورة", "account_type": "asset",
    "currency": "USD", "is_active": True
})
print("  account:", r.status_code, r.json().get("message", r.json())[:60])
fund_code = "FC" + rand
r = client.post("/api/funds", headers=h, json={
    "code": fund_code, "name": "صندوق فواتير", "account_code": acct_code,
    "fund_type": "main", "currency": "USD", "opening_balance": "5000",
})
fund_id = r.json().get("data", {}).get("id")
check("fund create", r.status_code == 201 and fund_id, f"status={r.status_code} body={r.json()}")

# إنشاء فاتورة بدون بنود
r = client.post("/api/invoices", headers=h, json={
    "customer_id": cust_id, "customer_name": "عميل فواتير", "currency": "USD",
    "payment_type": "cash", "fund_id": fund_id, "notes": "فاتورة اختبار",
})
inv_id = r.json().get("data", {}).get("id")
check("invoice create", r.status_code == 201 and inv_id, f"status={r.status_code} body={r.json()}")

# إضافة سطر
if inv_id:
    r = client.post(f"/api/invoices/{inv_id}/lines", headers=h, json={
        "product_code": p_code, "product_name": "منتج فاتورة", "quantity": "10", "unit_price": "10", "currency": "USD"
    })
    check("invoice add line", r.status_code == 201, f"status={r.status_code} body={r.json()}")
    line_id = r.json().get("data", {}).get("lines", [{}])[0].get("line_id") if r.json().get("data", {}).get("lines") else None

    # جلب الفاتورة
    r = client.get(f"/api/invoices/{inv_id}", headers=h)
    check("invoice get", r.status_code == 200, f"status={r.status_code}")
    data = r.json().get("data", {})
    check("invoice has 1 line", len(data.get("lines", [])) == 1, f"lines={len(data.get('lines', []))}")
    check("invoice total", abs(float(data.get("total", 0)) - 100.0) < 0.01, f"total={data.get('total')}")

    # ترحيل الفاتورة
    r = client.post(f"/api/invoices/{inv_id}/post", headers=h, json={})
    print("  post:", r.status_code, r.json().get("message", r.json())[:100])
    check("invoice post", r.status_code == 200 and r.json().get("success"), f"status={r.status_code}")

    # جلب بعد الترحيل
    r = client.get(f"/api/invoices/{inv_id}", headers=h)
    data = r.json().get("data", {})
    check("invoice posted status", data.get("status") == "posted", f"status={data.get('status')}")
    check("invoice journal entry", bool(data.get("journal_entry_id")), f"je={data.get('journal_entry_id')}")

print(f"RESULT: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)