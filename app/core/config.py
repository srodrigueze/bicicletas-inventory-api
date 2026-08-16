from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    database_url_direct: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 6  # sessions last 6 hours

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
