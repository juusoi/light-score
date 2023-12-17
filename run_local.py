import signal
import subprocess
import sys


def start_server(command, cwd):
    return subprocess.Popen(command, cwd=cwd, shell=True)


def signal_handler(sig, frame):
    print("Stopping servers...")
    backend_server.terminate()
    frontend_server.terminate()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

backend_server = start_server("uvicorn main:app --port 8000", "./backend/src")
frontend_server = start_server("FLASK_APP=app.py flask run", "./frontend/src")

signal.pause()
