from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OLLAMA_BASE_URL: str
    OLLAMA_MODEL: str
    MAX_ATTEMPTS: int
    API_HOST: str
    API_PORT: int
    API_BASE: str

    class Config:
        env_file = ".env"


settings = Settings()
