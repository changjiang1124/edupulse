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
PROJECT_DIR=${PROJECT_DIR:-/var/www/edupulse}
VENV_DIR=${VENV_DIR:-$PROJECT_DIR/.venv}
MANAGE_PY=${DJANGO_MANAGE:-$PROJECT_DIR/manage.py}
SERVICE_NAME=${SERVICE_NAME:-edupulse}

export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-edupulse.settings}
export PYTHONUNBUFFERED=1

# Change to project directory
cd "$PROJECT_DIR"

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
if command -v systemctl >/dev/null 2>&1; then
  echo "[INFO] Restarting systemd service: ${SERVICE_NAME}.service"
  systemctl daemon-reload || true
  systemctl restart "${SERVICE_NAME}.service"
  systemctl status "${SERVICE_NAME}.service" --no-pager -n 0 || true
else
  echo "[WARN] systemctl not found; please restart Gunicorn manually."
fi

echo "[SUCCESS] Deployment completed."