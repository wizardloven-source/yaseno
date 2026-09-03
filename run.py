# C:\Users\MTC\yaseeno\run.py

"""
نقطة الدخول الرئيسية لتشغيل خادم YAseen ERP API.
"""

import os
import sys
from pathlib import Path
import uvicorn

# إضافة المسار الحالي
sys.path.insert(0, str(Path(__file__).parent))


def main():
    """
    تهيئة وتشغيل خادم Uvicorn.
    """
    from dotenv import load_dotenv
    load_dotenv()

    env = os.getenv("ENV", "development")
    debug = os.getenv("DEBUG", "false").lower() == "true"
    reload = env == "development"

    print("=" * 60)
    print("YAseen ERP API Server v3.0.0")
    print(f"Environment: {env}")
    print(f"Debug: {debug}")
    print(f"Reload: {reload}")
    print("=" * 60)
    print(f"Project path: {Path(__file__).parent}")
    print(f"API URL: http://localhost:8000")
    print(f"API Docs: http://localhost:8000/docs" if reload else "API Docs: DISABLED (production)")
    print("=" * 60)
    print()

    uvicorn.run(
        "api:app", host="0.0.0.0", port=8000, reload=reload, log_level="info"
    )

if __name__ == "__main__":
    main()