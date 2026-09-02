import bcrypt
h = "$2b$12$giq1M/SESuM9Iy/pwMZlheCpMp0UN6lOhHmq9BiSl8n3CorkaOXOC"
print("hash len:", len(h))
for pw in ["admin123", "Admin@123", "admin", "admin@123", "Admin123"]:
    print(repr(pw), "->", bcrypt.checkpw(pw.encode("utf-8"), h.encode("utf-8")))