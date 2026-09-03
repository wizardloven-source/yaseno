from api_routers.shared.config import bootstrap
from sqlalchemy import text

with bootstrap.uow() as uow:
    rows = uow.session.execute(text("SELECT username, is_active FROM users ORDER BY created_at DESC LIMIT 5")).mappings().all()
    for r in rows:
        print("User:", r["username"], "active:", r["is_active"])
