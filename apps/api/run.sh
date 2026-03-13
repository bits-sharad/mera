#!/usr/bin/env bash
# Run the API with correct PYTHONPATH to avoid "No module named 'apps'" or "No module named 'src'"
cd "$(dirname "$0")"
API_DIR="$PWD"
WORKSPACE_ROOT="$(cd .. && pwd)"
export PYTHONPATH="${API_DIR}:${WORKSPACE_ROOT}${PYTHONPATH:+:}${PYTHONPATH:-}"
python -m uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload
