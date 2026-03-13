#!/usr/bin/env python3
"""Run script that sets PYTHONPATH before starting uvicorn.

Use this when you get "ModuleNotFoundError: No module named 'apps'" or "No module named 'src'".

Usage (from workspace root or apps/api):
    python apps/api/run.py
    # or from apps/api:
    python run.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure apps/api is in PYTHONPATH before any imports
_api_dir = Path(__file__).resolve().parent
_workspace_root = _api_dir.parent

# Set PYTHONPATH so uvicorn's reload subprocess inherits it (critical for --reload)
existing = os.environ.get("PYTHONPATH", "")
paths = [str(_api_dir), str(_workspace_root)]
for p in paths:
    if p not in sys.path:
        sys.path.insert(0, p)
os.environ["PYTHONPATH"] = os.pathsep.join(paths) + (os.pathsep + existing if existing else "")

# Now run uvicorn
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
    )
