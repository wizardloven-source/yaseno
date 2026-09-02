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
    print("=" * 60)
    print("🚀 YAseen ERP API Server v2.0.0")
    print("=" * 60)
    print(f"📁 Project path: {Path(__file__).parent}")
    print("🌐 API URL: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("=" * 60)
    print()

    uvicorn.run(
        "api:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )

if __name__ == "__main__":
    main()