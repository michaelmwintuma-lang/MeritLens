"""
Run the browser checks against a throwaway copy of the app:   python scripts/browser_test.py            (or with a check's name, or another script:
                                                        python scripts/browser_test.py scripts/capture_landing.js)

Starts its own backend (port 8001) on a new, temporary database with the demo accounts, and its own frontend
(port 5174), runs scripts/browser_checks.js against them, then stops both and deletes the temporary data. Your
real database (backend/instance/app.db) is never touched, and your private backend/.env is not read, so no real
email can be sent. The normal app on ports 8000 and 5173 can keep running meanwhile.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND, FRONTEND = ROOT / "backend", ROOT / "frontend"
# The backend's own environment if there is one (as on a developer's PC), otherwise the Python running this (as in CI)
_VENV_PYTHON = BACKEND / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
PYTHON = _VENV_PYTHON if _VENV_PYTHON.exists() else Path(sys.executable)
NPX = "npx.cmd" if os.name == "nt" else "npx"
# Other programs sometimes hold 8001 (Cisco Packet Tracer does): choose other ports with TEST_API_PORT / TEST_WEB_PORT
API_PORT, WEB_PORT = int(os.getenv("TEST_API_PORT", "8001")), int(os.getenv("TEST_WEB_PORT", "5174"))
WSL_PYTHON = "$HOME/venvs/hr-simple/bin/python"  # made by backend/setup_wsl.sh, as run.py uses


def python_runs_here() -> bool:
    """Windows Smart App Control can block Python or its machine-learning libraries; check before starting."""
    try:
        return subprocess.run([str(PYTHON), "-c", "import pandas, sklearn.linear_model"], capture_output=True).returncode == 0
    except OSError:
        return False


def wsl_path(path: Path) -> str:
    """C:\\Users\\... as WSL sees it: /mnt/c/Users/..."""
    drive, rest = path.as_posix().split(":", 1)
    return f"/mnt/{drive.lower()}{rest}"


def start_backend(env: dict, data: Path) -> subprocess.Popen:
    uvicorn = ["-m", "uvicorn", "app.main:app", "--port", str(API_PORT), "--no-access-log"]
    if os.name != "nt" or python_runs_here():
        return subprocess.Popen([str(PYTHON), *uvicorn], cwd=BACKEND, env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # In WSL the throwaway folders are passed as WSL paths; 0.0.0.0 so Windows' localhost reaches it (WSL is NAT'd)
    settings = {"SKIP_ENV_FILE": "1", "SMTP_HOST": "", "DATABASE_URL": f"sqlite:///{wsl_path(data / 'app.db')}",
                "OUTBOX_DIR": wsl_path(data / "outbox"), "FEEDBACK_FILES_DIR": wsl_path(data / "correction_evidence"),
                "APP_URL": env["APP_URL"]}
    command = " ".join(f"{k}='{v}'" for k, v in settings.items()) + f" exec {WSL_PYTHON} {' '.join(uvicorn)} --host 0.0.0.0"
    return subprocess.Popen(["wsl.exe", "--cd", str(BACKEND), "--", "bash", "-c", command],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_for(url: str, seconds: int = 90) -> None:
    for _ in range(seconds * 2):
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except OSError:
            time.sleep(0.5)
    sys.exit(f"{url} did not start")


def main() -> int:
    data = Path(tempfile.mkdtemp(prefix="meritlens-browser-"))
    env = {**os.environ, "SKIP_ENV_FILE": "1", "SMTP_HOST": "",
           "DATABASE_URL": f"sqlite:///{(data / 'app.db').as_posix()}",
           "OUTBOX_DIR": str(data / "outbox"), "FEEDBACK_FILES_DIR": str(data / "correction_evidence"),
           "API_URL": f"http://127.0.0.1:{API_PORT}", "APP_URL": f"http://127.0.0.1:{WEB_PORT}"}
    built = subprocess.run([NPX, "vite", "build", "--outDir", str(data / "dist"), "--emptyOutDir"], cwd=FRONTEND,
                           env=env, capture_output=True, text=True)
    if built.returncode != 0:
        sys.exit("The frontend didn't build:\n" + built.stdout[-2000:] + built.stderr[-2000:])
    servers = [
        start_backend(env, data),
        # A production build, served as is: unlike the development server, it never reloads a page mid-check
        subprocess.Popen([NPX, "vite", "preview", "--outDir", str(data / "dist"), "--port", str(WEB_PORT), "--strictPort"],
                         cwd=FRONTEND, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
    ]
    # Another script can be run against the throwaway copy instead, e.g. scripts/capture_landing.js
    if sys.argv[1:] and sys.argv[1].endswith(".js"):
        script_and_args = ["node", str(ROOT / sys.argv[1]), *sys.argv[2:]]
    else:
        script_and_args = ["node", str(ROOT / "scripts" / "browser_checks.js"), *sys.argv[1:]]
    try:
        wait_for(f"http://127.0.0.1:{API_PORT}/api/health")
        wait_for(f"http://127.0.0.1:{WEB_PORT}/")
        try:
            return subprocess.run(script_and_args, env=env, timeout=900).returncode
        except subprocess.TimeoutExpired:
            print("The browser checks took longer than 15 minutes and were stopped.")
            return 1
    finally:
        for server in servers:
            if os.name == "nt":  # npx starts child processes; stop the whole tree
                subprocess.run(["taskkill", "/pid", str(server.pid), "/T", "/F"], capture_output=True)
            else:
                server.terminate()
        if os.name == "nt":  # stopping wsl.exe doesn't always stop a server started inside WSL
            subprocess.run(["wsl.exe", "--", "pkill", "-f", f"uvicorn app.main:app --port {API_PORT}"], capture_output=True)
        time.sleep(1)
        shutil.rmtree(data, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
