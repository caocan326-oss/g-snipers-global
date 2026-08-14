from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://gsnipers:gsnipers@localhost:5432/gsnipers"
    secret_key: str = "dev-only-change-me"
    access_token_expire_minutes: int = 720
    frontend_origin: str = "http://localhost:3000"
    demo_am_email: str = "am@demo.gsnipers.com"
    demo_am_password: str = "demo1234"
    distribution_directory_api_key: str = ""
    distribution_guest_api_key: str = ""
    distribution_syndication_api_key: str = ""
    # One OpenAI-compatible gateway. Empty key = app still boots; AI returns 未配置.
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"


settings = Settings()
