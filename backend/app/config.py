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
    pagespeed_api_key: str = ""
    gsc_oauth_client_id: str = ""
    gsc_oauth_client_secret: str = ""
    gsc_oauth_redirect_uri: str = ""
    gsc_auto_sync_days: int = 28
    gsc_auto_sync_min_interval_hours: int = 24
    bing_webmaster_api_key: str = ""
    indexnow_key: str = ""
    indexnow_key_location: str = ""
    brightdata_browser_ws: str = ""
    brightdata_dataset_api_key: str = ""
    brightdata_serp_dataset_id: str = "gd_mfz5x93lmsjjjylob"
    brightdata_serp_endpoint: str = "https://api.brightdata.com/datasets/v3/scrape"
    onsite_render_js_enabled: bool = True
    onsite_render_timeout_ms: int = 30000
    perplexity_api_key: str = ""
    you_api_key: str = ""
    exa_api_key: str = ""
    tavily_api_key: str = ""
    bocha_api_key: str = ""
    bocha_web_search_url: str = "https://api.bochaai.com/v1/web-search"
    dashscope_api_key: str = ""
    bailian_model: str = "qwen-plus"
    bailian_chat_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"


settings = Settings()
