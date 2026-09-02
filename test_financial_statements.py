# test_financial_statements.py
import json
import urllib.request

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

    # Income statement
    status, r = call("POST", "/api/reports/income-statement",
                     {"period_start": "2026-01-01", "period_end": "2026-12-31", "currency": "USD"},
                     token)
    print(f"income-statement -> {status} success={r.get('success')}")
    assert status == 200 and r.get("success"), f"income-statement failed: {r}"
    data = r["data"]
    print("  sections:", len(data.get("sections", [])) if isinstance(data, dict) else type(data))

    # Balance sheet
    status, r = call("POST", "/api/reports/balance-sheet",
                     {"as_of_date": "2026-12-31", "currency": "USD"},
                     token)
    print(f"balance-sheet -> {status} success={r.get('success')}")
    assert status == 200 and r.get("success"), f"balance-sheet failed: {r}"

    # Cash flow
    status, r = call("POST", "/api/reports/cash-flow",
                     {"period_start": "2026-01-01", "period_end": "2026-12-31", "currency": "USD", "method": "indirect"},
                     token)
    print(f"cash-flow -> {status} success={r.get('success')}")
    assert status == 200 and r.get("success"), f"cash-flow failed: {r}"

    # List statements
    status, r = call("GET", "/api/reports/financial-statements?limit=50", None, token)
    print(f"list-statements -> {status} {r}")
    assert status == 200 and r.get("success"), f"list failed: {r}"

    print("RESULT: PASS")


if __name__ == "__main__":
    main()