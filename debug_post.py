import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import traceback

from fastapi.testclient import TestClient
import api

client = TestClient(api.app)
r = client.post("/api/auth/login", json={"username": "admin", "password": "Admin@123"})
headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

r = client.get("/api/journal-entries", headers=headers)
entry_id = r.json()["data"]["items"][0]["id"]

bootstrap = api.bootstrap
from core.domain.accounting.value_objects import JournalEntryId

with bootstrap.uow() as uow:
    entry = uow.journal_entries.get_by_id(JournalEntryId.from_string(entry_id))
    engine = bootstrap.container.resolve("posting_engine")
    try:
        result = engine.post(entry, "admin", skip_save=True)
        print("POST OK:", result.success, result.message)
    except Exception:
        traceback.print_exc()