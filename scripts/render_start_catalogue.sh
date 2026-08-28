#!/usr/bin/env bash
set -euo pipefail

: "${PORT:=10000}"

echo "Starting WIGOS Portal PoC catalogue on port ${PORT}"
exec gunicorn   --bind "0.0.0.0:${PORT}"   --workers 1   --threads 4   --timeout 120   --access-logfile -   --error-logfile -   pygeoapi.flask_app:APP
