from typing import Optional
from pydantic_settings import BaseSettings
import os


class ConfigService(BaseSettings):
    # Add all expected environment variables as Optional[str]
    app_env: Optional[str] = None
    app_name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[str] = None
    log_level: Optional[str] = None
    auth_mode: Optional[str] = None
    jwt_public_key_pem: Optional[str] = None
    jwt_audience: Optional[str] = None
    jwt_issuer: Optional[str] = None
    core_api_base_url: Optional[str] = None
    core_api_key: Optional[str] = None
    embeddings_base_url: Optional[str] = None
    embeddings_model: Optional[str] = None
    doc_processing_api_base_url: Optional[str] = None
    doc_processing_api_key: Optional[str] = None
    fetch_token_username: Optional[str] = None
    fetch_token_password: Optional[str] = None
    mongodb_uri: Optional[str] = None
    mongodb_database: Optional[str] = None
    mongodb_vector_index: Optional[str] = None
    mongodb_job_catalog_index: Optional[str] = None
    job_families_collection: Optional[str] = None
    http_timeout_s: Optional[str] = None
    http_max_retries: Optional[str] = None
    enable_request_logging: Optional[str] = None
    enable_audit_trail: Optional[str] = None
    database_name: Optional[str] = None
    spec_collection: Optional[str] = None
    alias_collection: Optional[str] = None
    spec_vector_index: Optional[str] = None
    spec_fulltext_index: Optional[str] = None
    alias_vector_index: Optional[str] = None
    alias_fulltext_index: Optional[str] = None
    embedding_model: Optional[str] = None
    embedding_dimension: Optional[str] = None
    reranker_model: Optional[str] = None
    top_k_per_search: Optional[str] = None
    total_candidates_spec: Optional[str] = None
    total_candidates_alias: Optional[str] = None
    final_results_limit: Optional[str] = None
    vector_weight: Optional[str] = None
    fulltext_weight: Optional[str] = None
    input_excel_file: Optional[str] = None
    # Existing fields
    APIGEE_ORGANIZATION: Optional[str] = None
    APIGEE_CLIENT_ID: Optional[str] = None
    APP_SHORT_KEY: str = "jbsltons"
    API_MONGODB_API_DB_URL: Optional[str] = None

    class Config:
        env_file = ".env"  # Specify the .env file to load

    def get(self, key: str, mandatory=True) -> str:
        if hasattr(self, key):
            return getattr(self, key)
        if os.environ.get(key):
            return os.environ.get(key)
        if mandatory:
            raise ValueError(f"Mandatory key: [{key}] not configured in env.")

        return None  # if not found and not mandatory


# Instantiate the ConfigService
config_service = ConfigService()
