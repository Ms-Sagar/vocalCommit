from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    gemini_api_key: Optional[str] = None
    
    model_config = {"env_file": Path(__file__).parent.parent / ".env"}

settings = Settings()
