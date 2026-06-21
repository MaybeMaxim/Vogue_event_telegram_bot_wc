from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, loaded from environment / .env file."""

    bot_token: str
    admin_ids: list[int] = []

    # The event runs 24-25.06 — the year is configurable so seed data
    # doesn't need to be edited by hand each time the bot is reused.
    # For testing, override event_day1/event_day2 in .env to shift the
    # actual activity datetimes without touching the display labels.
    event_year: int = 2026
    event_month: int = 6
    event_day1: int = 24
    event_day2: int = 25
    event_timezone: str = "Europe/Kyiv"

    # Support section configuration.
    # organizer_contact: a @username or t.me link shown to users who want
    #   to reach the organizer directly.
    # support_chat_id: chat (e.g. an admin group) where "ask a question"
    #   and "report a bug" submissions are forwarded. Falls back to the
    #   first admin id if left at 0.
    organizer_contact: str = "+380989273051"
    support_chat_id: int = 0

    # Booking configuration.
    # consultation_slot_minutes: length of each Anna Barinova consultation
    #   slot (divided into back-to-back slots of this length).
    # waitlist_confirm_minutes: how long a promoted waitlist user has to
    #   confirm an offered spot before it passes to the next person.
    consultation_slot_minutes: int = 20
    waitlist_confirm_minutes: int = 5

    # Time-driven (ticker) windows, in minutes before an activity starts:
    #   reminder_minutes: location reminder to booked users + free-seat broadcast to others.
    #   free_seat_broadcast_minutes: "last chance" free-seat broadcast to non-booked users.
    reminder_minutes: int = 30
    free_seat_broadcast_minutes: int = 10

    # Testing only: shift the ticker's clock by this many minutes (negative = go back in time).
    # Set to 0 (or remove) for production. Does not affect user-facing times or booking locks.
    clock_offset_minutes: int = 0

    # Deadline for anonymous sexologist questions: naive UTC datetime
    # string "YYYY-MM-DD HH:MM" (Europe/Kyiv 14:00 on Day 2 = UTC 11:00).
    sexologist_question_deadline: str = "2026-06-25 11:00"

    # Google Sheets live sync (optional).
    # gsheets_enabled: master switch; if False the bot skips all Sheets work.
    # gsheets_credentials_file: path to the service-account JSON key.
    # gsheets_spreadsheet_id: the target spreadsheet's id (from its URL). If
    #   empty, the bot creates a new spreadsheet on first sync and logs the
    #   id/URL so you can share it with the team.
    # gsheets_sync_seconds: how often the periodic sync runs.
    gsheets_enabled: bool = False
    gsheets_credentials_file: str = "google_credentials.json"
    gsheets_spreadsheet_id: str = ""
    gsheets_sync_seconds: int = 60

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
