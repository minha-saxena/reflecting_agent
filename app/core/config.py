from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OLLAMA_BASE_URL: str
    OLLAMA_MODEL: str
    OLLAMA_MAX_RETRIES: int = 3
    OLLAMA_RETRY_DELAY: float = 0.5

    MAX_ATTEMPTS: int
    API_HOST: str
    API_PORT: int
    API_BASE: str

    class Config:
        env_file = ".env"


settings = Settings()