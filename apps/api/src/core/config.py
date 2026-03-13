from __future__ import annotations

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


def _get_env_file() -> str:
    """Determine which .env file to use based on APP_ENV"""
    api_dir = Path(__file__).parent.parent.parent  # Go up from app/core to api/

    app_env = os.getenv("APP_ENV", "dev").lower().strip()

    env_mapping = {
        "dev": "development",
        "development": "development",
        "stage": "stage",
        "staging": "stage",
        "prod": "production",
        "production": "production",
    }

    full_env_name = env_mapping.get(app_env, "development")
    env_file = api_dir / f".env.{full_env_name}"

    # Fall back to .env if environment-specific file doesn't exist
    if not env_file.exists():
        env_file = api_dir / ".env"

    return str(env_file)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_get_env_file(), extra="ignore")

    app_env: str = Field(default="dev", alias="APP_ENV")
    app_name: str = Field(default="job-arch-multi-agent", alias="APP_NAME")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8080, alias="PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    auth_mode: str = Field(default="none", alias="AUTH_MODE")  # none|jwt
    jwt_public_key_pem: str = Field(default="", alias="JWT_PUBLIC_KEY_PEM")
    jwt_audience: str = Field(default="", alias="JWT_AUDIENCE")
    jwt_issuer: str = Field(default="", alias="JWT_ISSUER")

    core_api_base_url: str = Field(..., alias="CORE_API_BASE_URL")
    core_api_key: str = Field(..., alias="CORE_API_KEY")

    embeddings_base_url: str = Field(
        default="https://stg1.mmc-bedford-int-non-prod-ingress.mgti.mmc.com/coreapi/llm/embeddings/v1",
        alias="EMBEDDINGS_BASE_URL",
    )
    embeddings_model: str = Field(
        default="mmc-tech-text-embedding-3-large", alias="EMBEDDINGS_MODEL"
    )

    doc_processing_api_base_url: str = Field(..., alias="DOC_PROCESSING_API_BASE_URL")
    doc_processing_api_key: str = Field(..., alias="DOC_PROCESSING_API_KEY")

    fetch_token_username: str = Field(..., alias="FETCH_TOKEN_USERNAME")
    fetch_token_password: str = Field(..., alias="FETCH_TOKEN_PASSWORD")

    # MongoDB configuration - use component fields to build URI
    mongodb_username: str = Field(default="", alias="MONGODB_USERNAME")
    mongodb_password: str = Field(default="", alias="MONGODB_PASSWORD")
    mongodb_host: str = Field(default="", alias="MONGODB_HOST")
    mongodb_database: str = Field(
        default="jobmatchingmodelpocDev", alias="MONGODB_DATABASE"
    )
    mongodb_uri: str = Field(default="", alias="MONGODB_URI")

    # MongoDB Collection Names
    spec_collection: str = Field(default="job_specialties", alias="SPEC_COLLECTION")
    alias_collection: str = Field(default="job_aliases", alias="ALIAS_COLLECTION")
    job_families_collection: str = Field(
        default="job_families", alias="JOB_FAMILIES_COLLECTION"
    )

    # Search Index Names
    spec_vector_index: str = Field(
        default="spec_vector_index", alias="SPEC_VECTOR_INDEX"
    )
    spec_fulltext_index: str = Field(
        default="spec_fulltext_index", alias="SPEC_FULLTEXT_INDEX"
    )
    alias_vector_index: str = Field(
        default="alias_vector_index", alias="ALIAS_VECTOR_INDEX"
    )
    alias_fulltext_index: str = Field(
        default="alias_fulltext_index", alias="ALIAS_FULLTEXT_INDEX"
    )

    # Embedding Configuration
    embedding_model: str = Field(
        default="BAAI/bge-large-en-v1.5", alias="EMBEDDING_MODEL"
    )
    embedding_dimension: int = Field(default=3072, alias="EMBEDDING_DIMENSION")

    # Search Configuration
    top_k_per_search: int = Field(default=20, alias="TOP_K_PER_SEARCH")
    total_candidates_spec: int = Field(default=3000, alias="TOTAL_CANDIDATES_SPEC")
    total_candidates_alias: int = Field(default=10000, alias="TOTAL_CANDIDATES_ALIAS")
    final_results_limit: int = Field(default=10, alias="FINAL_RESULTS_LIMIT")

    # Hybrid Search Weights
    vector_weight: float = Field(default=0.5, alias="VECTOR_WEIGHT")
    fulltext_weight: float = Field(default=0.5, alias="FULLTEXT_WEIGHT")

    http_timeout_s: int = Field(default=30, alias="HTTP_TIMEOUT_S")
    http_max_retries: int = Field(default=3, alias="HTTP_MAX_RETRIES")

    enable_request_logging: bool = Field(default=True, alias="ENABLE_REQUEST_LOGGING")
    enable_audit_trail: bool = Field(default=True, alias="ENABLE_AUDIT_TRAIL")

    @field_validator("mongodb_uri", mode="after")
    @classmethod
    def build_mongodb_uri(cls, v, info):
        """Build MongoDB URI from components if not explicitly provided"""
        # If URI is already provided and valid, use it as-is
        if v and v.startswith("mongodb"):
            return v

        # Otherwise, build from component fields
        username = info.data.get("mongodb_username", "").strip()
        password = info.data.get("mongodb_password", "").strip()
        host = info.data.get("mongodb_host", "").strip()

        if username and password and host:
            uri = f"mongodb+srv://{username}:{password}@{host}/?retryWrites=true&w=majority"
            print(
                f"[CONFIG] Built MongoDB URI from components: mongodb+srv://***:***@{host}/?retryWrites=true&w=majority"
            )
            return uri
        else:
            # Fallback if components missing
            uri = f"mongodb://{host}/"
            print(f"[CONFIG] Using MongoDB URI without authentication: {uri}")
            return uri


