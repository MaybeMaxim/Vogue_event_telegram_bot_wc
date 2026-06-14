from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, loaded from environment / .env file."""

    bot_token: str
    admin_ids: list[int] = []

    # The event runs 24-25.06 — the year is configurable so seed data
    # doesn't need to be edited by hand each time the bot is reused.
    event_year: int = 2026
    event_timezone: str = "Europe/Kyiv"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
