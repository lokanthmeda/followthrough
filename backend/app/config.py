"""Configuration for Followthrough backend."""
import os
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # pragma: no cover
    from pydantic import BaseSettings
    SettingsConfigDict = dict


class Settings(BaseSettings):
    # LLM settings — prefers OpenAI-compatible local proxy (FreeLLMAPI on 31415), fallback to Ollama (11434)
    llm_base_url: str = "http://127.0.0.1:31415"
    llm_api_key: str = "freellmapi-bb8abf6416b357ffb031f17050fc992adef709aedd98b28e"
    llm_model: str = "auto"
    llm_model_fast: str = "auto"
    ollama_base_url: str = "http://127.0.0.1:11434"

    # Whisper / Voice settings (WhisperFlow proxy on 31415)
    whisper_base_url: str = "http://127.0.0.1:31415"
    whisper_api_key: str = "freellmapi-bb8abf6416b357ffb031f17050fc992adef709aedd98b28e"

    # Database
    database_url: str = "sqlite+aiosqlite:///./followthrough.db"

    # Tracker
    tracker_provider: str = "linear"   # linear | github | mock
    linear_api_key: str = ""
    linear_api_url: str = "https://api.linear.app"

    # Notifications
    resend_api_key: str = ""
    slack_webhook_url: str = ""

    # Demo
    demo_clock_offset_hours: int = 0

    # App
    app_name: str = "Followthrough"
    app_version: str = "0.1.0"
    default_timezone: str = "Asia/Kolkata"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")


settings = Settings()