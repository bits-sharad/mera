from __future__ import annotations
import os
import sys
import re
import warnings
from pathlib import Path
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Log the physical path to this main.py file
print(f"[INFO] Physical path to main.py: {os.path.abspath(__file__)}")

# Add the directory containing 'src' (apps/api) to Python path so that
# "from src.xxx" resolves to apps/api/src/xxx
_src_parent = Path(__file__).resolve().parents[1]  # apps/api
if str(_src_parent) not in sys.path:
    sys.path.insert(0, str(_src_parent))

# Suppress Pydantic V1 deprecation warnings from langchain-core
warnings.filterwarnings("ignore", message=".*Core Pydantic V1 functionality.*")


def load_environment():
    """Load the appropriate .env file based on APP_ENV variable.

    Priority:
    1. .env.{environment} file (e.g., .env.development, .env.stage, .env.production)
    2. .env file (default)

    Supported environments:
    - development (dev, dev)
    - stage (stage, staging)
    - production (prod, production)
    """

    # .env files are in the api directory (same as main.py)
    api_dir = Path(__file__).parent

    # First try to get APP_ENV from environment or system
    app_env = os.getenv("APP_ENV", "dev").lower().strip()

    # Map short names to full environment names
    env_mapping = {
        "local": "development",
        "dev": "development",
        "development": "development",
        "stage": "stage",
        "staging": "stage",
        "prod": "production",
        "production": "production",
    }

    full_env_name = env_mapping.get(app_env, "development")

    # Try to load environment-specific .env file
    env_file = api_dir / f".env.{full_env_name}"
    if env_file.exists():
        print(f"[INFO] Loading environment config from {env_file}")
        load_dotenv(env_file, override=True)
        print(f"[INFO] Successfully loaded {env_file}")
    else:
        # Fall back to default .env file
        default_env_file = api_dir / ".env"
        if default_env_file.exists():
            print(f"[WARNING] {env_file} not found. Falling back to {default_env_file}")
            print(f"[INFO] Loading default environment config from {default_env_file}")
            load_dotenv(default_env_file, override=True)
            print(f"[INFO] Successfully loaded {default_env_file}")
        else:
            print(
                f"[ERROR] No .env file found. Looked for: {env_file} or {default_env_file}"
            )


# Only load .env if APP_ENV is dev or development

os.environ.setdefault("APP_ENV", "local")
if os.getenv("APP_ENV", "local").lower().strip() in ["local"]:
    load_environment()

root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(root_path)


try:
    from src.core.config import settings
    from src.core.logging import setup_logging
    from src.routes.routes import router

    # Debug: Print loaded MongoDB configuration
    print(f"[DEBUG] MongoDB config loaded:")
    print(f"[DEBUG]   Username: {settings.mongodb_username}")
    print(
        f"[DEBUG]   Password: {'*' * len(settings.mongodb_password) if settings.mongodb_password else 'NOT SET'}"
    )
    print(f"[DEBUG]   Host: {settings.mongodb_host}")
    print(f"[DEBUG]   Database: {settings.mongodb_database}")
    print(
        f"[DEBUG]   URI (first 100 chars): {settings.mongodb_uri[:100] if settings.mongodb_uri else 'NOT SET'}"
    )
except ImportError as e:
    print(f"[ERROR] Failed to import app modules: {e}", file=sys.stderr)
    raise

# Set default log level if not provided
log_level = settings.log_level or "INFO"
setup_logging(log_level)

# Set default app name if not provided
app_name = settings.app_name or "Job Matching API"
app = FastAPI(title=app_name, version="0.1.0")

# CORS – adjust for your front-end origin(s)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


if __name__ == "__main__":
    # For development: use --reload flag manually: uvicorn main:app --reload
    # The reload watcher will watch for file changes in the api directory
    uvicorn_log_level = (settings.log_level or "INFO").lower()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=int(settings.port) if settings.port is not None else 8080,
        reload=False,  # Disable reload by default (use --reload flag instead)
        log_level=uvicorn_log_level,
    )
