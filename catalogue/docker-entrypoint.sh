#!/bin/sh
set -eu

: "${PORT:=10000}"
: "${PYGEOAPI_SERVER_URL:=http://localhost:${PORT}}"
: "${WIGOS_CATALOGUE_DB:=/app/data/wigos-facilities.tinydb}"
: "${WMDR2_SYNC_ON_START:=1}"
export PORT PYGEOAPI_SERVER_URL WIGOS_CATALOGUE_DB

if [ "${WMDR2_SYNC_ON_START}" = "1" ]; then
  python /app/scripts/rebuild_catalogue.py
elif [ ! -f "${WIGOS_CATALOGUE_DB}" ]; then
  python /app/scripts/build_catalogue.py
fi

pygeoapi openapi generate "${PYGEOAPI_CONFIG}" --output-file "${PYGEOAPI_OPENAPI}"
exec gunicorn --workers 2 --bind "0.0.0.0:${PORT}" pygeoapi.flask_app:APP
