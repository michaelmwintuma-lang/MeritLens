"""
Start everything with one command:   python run.py

Runs the FastAPI backend (http://127.0.0.1:8000) and the React frontend (http://127.0.0.1:5173) together.
Open the frontend address in your browser. Press Ctrl+C to stop both.
After changing backend code, stop and start again (automatic reloading was unreliable on Windows).

If Windows Smart App Control blocks the machine-learning libraries, the backend runs inside WSL (Ubuntu)
instead, using the environment made by backend/setup_wsl.sh. See README: Installation.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

# The backend's own virtual environment (see README: Installation)
VENV_PYTHON = BACKEND / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
NPM = "npm.cmd" if os.name == "nt" else "npm"
WSL_PYTHON = "$HOME/venvs/hr-simple/bin/python"  # made by backend/setup_wsl.sh

# --no-access-log: the server keeps no record of requests (addresses, times, paths), so nothing shows
# when a report was sent. See docs/HOW_IT_WORKS.md, step 6.
UVICORN = "-m uvicorn app.main:app --port 8000 --no-access-log"


def windows_can_load_libraries() -> bool:
    """Smart App Control can block the compiled parts of pandas and scikit-learn; check before starting."""
    check = subprocess.run([str(VENV_PYTHON), "-c", "import pandas, sklearn.linear_model"], capture_output=True)
    return check.returncode == 0


def wsl_ready() -> bool:
    check = subprocess.run(["wsl.exe", "--", "bash", "-c", f"test -x {WSL_PYTHON}"], capture_output=True)
    return check.returncode == 0


def start_backend():
    if os.name != "nt" or windows_can_load_libraries():
        if not VENV_PYTHON.exists():
            sys.exit("The backend isn't installed yet. Follow 'Installation' in README.md first.")
        return subprocess.Popen([str(VENV_PYTHON), *UVICORN.split()], cwd=BACKEND), False
    if not wsl_ready():
        sys.exit("Windows Smart App Control is blocking the machine-learning libraries.\n"
                 "Set up the backend in WSL once with:   wsl bash backend/setup_wsl.sh   then run this again.")
    print("  Windows blocked the machine-learning libraries, so the backend runs in WSL (Ubuntu).")
    # 0.0.0.0 inside WSL: Windows forwards localhost to it more reliably. WSL sits behind the PC (NAT),
    # so this doesn't open the backend to the network.
    command = f"exec {WSL_PYTHON} {UVICORN} --host 0.0.0.0"
    return subprocess.Popen(["wsl.exe", "--cd", str(BACKEND), "--", "bash", "-c", command]), True


def main():
    if not (FRONTEND / "node_modules").exists():
        sys.exit("The frontend isn't installed yet. Run 'npm install' in the frontend folder first.")

    backend, in_wsl = start_backend()
    frontend = subprocess.Popen([NPM, "run", "dev"], cwd=FRONTEND)
    print("\n  Open http://127.0.0.1:5173 in your browser. Press Ctrl+C to stop.\n")
    try:
        backend.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for process in (frontend, backend):
            process.terminate()
        if in_wsl:  # stopping wsl.exe doesn't always stop the server inside it
            subprocess.run(["wsl.exe", "--", "pkill", "-f", "uvicorn app.main:app"], capture_output=True)


if __name__ == "__main__":
    main()
