# test_inventory.py
import json
import urllib.request
import uuid

BASE = "http://127.0.0.1:8000"


def call(method, path, body=None, token=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def main():
    status, login = call("POST", "/api/auth/login", {"username": "admin", "password": "Admin@123"})
    assert status == 200, f"login failed: {login}"
    token = login.get("data", {}).get("access_token") or login.get("access_token")
    print("LOGIN OK")

    # 1. Create a product
    status, r = call("POST", "/api/products", {
        "name": "Item INV Test",
        "code": f"INV-{uuid.uuid4().hex[:8].upper()}",
        "unit_cost": "10.00",
        "price": "25.00",
        "stock_quantity": 0,
        "low_stock_threshold": 5,
    }, token)
    print(f"create product -> {status}")
    assert status in (200, 201), f"create product failed: {r}"
    product = r.get("data", {})
    pid = product.get("id") or product.get("product", {}).get("id") if isinstance(product, dict) else None
    if not pid:
        for key in ("id", "product_id"):
            if isinstance(product, dict) and product.get(key):
                pid = product[key]
                break
    assert pid, f"no product id in response: {r}"
    print(f"  product id: {pid}")

    # 2. Inbound purchase movement
    status, r = call("POST", "/api/inventory/movements/purchase", {
        "entity_type": "product",
        "entity_id": pid,
        "quantity": 100,
        "unit_cost": 10,
        "purchase_order_id": "TEST-PO-1",
    }, token)
    print(f"purchase movement -> {status} {r.get('message')}")
    assert status == 200 and r.get("success"), f"purchase movement failed: {r}"

    # 3. Quantity
    status, r = call("GET", f"/api/inventory/product/{pid}/quantity", None, token)
    print(f"quantity -> {status} {r.get('data')}")
    assert status == 200 and r.get("success"), f"quantity failed: {r}"
    assert float(r["data"]["quantity"]) == 100, f"expected 100, got {r['data']['quantity']}"

    # 4. Outbound sale movement
    status, r = call("POST", "/api/inventory/movements/sale", {
        "entity_type": "product",
        "entity_id": pid,
        "quantity": 40,
        "unit_cost": 10,
        "invoice_id": "TEST-INV-1",
    }, token)
    print(f"sale movement -> {status} {r.get('message')}")
    assert status == 200 and r.get("success"), f"sale movement failed: {r}"

    # 5. Quantity after sale
    status, r = call("GET", f"/api/inventory/product/{pid}/quantity", None, token)
    print(f"quantity after sale -> {r.get('data')}")
    assert float(r["data"]["quantity"]) == 60, f"expected 60, got {r['data']['quantity']}"

    # 6. Movements list
    status, r = call("GET", f"/api/inventory/product/{pid}/movements?limit=50", None, token)
    print(f"movements -> {status} total={r.get('data', {}).get('total')}")
    assert status == 200 and r.get("success"), f"movements failed: {r}"
    assert r["data"]["total"] >= 2

    # 7. Low stock (threshold high enough to include it)
    status, r = call("GET", "/api/inventory/low-stock?threshold=1000&limit=50", None, token)
    print(f"low-stock -> {status} total={r.get('data', {}).get('total')}")
    assert status == 200 and r.get("success"), f"low-stock failed: {r}"

    # 8. Create batch
    status, r = call("POST", "/api/inventory/batches", {
        "entity_type": "product",
        "entity_id": pid,
        "batch_number": f"BATCH-{uuid.uuid4().hex[:8].upper()}",
        "quantity": 50,
        "unit_cost": 9,
    }, token)
    print(f"create batch -> {status} {r.get('message')}")
    assert status == 200 and r.get("success"), f"create batch failed: {r}"
    batch_id = (r.get("data") or {}).get("id")
    assert batch_id, f"no batch id: {r}"

    # 9. Consume batch
    status, r = call("POST", f"/api/inventory/batches/{batch_id}/consume", {
        "quantity": 20,
        "reference_type": "sale",
        "reference_id": "TEST-INV-2",
    }, token)
    print(f"consume batch -> {status} {r.get('message')}")
    assert status == 200 and r.get("success"), f"consume batch failed: {r}"

    # 10. Create transfer
    status, r = call("POST", "/api/inventory/transfers", {
        "entity_type": "product",
        "entity_id": pid,
        "quantity": 10,
        "unit_cost": 10,
        "from_location": "main",
        "to_location": "secondary",
    }, token)
    print(f"create transfer -> {status} {r.get('message')}")
    assert status == 200 and r.get("success"), f"create transfer failed: {r}"
    transfer_id = (r.get("data") or {}).get("id")
    assert transfer_id, f"no transfer id: {r}"

    # 11. Complete transfer
    status, r = call("POST", f"/api/inventory/transfers/{transfer_id}/complete", None, token)
    print(f"complete transfer -> {status} {r.get('message')}")
    assert status == 200 and r.get("success"), f"complete transfer failed: {r}"

    # 12. Valuation
    status, r = call("GET", f"/api/inventory/product/{pid}/valuation?as_of_date=2026-12-31&method=fifo", None, token)
    print(f"valuation -> {status} {r.get('data') if r.get('success') else r.get('message')}")
    assert status == 200 and r.get("success"), f"valuation failed: {r}"

    print("RESULT: PASS")


if __name__ == "__main__":
    main()