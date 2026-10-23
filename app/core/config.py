from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    database_url_direct: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 6  # sessions last 6 hours

    # Which ImageStorageRepository implementation to use (see
    # app/api/deps.py). "gcs" is currently the only one.
    storage_backend: str = "gcs"
    image_base_url: str = ""
    gcs_bucket_name: str = ""

    # RNG-01: the system is exclusively administrative, so the API schema
    # itself (Swagger/ReDoc/openapi.json) isn't exposed unless explicitly
    # enabled. Off by default so a deploy that forgets to set it stays safe;
    # set ENABLE_API_DOCS=true in the local .env for development.
    enable_api_docs: bool = False

    # Login throttling: after `login_max_attempts` consecutive failures the
    # account refuses logins for `login_lock_minutes`.
    login_max_attempts: int = 5
    login_lock_minutes: int = 15

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
