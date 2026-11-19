#!/bin/sh
# Start/stop the Homebound server in the background. Used by Homebound.app.
# Usage: scripts/homebound-ctl.sh start|stop|status
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
URL="http://127.0.0.1:8765"
PIDFILE="$REPO/data/server.pid"
LOG="$REPO/data/server.log"
cd "$REPO" || exit 1
mkdir -p data

running() { curl -s -o /dev/null --max-time 1 "$URL/api/log"; }

case "${1:-}" in
  start)
    running && exit 0
    if [ ! -x .venv/bin/python ]; then
      echo "$(date) creating virtualenv" >> "$LOG"
      /usr/bin/python3 -m venv .venv >> "$LOG" 2>&1 && .venv/bin/pip install -q -r requirements.txt >> "$LOG" 2>&1 \
        || { echo "Couldn't install Python requirements. See $LOG"; exit 1; }
    fi
    echo "$(date) starting server" >> "$LOG"
    nohup .venv/bin/python -m homebound --no-browser >> "$LOG" 2>&1 < /dev/null &
    echo $! > "$PIDFILE"
    i=0
    while [ $i -lt 30 ]; do running && exit 0; sleep 0.5; i=$((i+1)); done
    echo "Server didn't start within 15 seconds. See $LOG"; exit 1
    ;;
  stop)
    if [ -f "$PIDFILE" ]; then
      PID="$(cat "$PIDFILE")"
      # Only kill it if that PID is really our server.
      ps -p "$PID" -o command= 2>/dev/null | grep -q "homebound" && kill "$PID"
      rm -f "$PIDFILE"
    fi
    echo "$(date) server stopped" >> "$LOG"
    ;;
  status)
    running && echo "running at $URL" || { echo "stopped"; exit 1; }
    ;;
  *) echo "usage: $0 start|stop|status"; exit 2 ;;
esac
