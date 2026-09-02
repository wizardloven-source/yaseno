# -*- coding: utf-8 -*-
"""Basic Units API test - currencies, sites, centers, settings, customer branches"""
import json
import random
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
    ok_status = st == want
    ok_success = resp.get("success") in (None, True) or st != 200
    print(f"{label} -> {st} success={resp.get('success')} msg={str(resp.get('message'))[:80]}")
    if not ok_status or (st == 200 and resp.get("success") is False):
        print(f"   ERR: {json.dumps(resp, ensure_ascii=False)[:300]}")
        return False
    return True

def main():
    token = login()
    print("LOGIN OK")
    results = []
    u = uuid.uuid4().hex[:8]

    # ============ CURRENCY ============
    ccode = ''.join(random.choice('ABCDEFGHJKLMNPQRSTUVWXYZ') for _ in range(3))
    st, r = api("POST", "/api/currency", {"code": ccode, "name": f"Test Currency {u}"}, token)
    results.append(ok("create currency", st, r))
    cur = (r.get("data") or {})
    cid = cur.get("id") or cur.get("currency_id")
    if cid:
        st, r = api("GET", f"/api/currency/{cid}", token=token)
        results.append(ok("get currency", st, r))
    st, r = api("GET", "/api/currency", token=token)
    results.append(ok("list currencies", st, r))
    st, r = api("GET", f"/api/currency/by-code/{ccode}", token=token)
    results.append(ok("get currency by code", st, r))
    st, r = api("GET", "/api/currency/base", token=token)
    results.append(ok("get base currency", st, r))
    st, r = api("GET", "/api/currency/exchange-rate?from_currency_code=USD&to_currency_code=EUR", token=token)
    results.append(ok("get exchange rate", st, r))
    if cid:
        st, r = api("POST", f"/api/currency/{cid}/exchange-rate", {"to_currency_code": "EUR", "rate": 0.92}, token)
        results.append(ok("set exchange rate", st, r))
        st, r = api("GET", f"/api/currency/{cid}", token=token)
        cver = (r.get("data") or {}).get("version", 1)
        st, r = api("PUT", f"/api/currency/{cid}", {"name": f"Updated {u}", "version": cver}, token)
        results.append(ok("update currency", st, r))
        st, r = api("DELETE", f"/api/currency/{cid}", token=token)
        results.append(ok("delete currency", st, r))
        st, r = api("POST", "/api/currency", {"code": ''.join(random.choice('ABCDEFGHJKLMNPQRSTUVWXYZ') for _ in range(3)), "name": f"Base {u}"}, token)
        results.append(ok("create base currency", st, r))
        bcur = (r.get("data") or {})
        bid = bcur.get("id")
        if bid:
            st, r = api("POST", f"/api/currency/{bid}/base", token=token)
            results.append(ok("set base currency", st, r))

    # ============ SITES ============
    st, r = api("POST", "/api/sites", {"code": f"S{u}", "name": f"Test Site {u}", "city": "Beirut"}, token)
    results.append(ok("create site", st, r))
    site = (r.get("data") or {})
    sid = site.get("id") or site.get("site_id")
    if sid:
        st, r = api("GET", f"/api/sites/{sid}", token=token)
        results.append(ok("get site", st, r))
        st, r = api("GET", f"/api/sites/{sid}/statistics", token=token)
        results.append(ok("get site statistics", st, r))
        st, r = api("POST", f"/api/sites/{sid}/default", token=token)
        results.append(ok("set default site", st, r))
        st, r = api("GET", f"/api/sites/{sid}", token=token)
        sver = (r.get("data") or {}).get("version", 1)
        st, r = api("PUT", f"/api/sites/{sid}", {"name": f"Site Updated {u}", "version": sver}, token)
        results.append(ok("update site", st, r))
    st, r = api("GET", "/api/sites", token=token)
    results.append(ok("list sites", st, r))
    st, r = api("GET", "/api/sites/default", token=token)
    results.append(ok("get default site", st, r))
    st, r = api("GET", "/api/sites/search?q=Test", token=token)
    results.append(ok("search sites", st, r))
    st, r = api("GET", "/api/sites/combo", token=token)
    results.append(ok("get sites for combo", st, r))

    # ============ CENTERS ============
    c1, c2 = f"CC{u}A", f"CC{u}B"
    st, r = api("POST", "/api/centers", {"code": c1, "name": f"Center A {u}", "center_type": "cost"}, token)
    results.append(ok("create center A", st, r))
    center_a = (r.get("data") or {})
    ca_id = center_a.get("id")
    st, r = api("POST", "/api/centers", {"code": c2, "name": f"Center B {u}", "center_type": "profit"}, token)
    results.append(ok("create center B", st, r))
    st, r = api("GET", "/api/centers", token=token)
    results.append(ok("list centers", st, r))
    st, r = api("GET", "/api/centers/tree", token=token)
    results.append(ok("get center tree", st, r))
    st, r = api("GET", f"/api/centers/{c1}/summary?from_date=2026-01-01&to_date=2026-12-31", token=token)
    results.append(ok("get center summary", st, r))
    if ca_id:
        st, r = api("GET", f"/api/centers/{ca_id}", token=token)
        results.append(ok("get center", st, r))
        st, r = api("POST", f"/api/centers/{ca_id}/activate", token=token)
        results.append(ok("activate center", st, r))
        st, r = api("GET", f"/api/centers/{ca_id}", token=token)
        cver = (r.get("data") or {}).get("version", 1)
        st, r = api("PUT", f"/api/centers/{ca_id}", {"version": cver, "name": f"Center A Upd {u}"}, token)
        results.append(ok("update center", st, r))
    st, r = api("POST", "/api/centers/allocations", {
        "source_center_code": c1,
        "target_center_codes": [c2],
        "amount": "100.00",
        "period_start": "2026-01-01",
        "period_end": "2026-12-31",
        "method": "equal",
    }, token)
    results.append(ok("create allocation", st, r))
    alloc_id = (r.get("data") or {}).get("id")
    if alloc_id:
        st, r = api("POST", f"/api/centers/allocations/{alloc_id}/post", token=token)
        results.append(ok("post allocation", st, r))

    # ============ SETTINGS ============
    st, r = api("GET", "/api/settings", token=token)
    results.append(ok("get settings", st, r))
    st, r = api("GET", "/api/settings/ui", token=token)
    results.append(ok("get UI settings", st, r))
    st, r = api("PUT", "/api/settings/ui", {"theme": "dark", "language": "ar"}, token)
    results.append(ok("update UI settings", st, r))
    st, r = api("PUT", "/api/settings", {"ui": {"font_size": 14}}, token)
    results.append(ok("update all settings", st, r))

    # ============ CUSTOMER BRANCHES ============
    cust_id = str(uuid.uuid4())
    st, r = api("POST", f"/api/customers/{cust_id}/branches",
                {"code": f"BR{u}", "name": f"Branch {u}", "customer_name": "Test Customer"}, token)
    results.append(ok("create branch", st, r))
    br = (r.get("data") or {})
    bid = br.get("id") or br.get("branch_id")
    if bid:
        st, r = api("GET", f"/api/branches/{bid}", token=token)
        results.append(ok("get branch", st, r))
        st, r = api("GET", f"/api/branches/by-code/BR{u}", token=token)
        results.append(ok("get branch by code", st, r))
        st, r = api("PUT", f"/api/branches/{bid}", {"version": 1, "name": f"Branch Upd {u}"}, token)
        results.append(ok("update branch", st, r))
        st, r = api("POST", f"/api/branches/{bid}/default", {"customer_id": cust_id}, token)
        results.append(ok("set default branch", st, r))
        st, r = api("POST", f"/api/branches/{bid}/deactivate", token=token)
        results.append(ok("deactivate branch", st, r))
        st, r = api("POST", f"/api/branches/{bid}/activate", token=token)
        results.append(ok("activate branch", st, r))
    st, r = api("GET", f"/api/branches?customer_id={cust_id}", token=token)
    results.append(ok("list branches", st, r))
    st, r = api("GET", f"/api/branches/default?customer_id={cust_id}", token=token)
    results.append(ok("get default branch", st, r))
    st, r = api("GET", "/api/branches/search?q=Branch", token=token)
    results.append(ok("search branches", st, r))

    passed = sum(1 for x in results if x)
    print(f"RESULT: {'PASS' if passed == len(results) else 'FAIL'} ({passed}/{len(results)} passed)")

if __name__ == "__main__":
    main()