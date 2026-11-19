"""Entry point: `./homebound` starts the server and opens the browser."""

import threading
import webbrowser

import uvicorn

HOST = "127.0.0.1"
PORT = 8765


def main() -> None:
    url = f"http://{HOST}:{PORT}"
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"Homebound running at {url}  (Ctrl+C to quit)")
    uvicorn.run("homebound.app:app", host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
