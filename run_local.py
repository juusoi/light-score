import os
import signal
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_BIN = ROOT / ".venv" / "bin"
UVICORN = str(VENV_BIN / "uvicorn")
PYTHON = str(VENV_BIN / "python")


def start_server(args: list[str], cwd: Path) -> subprocess.Popen:
    # Start each server in its own process group for clean shutdowns
    return subprocess.Popen(
        args,
        cwd=str(cwd),
        preexec_fn=os.setsid,  # new process group (POSIX)
    )


def stop_server(proc: subprocess.Popen, name: str):
    if proc and proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass


def handle_exit(_sig, _frame):
    print("\nStopping servers...")
    stop_server(backend_server, "backend")
    stop_server(frontend_server, "frontend")
    sys.exit(0)


signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)


backend_cwd = ROOT / "backend" / "src"
frontend_cwd = ROOT / "frontend" / "src"
functions_cwd = ROOT / "functions" / "src"


def generate_standings_cache_once() -> None:
    """Run the functions main once to produce the backend standings cache."""
    print("Generating standings cache via functions...")
    try:
        subprocess.run([PYTHON, "main.py"], cwd=str(functions_cwd), check=False)
    except FileNotFoundError:
        print(
            "Warning: Could not run functions to generate cache (missing venv/binaries)."
        )


# Generate cache before starting servers (best-effort)
generate_standings_cache_once()

# Backend: uvicorn main:app --port 8000 --reload
backend_server = start_server(
    [UVICORN, "main:app", "--port", "8000", "--reload"], backend_cwd
)

# Frontend: python app.py
frontend_server = start_server([PYTHON, "app.py"], frontend_cwd)


def wait_and_watch():
    # If either server exits, stop the other and exit
    procs = {"backend": backend_server, "frontend": frontend_server}
    try:
        while True:
            for name, proc in list(procs.items()):
                ret = proc.poll()
                if ret is not None:
                    print(
                        f"{name} server exited with code {ret}. Shutting down the other..."
                    )
                    # Stop the other server
                    for other_name, other_proc in procs.items():
                        if other_name != name:
                            stop_server(other_proc, other_name)
                    sys.exit(ret if isinstance(ret, int) else 1)
            signal.pause()
    except KeyboardInterrupt:
        handle_exit(None, None)


wait_and_watch()
