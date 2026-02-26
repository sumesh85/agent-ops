from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # PostgreSQL (read-only access)
    postgres_host:     str = "db"
    postgres_port:     int = 5432
    postgres_db:       str = "casepilot"
    postgres_user:     str = "casepilot"
    postgres_password: str = "casepilot_dev_secret"

    # Redis
    redis_host:          str = "redis"
    redis_port:          int = 6379
    redis_ttl_tool_call: int = 60
    redis_ttl_policy:    int = 300
    redis_ttl_cases:     int = 120

    # ChromaDB
    chroma_host:                 str = "chroma"
    chroma_port:                 int = 8000
    chroma_collection_policies:  str = "policies"
    chroma_collection_cases:     str = "case_embeddings"

    # MCP server
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8002

    @property
    def database_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}"

    @property
    def chroma_url(self) -> str:
        return f"http://{self.chroma_host}:{self.chroma_port}"


@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
