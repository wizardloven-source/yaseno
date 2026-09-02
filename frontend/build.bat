@echo off
set PATH=C:\Program Files\Git\cmd;C:\bin;%PATH%
cd /d C:\Users\MTC\Desktop\yaseeno\frontend
flutter build windows --release
echo BUILD RESULT: %ERRORLEVEL%
