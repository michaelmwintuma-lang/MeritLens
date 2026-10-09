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
PYTHON = BACKEND / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
NPX = "npx.cmd" if os.name == "nt" else "npx"
API_PORT, WEB_PORT = 8001, 5174


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
           "OUTBOX_DIR": str(data / "outbox"), "EVIDENCE_DIR": str(data / "evidence"),
           "FEEDBACK_FILES_DIR": str(data / "correction_evidence"),
           "API_URL": f"http://127.0.0.1:{API_PORT}", "APP_URL": f"http://127.0.0.1:{WEB_PORT}"}
    built = subprocess.run([NPX, "vite", "build", "--outDir", str(data / "dist"), "--emptyOutDir"], cwd=FRONTEND,
                           env=env, capture_output=True, text=True)
    if built.returncode != 0:
        sys.exit("The frontend didn't build:\n" + built.stdout[-2000:] + built.stderr[-2000:])
    servers = [
        subprocess.Popen([str(PYTHON), "-m", "uvicorn", "app.main:app", "--port", str(API_PORT), "--no-access-log"],
                         cwd=BACKEND, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
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
        time.sleep(1)
        shutil.rmtree(data, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
