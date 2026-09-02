import requests
import uuid

# Login
r = requests.post('http://localhost:8000/api/auth/login', json={'username': 'admin', 'password': 'Admin@123!'}, timeout=5)
token = r.json()['access_token']
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

# Create a unique idempotency key
key = str(uuid.uuid4())

# 1st request - should succeed
payload = {'payment_type': 'receive', 'payment_method': 'cash', 'amount': 100, 'currency': 'USD', 'fund_id': 'test'}
r1 = requests.post('http://localhost:8000/api/payments', json=payload, headers={**headers, 'Idempotency-Key': key}, timeout=5)
print(f"1st request: {r1.status_code}")

# 2nd request - SAME key + SAME payload (should return cached response)
r2 = requests.post('http://localhost:8000/api/payments', json=payload, headers={**headers, 'Idempotency-Key': key}, timeout=5)
print(f"2nd request (same key+payload): {r2.status_code}")

# 3rd request - SAME key + DIFFERENT payload (should fail with 422)
payload2 = {'payment_type': 'pay', 'payment_method': 'cash', 'amount': 200, 'currency': 'USD', 'fund_id': 'test'}
r3 = requests.post('http://localhost:8000/api/payments', json=payload2, headers={**headers, 'Idempotency-Key': key}, timeout=5)
print(f"3rd request (same key, different payload): {r3.status_code}")
if r3.status_code == 422:
    print(f"  Error code: {r3.json().get('error_code', 'N/A')}")
    print("  IDEMPOTENCY_KEY_REUSED detected correctly!")
