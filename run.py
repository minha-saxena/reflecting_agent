import subprocess
import sys
import signal
import os

processes = []


def shutdown(sig=None, frame=None):
    print("\n Shutting down...")
    for p in processes:
        p.terminate()
    sys.exit(0)


signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)


def main():
    print(" Starting SQL Reflection Agent\n")
    print("   API  →  http://localhost:8000")
    print("   UI   →  http://localhost:8501")
    print("   Docs →  http://localhost:8000/docs")
    print("\n   Press Ctrl+C to stop both servers.\n")

    # Ensure both subprocesses can resolve `app.*` imports
    project_root = os.path.dirname(os.path.abspath(__file__))
    env = {**os.environ, "PYTHONPATH": project_root}

    api = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "app"],
        env=env,
    )
    processes.append(api)

    streamlit = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "streamlit_app/streamlit_app.py", "--server.port", "8501"],
        env=env,
    )
    processes.append(streamlit)

    # Wait — if either process dies unexpectedly, shut everything down
    while True:
        for p in processes:
            if p.poll() is not None:
                print(f"\n⚠️  A process exited unexpectedly (code {p.returncode}). Shutting down.")
                shutdown()
        try:
            processes[0].wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass


if __name__ == "__main__":
    main()