from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    database_url: str = "sqlite:///./pathly.db"
    jwt_secret: str = "development-only-change-me"
    ai_provider: str = "mock"
    ai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"
    ai_base_url: str = "https://api.openai.com/v1"
    ai_timeout_seconds: float = 12.0
    frontend_url: str = "http://localhost:5173"
    opportunity_discovery_provider: str = "demo"
    opportunity_search_api_key: str = ""
    opportunity_search_base_url: str = "https://google.serper.dev/search"
    opportunity_search_timeout_seconds: float = 10.0
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
settings=Settings()
