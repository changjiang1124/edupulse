#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="${VENV_PYTHON:-$PROJECT_DIR/.venv/bin/python}"
MANAGE_PY="${MANAGE_PY:-$PROJECT_DIR/manage.py}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-25001}"
DEFAULT_SITE_DOMAIN="${DEFAULT_SITE_DOMAIN:-127.0.0.1:${PORT}}"
MODE="${1:-server}"
OPEN_BROWSER="${OPEN_BROWSER:-1}"
BROWSER_DELAY="${BROWSER_DELAY:-2}"

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-edupulse.settings}"
export PYTHONUNBUFFERED=1
export SITE_PROTOCOL="${SITE_PROTOCOL:-http}"
export SITE_DOMAIN="${SITE_DOMAIN:-$DEFAULT_SITE_DOMAIN}"

usage() {
  cat <<'EOF'
Usage: ./dev.sh [server|worker|all|help]

Modes:
  server  Start the Django development server on 127.0.0.1:25001 (default)
  worker  Start the Django RQ worker for notifications/default queues
  all     Start both the dev server and the RQ worker
  help    Show this help message

Optional environment variables:
  HOST=127.0.0.1
  PORT=25001
  SITE_DOMAIN=127.0.0.1:25001
  OPEN_BROWSER=1
  BROWSER_DELAY=2
  VENV_PYTHON=/path/to/.venv/bin/python
  MANAGE_PY=/path/to/manage.py
EOF
}

ensure_requirements() {
  if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "[ERROR] Python virtual environment not found: $VENV_PYTHON" >&2
    exit 1
  fi

  if [[ ! -f "$MANAGE_PY" ]]; then
    echo "[ERROR] manage.py not found: $MANAGE_PY" >&2
    exit 1
  fi

  if [[ ! -f "$PROJECT_DIR/.env" ]]; then
    echo "[WARN] .env not found at $PROJECT_DIR/.env"
  fi
}

check_port() {
  if command -v lsof >/dev/null 2>&1 && lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "[WARN] Port $PORT is already in use by the following process(es):" >&2
    lsof -iTCP:"$PORT" -sTCP:LISTEN >&2 || true
    
    printf "\nDo you want to kill these processes and continue? [y/N]: " >&2
    read -r response < /dev/tty
    
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
      local pids
      pids=$(lsof -t -iTCP:"$PORT" -sTCP:LISTEN)
      if [[ -n "$pids" ]]; then
        echo "[INFO] Killing processes: $pids" >&2
        kill -9 $pids 2>/dev/null || true
        sleep 1
      fi
    else
      echo "[ERROR] Stop the existing process or run with a different PORT." >&2
      exit 1
    fi
  fi
}

run_checks() {
  echo "[INFO] Checking for missing migrations..."
  "$VENV_PYTHON" "$MANAGE_PY" makemigrations --check --dry-run

  echo "[INFO] Applying database migrations..."
  "$VENV_PYTHON" "$MANAGE_PY" migrate --noinput

  echo "[INFO] Running Django system checks..."
  "$VENV_PYTHON" "$MANAGE_PY" check
}

open_browser() {
  local url="http://${HOST}:${PORT}"

  if [[ "$OPEN_BROWSER" != "1" ]]; then
    return
  fi

  (
    sleep "$BROWSER_DELAY"

    if command -v open >/dev/null 2>&1; then
      open "$url" >/dev/null 2>&1 || true
    elif command -v xdg-open >/dev/null 2>&1; then
      xdg-open "$url" >/dev/null 2>&1 || true
    fi
  ) &
}

run_server() {
  echo "[INFO] Starting Django development server"
  echo "[INFO] URL: http://${HOST}:${PORT}"
  echo "[INFO] SITE_DOMAIN=${SITE_DOMAIN}"
  open_browser
  exec "$VENV_PYTHON" "$MANAGE_PY" runserver "${HOST}:${PORT}"
}

run_worker() {
  echo "[INFO] Starting Django RQ worker"
  exec "$VENV_PYTHON" "$MANAGE_PY" rqworker notifications default
}

run_all() {
  local server_pid=""
  local worker_pid=""

  cleanup() {
    local exit_code=$?

    if [[ -n "$server_pid" ]] && kill -0 "$server_pid" 2>/dev/null; then
      kill "$server_pid" 2>/dev/null || true
    fi

    if [[ -n "$worker_pid" ]] && kill -0 "$worker_pid" 2>/dev/null; then
      kill "$worker_pid" 2>/dev/null || true
    fi

    wait "$server_pid" 2>/dev/null || true
    wait "$worker_pid" 2>/dev/null || true

    exit "$exit_code"
  }

  trap cleanup INT TERM EXIT

  echo "[INFO] Starting full development environment"
  echo "[INFO] Django URL: http://${HOST}:${PORT}"
  echo "[INFO] SITE_DOMAIN=${SITE_DOMAIN}"

  open_browser
  "$VENV_PYTHON" "$MANAGE_PY" runserver "${HOST}:${PORT}" &
  server_pid=$!

  "$VENV_PYTHON" "$MANAGE_PY" rqworker notifications default &
  worker_pid=$!

  wait -n "$server_pid" "$worker_pid"
}

ensure_requirements

case "$MODE" in
  server)
    check_port
    run_checks
    run_server
    ;;
  worker)
    run_checks
    run_worker
    ;;
  all)
    check_port
    run_checks
    run_all
    ;;
  help|--help|-h)
    usage
    ;;
  *)
    echo "[ERROR] Unknown mode: $MODE" >&2
    usage >&2
    exit 1
    ;;
esac