# Use config_service for all values if env != 'dev', else use Settings
from src.utils.config_service import config_service

APP_ENV = os.getenv("APP_ENV", "local").lower().strip()

if APP_ENV == "local":
    settings = Settings()
else:

    class SettingsFromConfigService:
        def __init__(self):
            # List all config keys as attributes, fallback to None if not found
            self.app_env = config_service.get("APP_ENV", mandatory=False)
            self.app_name = config_service.get("APP_NAME", mandatory=False)
            self.host = config_service.get("HOST", mandatory=False)
            self.port = config_service.get("PORT", mandatory=False)
            self.log_level = config_service.get("LOG_LEVEL", mandatory=False)
            self.auth_mode = config_service.get("AUTH_MODE", mandatory=False)
            self.jwt_public_key_pem = config_service.get(
                "JWT_PUBLIC_KEY_PEM", mandatory=False
            )
            self.jwt_audience = config_service.get("JWT_AUDIENCE", mandatory=False)
            self.jwt_issuer = config_service.get("JWT_ISSUER", mandatory=False)
            self.core_api_base_url = config_service.get(
                "CORE_API_BASE_URL", mandatory=False
            )
            self.core_api_key = config_service.get("CORE_API_KEY", mandatory=False)
            self.embeddings_base_url = config_service.get(
                "EMBEDDINGS_BASE_URL", mandatory=False
            )
            self.embeddings_model = config_service.get(
                "EMBEDDINGS_MODEL", mandatory=False
            )
            self.doc_processing_api_base_url = config_service.get(
                "DOC_PROCESSING_API_BASE_URL", mandatory=False
            )
            self.doc_processing_api_key = config_service.get(
                "DOC_PROCESSING_API_KEY", mandatory=False
            )
            self.fetch_token_username = config_service.get(
                "FETCH_TOKEN_USERNAME", mandatory=False
            )
            self.fetch_token_password = config_service.get(
                "FETCH_TOKEN_PASSWORD", mandatory=False
            )
            self.mongodb_username = config_service.get(
                "MONGODB_USERNAME", mandatory=False
            )
            self.mongodb_password = config_service.get(
                "MONGODB_PASSWORD", mandatory=False
            )
            self.mongodb_host = config_service.get("MONGODB_HOST", mandatory=False)
            self.mongodb_database = config_service.get(
                "MONGODB_DATABASE", mandatory=False
            )
            self.mongodb_uri = config_service.get("MONGODB_URI", mandatory=False)
            self.spec_collection = config_service.get(
                "SPEC_COLLECTION", mandatory=False
            )
            self.alias_collection = config_service.get(
                "ALIAS_COLLECTION", mandatory=False
            )
            self.job_families_collection = config_service.get(
                "JOB_FAMILIES_COLLECTION", mandatory=False
            )
            self.spec_vector_index = config_service.get(
                "SPEC_VECTOR_INDEX", mandatory=False
            )
            self.spec_fulltext_index = config_service.get(
                "SPEC_FULLTEXT_INDEX", mandatory=False
            )
            self.alias_vector_index = config_service.get(
                "ALIAS_VECTOR_INDEX", mandatory=False
            )
            self.alias_fulltext_index = config_service.get(
                "ALIAS_FULLTEXT_INDEX", mandatory=False
            )
            self.embedding_model = config_service.get(
                "EMBEDDING_MODEL", mandatory=False
            )
            self.embedding_dimension = config_service.get(
                "EMBEDDING_DIMENSION", mandatory=False
            )
            self.top_k_per_search = int(
                config_service.get("TOP_K_PER_SEARCH", mandatory=False)
            )
            self.total_candidates_spec = int(
                config_service.get("TOTAL_CANDIDATES_SPEC", mandatory=False)
            )
            self.total_candidates_alias = int(
                config_service.get("TOTAL_CANDIDATES_ALIAS", mandatory=False)
            )
            self.final_results_limit = int(
                config_service.get("FINAL_RESULTS_LIMIT", mandatory=False)
            )
            self.vector_weight = float(
                config_service.get("VECTOR_WEIGHT", mandatory=False)
            )
            self.fulltext_weight = float(
                config_service.get("FULLTEXT_WEIGHT", mandatory=False)
            )
            self.http_timeout_s = config_service.get("HTTP_TIMEOUT_S", mandatory=False)
            self.http_max_retries = config_service.get(
                "HTTP_MAX_RETRIES", mandatory=False
            )
            self.enable_request_logging = config_service.get(
                "ENABLE_REQUEST_LOGGING", mandatory=False
            )
            self.enable_audit_trail = config_service.get(
                "ENABLE_AUDIT_TRAIL", mandatory=False
            )

    settings = SettingsFromConfigService()
