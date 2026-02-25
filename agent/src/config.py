from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model:   str = "claude-sonnet-4-6"

    # MCP server SSE endpoint
    mcp_server_url: str = "http://mcp-server:8002/sse"

    # Application
    app_env:   str = "development"
    log_level: str = "INFO"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
