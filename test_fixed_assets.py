# -*- coding: utf-8 -*-
"""Fixed Assets API test"""
import json
import uuid
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE = "http://127.0.0.1:8000"

def api(method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8", errors="replace"))
    except HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8", errors="replace"))
        except Exception:
            return e.code, {}

def login():
    st, resp = api("POST", "/api/auth/login", {"username": "admin", "password": "Admin@123"})
    assert st == 200, f"login failed {st}: {resp}"
    tok = resp.get("access_token") or (resp.get("data") or {}).get("access_token")
    assert tok, f"no token: {resp}"
    return tok

def ok(label, st, resp, want=200):
    failed = st != want or (st == 200 and resp.get("success") is False)
    print(f"{label} -> {st} success={resp.get('success')} msg={str(resp.get('message'))[:80]}")
    if failed:
        print(f"   ERR: {json.dumps(resp, ensure_ascii=False)[:300]}")
        return False
    return True

def main():
    token = login()
    print("LOGIN OK")
    results = []
    u = uuid.uuid4().hex[:8]

    # ============ CREATE ============
    code = f"FA-{u[:6]}"
    st, r = api("POST", "/api/assets", {
        "code": code,
        "name": f"Delivery Vehicle {u[:6]}",
        "acquisition_cost": 15000,
        "acquisition_date": "2025-01-15",
        "asset_type": "vehicle",
        "useful_life_years": 5,
        "salvage_value": 1000,
        "depreciation_method": "straight_line",
        "currency": "USD",
        "category": "transport",
        "location": "Main Warehouse",
        "responsible_person": "ali",
        "notes": "test asset",
    }, token)
    results.append(ok("create asset", st, r))
    asset = (r.get("data") or {})
    aid = asset.get("id") or asset.get("asset_id")
    if not aid:
        aid = code
    else:
        st, r = api("GET", f"/api/assets/{aid}", token=token)
        results.append(ok("get asset", st, r))

    st, r = api("GET", "/api/assets", token=token)
    results.append(ok("list assets", st, r))

    # ============ DEPRECIATION ============
    st, r = api("POST", f"/api/assets/{aid}/depreciation", {"period": 1}, token)
    results.append(ok("post depreciation p1", st, r))
    st, r = api("POST", f"/api/assets/{aid}/depreciation", {"period": 2}, token)
    results.append(ok("post depreciation p2", st, r))

    st, r = api("POST", "/api/assets/run-depreciation", {}, token)
    results.append(ok("run monthly depreciation", st, r))

    # ============ DISPOSE ============
    st, r = api("POST", f"/api/assets/{aid}/dispose", {
        "disposal_date": "2026-01-20",
        "disposal_method": "sale",
        "sale_amount": 5000,
        "reason": "sold",
    }, token)
    results.append(ok("dispose asset", st, r))

    print(f"\nPASS {results.count(True)}/{len(results)}")
    return 0 if all(results) else 1

if __name__ == "__main__":
    raise SystemExit(main())