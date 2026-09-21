# launcher.py
"""
YAseen ERP Launcher.

يُحوَّل هذا الملف إلى exe واحد (PyInstaller --onefile --windowed).
يقوم:
  1) بتشغيل خادم الفاست API في الخلفية بدون أي نافذة أوامر
     (عبر run.py، ويضبط ENV=production لإيقاف reload).
  2) بانتظار جاهزية الخادم عبر /api/health.
  3) بفتح تطبيق Flutter النهائي.
  4) بمراقبة التطبيق وعند إغلاقه يوقف الخادم الذي أطلقه فقط.
"""

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import ctypes  # لإخفاء نافذة الأوامر عند الاطلاع (Console Window)

HEALTH_URL = "http://127.0.0.1:8000/api/health"
TIMEOUT_SECONDS = 60
POLL_SECONDS = 0.5

RELATIVE_APP_EXE = Path(r"frontend\build\windows\x64\runner\Release\ya_seen_erp_flutter.exe")


def base_dir() -> Path:
    """مجلد الـ exe (عند التجميد) أو مجلد المشروع (عند التطوير)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def show_error(message: str) -> None:
    """نجد بلا نافذة أوامر: نعرض MessageBox عبر Win32."""
    try:
        ctypes.windll.user32.MessageBoxW(
            None, message, "YAseen ERP", 0x10  # MB_ICONERROR
        )
    except Exception:
        print(message)


def is_healthy(timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def server_already_running() -> bool:
    """تجريبي: خادم مفتوح مسبقاً (من مستخدم أصلاً)؟"""
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def find_python() -> Path | None:
    """بايثون موثوق: عند التجميد نستخدم المفسِّر الأصلي للمنظومة."""
    candidates = []
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_base_executable", None)
        if base:
            candidates.append(Path(base))
    candidates.append(Path(sys.executable))
    for py in candidates:
        if py.exists():
            # تحقق من توفر uvicorn
            try:
                r = subprocess.run(
                    [str(py), "-m", "uvicorn", "--version"],
                    capture_output=True,
                    timeout=15,
                )
                if r.returncode == 0:
                    return py
            except Exception:
                continue
    return None


def start_server(python: Path, root: Path) -> subprocess.Popen | None:
    env = dict(os.environ)
    env["ENV"] = "production"  # تعطيل reload حتى يمكن قتل العملية مباشرةً
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NO_WINDOW  # إخفاء نافذة أوامر
    try:
        return subprocess.Popen(
            [str(python), "run.py"],
            cwd=str(root),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
    except Exception as e:
        show_error(f"تعذر تشغيل الخادم:\n{e}")
        return None


def wait_healthy(server: subprocess.Popen | None, already_up: bool) -> bool:
    if already_up:
        return True
    deadline = time.time() + TIMEOUT_SECONDS
    while time.time() < deadline:
        if server is not None and server.poll() is not None:
            return False  # توقف الخادم قبل الجاهزية
        if is_healthy(timeout=0.5):
            return True
        time.sleep(POLL_SECONDS)
    return False


def stop_server(pid: int) -> None:
    if not pid:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                timeout=10,
            )
        except Exception:
            pass
    else:
        try:
            os.kill(pid, 9)
        except Exception:
            pass


def wait_app_closed(app_exe: Path) -> None:
    image = app_exe.name
    while True:
        time.sleep(2)
        # هل ما زالت العملية موجودة؟
        running = False
        try:
            if os.name == "nt":
                out = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {image}"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                ).stdout
                running = image.lower() in out.lower() and "no tasks" not in out.lower()
            else:
                out = subprocess.run(
                    ["pgrep", "-f", str(app_exe)], capture_output=True, text=True, timeout=10
                ).stdout
                running = bool(out.strip())
        except Exception:
            return
        if not running:
            return


def launch_app(app_exe: Path) -> None:
    try:
        if os.name == "nt":
            flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
            subprocess.Popen(
                [str(app_exe)], cwd=str(app_exe.parent),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=flags, close_fds=True,
            )
        else:
            subprocess.Popen(
                [str(app_exe)], cwd=str(app_exe.parent),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True, close_fds=True,
            )
    except Exception as e:
        show_error(f"تعذر فتح تطبيق YAseen ERP:\n{e}")


def main() -> int:
    root = base_dir()
    app_exe = root / RELATIVE_APP_EXE
    if not app_exe.exists():
        # إن كان الـ launcher في مجلد dist، نرجو المسار من جذر المشروع المجاور.
        alt = root.parent / RELATIVE_APP_EXE
        if alt.exists():
            app_exe = alt

    already_up = server_already_running()
    server = None

    if not already_up:
        python = find_python()
        if python is None:
            show_error(
                "تعذر العثور على بايثون بتثبيت uvicorn.\n"
                "تأكد من تشغيل:  pip install -r requirements.txt"
            )
            return 1
        # تأكد أن run.py موجود بمحاذاة الـ launcher
        run_py = root / "run.py"
        if not run_py.exists():
            run_py = root.parent / "run.py"
        if not run_py.exists():
            show_error("لم يُعثر على run.py بجوار الـ launcher.")
            return 1
        server = start_server(python, root)

    if not wait_healthy(server, already_up):
        stop_server(server.pid if server else 0)
        show_error(
            "لم يستجب الخادم خلال 60 ثانية.\n"
            "تحقق من قاعدة البيانات/الإعدادات ثم أعد المحاولة."
        )
        return 1

    if not app_exe.exists():
        if already_up:
            show_error(
                "تم تشغيل الخادم، لكن لم يُعثر على ملف التطبيق:\n"
                f"{app_exe}"
            )
        else:
            show_error(f"لم يُعثر على ملف التطبيق:\n{app_exe}")
        stop_server(server.pid if server else 0)
        return 1

    launch_app(app_exe)
    wait_app_closed(app_exe)
    stop_server(server.pid if server else 0)
    return 0


if __name__ == "__main__":
    sys.exit(main())