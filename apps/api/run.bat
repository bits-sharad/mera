@echo off
REM Run the API with correct PYTHONPATH to avoid "No module named 'apps'" or "No module named 'src'"
cd /d "%~dp0"
set API_DIR=%CD%
cd ..
set WORKSPACE_ROOT=%CD%
cd /d "%API_DIR%"
set PYTHONPATH=%API_DIR%;%WORKSPACE_ROOT%
python -m uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload
