import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.bootstrap.startup import init_bootstrap

b = init_bootstrap(
    database_url=os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/erpya"),
    echo_sql=False,
    seed_data=False,
)

with b.uow() as uow:
    try:
        user = uow.users.get_by_username("admin")
        print("admin user:", user)
        if user:
            print("is_active:", user.is_active)
            print("password_hash:", (user.password_hash or "")[:30])
            print("roles:", [r.name for r in user.roles])
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("ERR get_by_username:", type(e).__name__, e)