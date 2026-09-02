@echo off
cd /d C:\Users\MTC\Desktop\yaseeno
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
"C:\Users\MTC\AppData\Local\Programs\Python\Python310\python.exe" -m uvicorn api:app --host 0.0.0.0 --port 8000
