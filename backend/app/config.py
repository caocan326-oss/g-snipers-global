from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://gsnipers:gsnipers@localhost:5432/gsnipers"
    secret_key: str = "dev-only-change-me"
    access_token_expire_minutes: int = 720
    frontend_origin: str = "http://localhost:3000"
    demo_am_email: str = "am@demo.local"
    demo_am_password: str = "demo1234"


settings = Settings()
