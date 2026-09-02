from passlib.context import CryptContext
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
h = "$2b$12$giq1M/SESuM9Iy/pwMZlheCpMp0UN6lOhHmq9BiSl8n3CorkaOXOC"
for pw in ["admin123", "Admin@123"]:
    print(pw, "->", pwd.verify(pw, h))