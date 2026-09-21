@echo off
setlocal
rem build_exe.bat - يبني الـ exe الواحد (Launcher) عبر PyInstaller.
cd /d "%~dp0"

set PYTHON=C:\Users\MTC\AppData\Local\Programs\Python\Python310\python.exe
set EXE_NAME="YAseen ERP.exe"

if not exist "%PYTHON%" (
    echo لم يُعثر على بايثون في المسار:
    echo %PYTHON%
    pause
    exit /b 1
)

echo [1/3] تثبيت PyInstaller...
"%PYTHON%" -m pip install --upgrade pyinstaller
if errorlevel 1 (
    echo فشل تثبيت PyInstaller.
    pause
    exit /b 1
)

echo [2/3] بناء الـ launcher...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

"%PYTHON%" -m PyInstaller --onefile --windowed --clean --noconfirm ^
    --name "YAseenERP_Launcher" ^
    --distpath dist ^
    launcher.py
if errorlevel 1 (
    echo فشل بناء الـ launcher.
    pause
    exit /b 1
)

echo [3/3] نسخ الـ exe إلى جذر المشروع...
copy /y "dist\YAseenERP_Launcher.exe" "%EXE_NAME%" >nul
if errorlevel 1 (
    echo فشل نسخ الـ exe.
    pause
    exit /b 1
)

echo.
echo تم بنجاح: %EXE_NAME%
pause
endlocal