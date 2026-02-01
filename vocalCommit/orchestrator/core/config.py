from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    gemini_api_key: Optional[str] = Field(None, validation_alias="GEMINI_API_KEY")
    
    # GitHub configuration for production todo-ui repo
    github_token: Optional[str] = Field(None, validation_alias="GITHUB_TOKEN")
    todo_ui_repo_url: str = Field("https://github.com/Ms-Sagar/TODO-UI.git", validation_alias="TODO_UI_REPO_URL")
    todo_ui_local_path: str = Field("todo-ui", validation_alias="TODO_UI_LOCAL_PATH")
    
    model_config = {"env_file": Path(__file__).parent.parent / ".env", "extra": "ignore"}

settings = Settings()
