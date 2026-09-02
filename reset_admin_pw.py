import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.bootstrap.startup import init_bootstrap
from core.application.security.password_hasher import PasswordHasher

b = init_bootstrap(
    database_url=os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/erpya"),
    echo_sql=False,
    seed_data=False,
)

new_hash = PasswordHasher.hash("Admin@123")
with b.uow() as uow:
    user = uow.users.get_by_username("admin")
    if not user:
        print("ERROR: admin user not found")
        sys.exit(1)
    user.password_hash = new_hash
    uow.users.save(user)
    uow.commit()
    print("Admin password reset to 'Admin@123'")
    print("verify:", PasswordHasher.verify("Admin@123", user.password_hash))