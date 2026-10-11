from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    database_url_direct: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 6  # sessions last 6 hours

    image_base_url: str = ""
    gcs_bucket_name: str = ""

    # RNG-01: the system is exclusively administrative, so the API schema
    # itself (Swagger/ReDoc/openapi.json) isn't exposed in production —
    # disabled via env var, left on by default for dev/test convenience.
    enable_api_docs: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
