from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    gemini_api_key: Optional[str] = Field(None, validation_alias="GEMINI_API_KEY")
    
    model_config = {"env_file": Path(__file__).parent.parent / ".env", "extra": "ignore"}

settings = Settings()
