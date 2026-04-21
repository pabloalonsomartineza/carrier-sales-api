from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_KEY: str = "dev-secret-key-change-in-prod"
    FMCSA_API_KEY: str = ""
    DATABASE_URL: str = "sqlite:///./calls.db"
    LOADS_FILE: str = "data/loads.json"
    MIN_RATE_FACTOR: float = 0.85  # minimum we'll accept = loadboard_rate * this factor

    class Config:
        env_file = ".env"


settings = Settings()
