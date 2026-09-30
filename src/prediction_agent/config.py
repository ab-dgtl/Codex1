from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_token: str = Field(min_length=24)
    database_path: str = "data/agent.db"
    poll_seconds: float = Field(default=2, ge=0.1)
    telegram_bot_token: str = ""
    telegram_allowed_user_ids: str = ""
    provider_url: str = ""
    provider_allowed_hosts: str = ""
    provider_api_key: str = ""
    llm_url: str = "https://api.openai.com/v1/chat/completions"
    llm_api_key: str = ""
    llm_model: str = ""
