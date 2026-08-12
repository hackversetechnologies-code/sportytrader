"""
Central configuration. Loaded once from environment variables / .env file.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # API-Football
    api_football_key: str
    api_football_base_url: str = "https://v3.football.api-sports.io"
    # Pro plan limits (per docs): 7500/day, 300/min (5 req/sec)
    api_football_max_per_second: float = 5.0
    api_football_max_per_day: int = 7500

    # Telegram
    telegram_bot_token: str
    telegram_chat_id: str

    # Database
    database_url: str = "sqlite+aiosqlite:///./no3bot.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # App
    timezone: str = "Africa/Lagos"
    log_level: str = "INFO"

    # Pipeline scheduling (runs at 10 PM / 22:00 daily)
    daily_run_hour: int = 22
    daily_run_minute: int = 0
    recheck_interval_minutes: int = 5
    recheck_window_minutes: int = 100  # trigger recheck for fixtures kicking off within this window


@lru_cache
def get_settings() -> Settings:
    return Settings()
