# -*- coding: utf-8 -*-
"""Workflow API test"""
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
    u = uuid.uuid4().hex[:6]

    # ============ WORKFLOW ============
    wcode = f"WF-{u}"
    st, r = api("POST", "/api/workflows", {
        "name": f"PO Approval {u}",
        "code": wcode,
        "entity_type": "purchase_order",
        "steps": [
            {"name": "Manager", "order": 1, "role": "manager", "required_approvals": 1, "requires_all": False, "is_final": False},
            {"name": "Director", "order": 2, "role": "director", "required_approvals": 1, "requires_all": False, "is_final": True},
        ],
        "description": "workflow test",
        "is_mandatory": True,
    }, token)
    results.append(ok("create workflow", st, r))
    wf = (r.get("data") or {})
    wid = wf.get("id") or wf.get("workflow_id")

    st, r = api("GET", f"/api/workflows/{wid}", token=token)
    results.append(ok("get workflow", st, r))

    st, r = api("GET", "/api/workflows", token=token)
    results.append(ok("list workflows", st, r))

    st, r = api("GET", "/api/workflows/by-entity/purchase_order", token=token)
    results.append(ok("get workflow by entity", st, r))

    st, r = api("POST", f"/api/workflows/{wid}/activate", token=token)
    results.append(ok("activate workflow", st, r))

    st, r = api("PUT", f"/api/workflows/{wid}", {"description": "updated desc"}, token)
    results.append(ok("update workflow", st, r))

    # ============ APPROVAL REQUESTS ============
    eid = f"PO-{u}"
    st, r = api("POST", "/api/approval-requests", {
        "entity_type": "purchase_order",
        "entity_id": eid,
        "title": f"Approve PO {eid}",
        "description": "please approve",
        "amount": 1200,
        "currency": "USD",
        "priority": "high",
    }, token)
    results.append(ok("create approval request", st, r))
    req = (r.get("data") or {})
    rid = req.get("id") or req.get("request_id")

    st, r = api("POST", f"/api/approval-requests/{rid}/submit", token=token)
    results.append(ok("submit request", st, r))

    st, r = api("GET", f"/api/approval-requests/{rid}", token=token)
    results.append(ok("get request", st, r))

    st, r = api("POST", f"/api/approval-requests/{rid}/approve", {"approver_id": "manager1", "approver_name": "Manager One"}, token)
    results.append(ok("approve request", st, r))

    # second request -> reject
    st, r = api("POST", "/api/approval-requests", {
        "entity_type": "purchase_order",
        "entity_id": f"PO2-{u}",
        "title": f"Reject me {u}",
        "amount": 50,
    }, token)
    r2 = (r.get("data") or {})
    rid2 = r2.get("id") or r2.get("request_id")
    st, r = api("POST", f"/api/approval-requests/{rid2}/submit", token=token)
    results.append(ok("submit request 2", st, r))
    st, r = api("POST", f"/api/approval-requests/{rid2}/reject", {"approver_id": "manager1", "reason": "not enough info"}, token)
    results.append(ok("reject request 2", st, r))

    st, r = api("GET", "/api/approval-requests/pending", token=token)
    results.append(ok("list pending", st, r))

    st, r = api("GET", "/api/approval-requests/statistics", token=token)
    results.append(ok("get statistics", st, r))

    # escalate / reassign on a fresh request
    st, r = api("POST", "/api/approval-requests", {
        "entity_type": "purchase_order", "entity_id": f"PO3-{u}", "title": f"Escalate {u}",
    }, token)
    r3 = (r.get("data") or {})
    rid3 = r3.get("id") or r3.get("request_id")
    st, r = api("POST", f"/api/approval-requests/{rid3}/submit", token=token)
    results.append(ok("submit request 3", st, r))
    st, r = api("POST", f"/api/approval-requests/{rid3}/escalate", {"reason": "urgent"}, token)
    results.append(ok("escalate request", st, r))
    st, r = api("POST", f"/api/approval-requests/{rid3}/reassign", {"new_approver_id": "director1", "new_approver_name": "Director One"}, token)
    results.append(ok("reassign request", st, r))

    # batch approve
    st, r = api("POST", "/api/approval-requests", {
        "entity_type": "purchase_order", "entity_id": f"PO4-{u}", "title": f"Batch {u}",
    }, token)
    r4 = (r.get("data") or {})
    rid4 = r4.get("id") or r4.get("request_id")
    st, r = api("POST", f"/api/approval-requests/{rid4}/submit", token=token)
    st, r = api("POST", "/api/approval-requests/batch-approve", {"request_ids": [rid4], "comment": "ok"}, token)
    results.append(ok("batch approve", st, r))

    st, r = api("POST", f"/api/workflows/{wid}/deactivate", token=token)
    results.append(ok("deactivate workflow", st, r))

    print(f"\nPASS {results.count(True)}/{len(results)}")
    return 0 if all(results) else 1

if __name__ == "__main__":
    raise SystemExit(main())