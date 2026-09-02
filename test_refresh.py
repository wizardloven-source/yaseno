import requests
from jose import jwt
from api_routers.shared.config import bootstrap, SECRET_KEY, ALGORITHM
from sqlalchemy import text

# Login
r = requests.post('http://localhost:8000/api/auth/login', json={'username': 'admin', 'password': 'Admin@123!'}, timeout=5)
data = r.json()
token = data['access_token']
refresh = data['refresh_token']

decoded = jwt.get_unverified_claims(refresh)
print(f"Refresh JTI: {decoded.get('jti')}")
print(f"Refresh type: {decoded.get('type')}")

with bootstrap.uow() as uow:
    rows = uow.session.execute(
        text("SELECT jti, revoked_at, family_id, generation FROM user_sessions ORDER BY created_at DESC LIMIT 5")
    ).mappings().all()
    for row in rows:
        print(f"  DB: jti={row['jti'][:8]}... revoked={row['revoked_at']} gen={row['generation']}")

# Try refresh
print("\n--- Attempting refresh with token A ---")
r2 = requests.post('http://localhost:8000/api/auth/refresh', json={'token': refresh}, timeout=5)
print(f"Refresh A result: {r2.status_code}")
if r2.status_code == 200:
    new_refresh = r2.json().get('refresh_token', '')
    print("Got new refresh token B")
    
    # Try reuse token A
    print("\n--- Attempting REUSE of token A ---")
    r3 = requests.post('http://localhost:8000/api/auth/refresh', json={'token': refresh}, timeout=5)
    print(f"Reuse A result: {r3.status_code} - {r3.json().get('message', '')[:80]}")
    
    # Check sessions after reuse attempt
    with bootstrap.uow() as uow:
        rows = uow.session.execute(
            text("SELECT jti, revoked_at, revoked_reason FROM user_sessions ORDER BY created_at DESC LIMIT 5")
        ).mappings().all()
        print("\nSessions after reuse attempt:")
        for row in rows:
            print(f"  jti={row['jti'][:8]}... revoked={row['revoked_at']} reason={row['revoked_reason']}")
else:
    print(f"Error: {r2.json().get('detail', '')[:100]}")
