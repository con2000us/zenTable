#!/usr/bin/env bash
set -euo pipefail

# Simple background controller for the integrated ZenTable FastAPI service.
# - Starts detached (no blocking), writes a pidfile, logs to a file.
# - Does NOT register systemd autostart.

ZEN_ROOT="/var/www/html/zenTable"
VENV_PY="$ZEN_ROOT/venv/bin/python3"
PIDFILE_DEFAULT="$HOME/.openclaw/zentable_api.pid"
LOGFILE_DEFAULT="$HOME/.openclaw/zentable_api.log"
HOST_DEFAULT="127.0.0.1"
PORT_DEFAULT="8001"

cmd="${1:-}"
shift || true

usage() {
  cat <<EOF
Usage: $(basename "$0") <start|stop|restart|status|health> [options]

Options:
  --host <host>        (default: $HOST_DEFAULT)
  --port <port>        (default: $PORT_DEFAULT)
  --pidfile <path>     (default: $PIDFILE_DEFAULT)
  --logfile <path>     (default: $LOGFILE_DEFAULT)

Examples:
  $(basename "$0") start --port 8001
  $(basename "$0") status
  $(basename "$0") stop
EOF
}

HOST="$HOST_DEFAULT"
PORT="$PORT_DEFAULT"
PIDFILE="$PIDFILE_DEFAULT"
LOGFILE="$LOGFILE_DEFAULT"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="$2"; shift 2;;
    --port) PORT="$2"; shift 2;;
    --pidfile) PIDFILE="$2"; shift 2;;
    --logfile) LOGFILE="$2"; shift 2;;
    *) echo "Unknown arg: $1"; usage; exit 2;;
  esac
done

mkdir -p "$(dirname "$PIDFILE")" "$(dirname "$LOGFILE")" || true

is_running_pid() {
  local pid="$1"
  [[ -n "$pid" ]] || return 1
  kill -0 "$pid" 2>/dev/null
}

find_listen_pid() {
  # best-effort: find PID listening on HOST:PORT (Linux)
  ss -ltnp 2>/dev/null | awk -v p=":$PORT" '$4 ~ p {print $NF}' | head -n1 | sed -E 's/.*pid=([0-9]+).*/\1/' || true
}

case "$cmd" in
  start)
    if [[ ! -x "$VENV_PY" ]]; then
      echo "ERROR: venv python not found: $VENV_PY" >&2
      exit 1
    fi

    if [[ -f "$PIDFILE" ]]; then
      oldpid="$(cat "$PIDFILE" 2>/dev/null || true)"
      if is_running_pid "$oldpid"; then
        echo "Already running (pid=$oldpid)";
        exit 0
      fi
    fi

    # Detached start (no blocking): setsid + nohup
    # NOTE: This keeps the process alive after the caller exits.
    (
      cd "$ZEN_ROOT"
      export ZENTABLE_HOST="$HOST"
      export ZENTABLE_PORT="$PORT"
      export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
      exec "$VENV_PY" -m api.zentable_service
    ) >>"$LOGFILE" 2>&1 &

    pid=$!
    echo "$pid" > "$PIDFILE"
    echo "Started (pid=$pid) log=$LOGFILE"
    ;;

  stop)
    pid="$(cat "$PIDFILE" 2>/dev/null || true)"
    if is_running_pid "$pid"; then
      kill "$pid" || true
      sleep 0.5
      if is_running_pid "$pid"; then
        kill -9 "$pid" || true
      fi
      echo "Stopped (pid=$pid)"
    else
      # try find by port
      pid2="$(find_listen_pid)"
      if is_running_pid "$pid2"; then
        kill "$pid2" || true
        echo "Stopped by port (pid=$pid2)"
      else
        echo "Not running"
      fi
    fi
    rm -f "$PIDFILE" 2>/dev/null || true
    ;;

  restart)
    "$0" stop --host "$HOST" --port "$PORT" --pidfile "$PIDFILE" --logfile "$LOGFILE" || true
    "$0" start --host "$HOST" --port "$PORT" --pidfile "$PIDFILE" --logfile "$LOGFILE"
    ;;

  status)
    pid="$(cat "$PIDFILE" 2>/dev/null || true)"
    if is_running_pid "$pid"; then
      echo "running pid=$pid (pidfile=$PIDFILE)"
      exit 0
    fi
    pid2="$(find_listen_pid)"
    if is_running_pid "$pid2"; then
      echo "running pid=$pid2 (found by port :$PORT; pidfile missing/stale)"
      exit 0
    fi
    echo "stopped"
    exit 1
    ;;

  health)
    url="http://$HOST:$PORT/health"
    python3 - <<PY
import urllib.request
print(urllib.request.urlopen("$url", timeout=3).read().decode())
PY
    ;;

  -h|--help|help|"")
    usage
    ;;

  *)
    echo "Unknown command: $cmd" >&2
    usage
    exit 2
    ;;
esac
