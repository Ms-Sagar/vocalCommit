from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    gemini_api_key: Optional[str] = None
    
    model_config = {"env_file": ".env"}

settings = Settings()
