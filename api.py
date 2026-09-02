# api.py
"""
YAseen ERP - FastAPI REST API (Thin Wrapper)
All endpoints are defined in api_routers/ directory.
This file only bootstraps the app and includes routers.
"""
import sys
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent))

# Import the app and register all routers
from api_routers.router import app  # noqa: F401

# =============================================================================
# تشغيل الخادم
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    import os
    ENV = os.getenv("ENV", "development")
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=(ENV == "development"),
    )
