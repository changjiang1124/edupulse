#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# EduPulse deployment script (Ubuntu 22.04)
# - Applies Django database migrations
# - Collects static files to STATIC_ROOT
# - Restarts Gunicorn service
#
# USAGE (example):
#   sudo bash deploy/deploy.sh \
#     PROJECT_DIR=/var/www/edupulse \
#     VENV_DIR=/var/www/edupulse/.venv
# -----------------------------------------------------------------------------
set -euo pipefail

# Configuration via environment variables with sensible defaults
# Default paths are set to match deploy/*.service templates
PROJECT_DIR=${PROJECT_DIR:-/var/www/edupulse}
VENV_DIR=${VENV_DIR:-$PROJECT_DIR/.venv}
MANAGE_PY=${DJANGO_MANAGE:-$PROJECT_DIR/manage.py}
SERVICE_NAME=${SERVICE_NAME:-edupulse}
RQ_SERVICE_NAME=${RQ_SERVICE_NAME:-edupulse-rqworker}
REDIS_SERVICE_NAME=${REDIS_SERVICE_NAME:-redis}
REDIS_CLI=${REDIS_CLI:-redis-cli}
ENV_FILE=${ENV_FILE:-$PROJECT_DIR/.env}
SYSTEMD_DIR=${SYSTEMD_DIR:-/etc/systemd/system}

export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-edupulse.settings}
export PYTHONUNBUFFERED=1

# Helpers
maybe_restart_service() {
  local svc="$1"
  if command -v systemctl >/dev/null 2>&1; then
    echo "[INFO] Restarting systemd service: ${svc}.service"
    systemctl daemon-reload || true
    systemctl restart "${svc}.service"
    systemctl status "${svc}.service" --no-pager -n 0 || true
  else
    echo "[WARN] systemctl not found; please restart ${svc} manually."
  fi
}

check_redis() {
  if ! command -v "$REDIS_CLI" >/dev/null 2>&1; then
    echo "[WARN] redis-cli not found; skipping Redis connectivity check."
    return
  fi
  if "$REDIS_CLI" ping >/dev/null 2>&1; then
    echo "[INFO] Redis ping ok."
  else
    echo "[WARN] Redis ping failed, attempting to restart ${REDIS_SERVICE_NAME}.service ..."
    maybe_restart_service "$REDIS_SERVICE_NAME"
    if "$REDIS_CLI" ping >/dev/null 2>&1; then
      echo "[INFO] Redis recovered after restart."
    else
      echo "[ERROR] Redis still unreachable; queued tasks may not run." >&2
    fi
  fi
}

sync_service_unit() {
  local unit_name="$1"
  local source_path="$2"
  local target_path="$SYSTEMD_DIR/$unit_name"

  if [ ! -f "$source_path" ]; then
    echo "[WARN] Service template not found: $source_path (skipping)"
    return
  fi

  if [ ! -f "$target_path" ]; then
    echo "[INFO] Installing systemd unit: $unit_name"
    cp "$source_path" "$target_path"
    systemctl daemon-reload || true
    systemctl enable "$unit_name" || true
  else
    if cmp -s "$source_path" "$target_path"; then
      echo "[INFO] Systemd unit up-to-date: $unit_name"
    else
      echo "[INFO] Updating systemd unit: $unit_name (detected changes)"
      cp "$source_path" "$target_path"
      systemctl daemon-reload || true
      # Keep enabled state as-is
    fi
  fi
}

# Change to project directory
cd "$PROJECT_DIR"

# Load environment variables if available
if [ -f "$ENV_FILE" ]; then
  echo "[INFO] Loading environment from $ENV_FILE"
  # shellcheck disable=SC1090
  set -a && source "$ENV_FILE" && set +a
else
  echo "[WARN] .env not found at $ENV_FILE; ensure required variables are set."
fi

# Activate virtual environment
if [ -f "$VENV_DIR/bin/activate" ]; then
  # shellcheck disable=SC1090
  source "$VENV_DIR/bin/activate"
else
  echo "[ERROR] Virtualenv not found at: $VENV_DIR" >&2
  exit 1
fi

# Ensure manage.py exists
if [ ! -f "$MANAGE_PY" ]; then
  echo "[ERROR] manage.py not found at: $MANAGE_PY" >&2
  exit 1
fi

# Ensure systemd units are installed/updated (idempotent)
sync_service_unit "${SERVICE_NAME}.service" "$PROJECT_DIR/deploy/edupulse.service"
sync_service_unit "${RQ_SERVICE_NAME}.service" "$PROJECT_DIR/deploy/edupulse-rqworker.service"

# Basic health checks
check_redis

# Apply migrations
echo "[INFO] Running database migrations..."
python "$MANAGE_PY" migrate --noinput

# Collect statics
echo "[INFO] Collecting static files..."
python "$MANAGE_PY" collectstatic --noinput

# Optionally run checks
echo "[INFO] Running Django system checks..."
python "$MANAGE_PY" check --deploy || true

# Restart Gunicorn service if systemd is available
maybe_restart_service "$SERVICE_NAME"

# Restart RQ worker service (notifications queue)
maybe_restart_service "$RQ_SERVICE_NAME"

echo "[SUCCESS] Deployment completed."
