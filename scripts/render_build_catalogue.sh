#!/usr/bin/env bash
set -euo pipefail

echo "Installing catalogue dependencies..."
python -m pip install -r requirements.txt

echo "Synchronizing published WMDR2 examples and building WIGOS catalogue..."
python scripts/rebuild_catalogue.py

echo "Generating pygeoapi OpenAPI document..."
pygeoapi openapi generate \
  "${PYGEOAPI_CONFIG}" \
  --output-file "${PYGEOAPI_OPENAPI}"

echo "Render catalogue build complete."
