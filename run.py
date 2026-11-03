"""Entry point for OSINT Verification Workbench.

Starts the local server and opens the dashboard in the default browser.
When packaged with PyInstaller this is the file that gets frozen; data
is stored next to the executable so everything stays on the USB stick.

Usage (development):   python run.py [--port 8000]
"""

from __future__ import annotations

import argparse
import socket
import threading
import time
import webbrowser


def wait_then_open(port: int):
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.2)
    webbrowser.open(f"http://127.0.0.1:{port}")


def main():
    parser = argparse.ArgumentParser(description="OSINT Verification Workbench")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true",
                        help="don't auto-open the browser")
    args = parser.parse_args()

    import uvicorn  # deferred so --help works without uvicorn import cost
    from app.main import app as asgi_app  # direct import: works when frozen

    if not args.no_browser:
        threading.Thread(target=wait_then_open, args=(args.port,),
                         daemon=True).start()

    print(f"OSINT Verification Workbench → http://127.0.0.1:{args.port}")
    print("Press Ctrl+C to stop. All data stays in ./data next to this app.")
    uvicorn.run(asgi_app, host="127.0.0.1", port=args.port,
                log_level="warning")


if __name__ == "__main__":
    main()
