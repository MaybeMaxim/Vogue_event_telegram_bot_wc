from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, loaded from environment / .env file."""

    bot_token: str
    admin_ids: list[int] = []

    # The event runs 24-25.06 — the year is configurable so seed data
    # doesn't need to be edited by hand each time the bot is reused.
    event_year: int = 2026
    event_timezone: str = "Europe/Kyiv"

    # Support section configuration.
    # organizer_contact: a @username or t.me link shown to users who want
    #   to reach the organizer directly.
    # support_chat_id: chat (e.g. an admin group) where "ask a question"
    #   and "report a bug" submissions are forwarded. Falls back to the
    #   first admin id if left at 0.
    organizer_contact: str = "@organizer"
    support_chat_id: int = 0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def effective_support_chat_id(self) -> int | None:
        """Where to route support submissions: explicit chat, else first admin."""
        if self.support_chat_id:
            return self.support_chat_id
        if self.admin_ids:
            return self.admin_ids[0]
        return None


settings = Settings()
