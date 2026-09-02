"""
Script to create new database tables for security features.
Run this once: python create_security_tables.py
"""

import os
import sys
from pathlib import Path

# Load .env
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, text
from core.infrastructure.db.models.account_model import Base
from core.infrastructure.db.models.auth_models import UserSessionModel
from core.infrastructure.db.models.idempotency_model import IdempotencyKeyModel


def create_tables():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set. Copy .env.example to .env and configure it.")
        sys.exit(1)
    
    engine = create_engine(database_url)
    
    print("Creating new security tables...")
    
    # Create user_sessions table
    print("  Creating user_sessions table...")
    UserSessionModel.__table__.create(engine, checkfirst=True)
    
    # Create idempotency_keys table
    print("  Creating idempotency_keys table...")
    IdempotencyKeyModel.__table__.create(engine, checkfirst=True)
    
    print("Done! New tables created successfully.")
    
    # Verify tables exist
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_name IN ('user_sessions', 'idempotency_keys')
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]
        print(f"Verified tables: {', '.join(tables)}")


if __name__ == "__main__":
    create_tables()
