"""
Keyboard builders for the read-only schedule view (📅 Розклад).

Booking buttons live in the "✍️ Записатись" flow now — this view only
navigates between the two days.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import settings
from texts import schedule as t

# Event dates, derived once from config.event_year (24-25.06).
_DAY_DATES = {
    1: f"24.06.{settings.event_year}",
    2: f"25.06.{settings.event_year}",
}


def day_picker_keyboard() -> InlineKeyboardMarkup:
    """Inline buttons to choose Day 1 / Day 2."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.DAY_BUTTON.format(day=1, date=_DAY_DATES[1]), callback_data="schedule:day:1")],
            [InlineKeyboardButton(text=t.DAY_BUTTON.format(day=2, date=_DAY_DATES[2]), callback_data="schedule:day:2")],
        ]
    )


def day_view_keyboard() -> InlineKeyboardMarkup:
    """Shown under a day's schedule: switch back to the day picker."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.BACK_TO_DAYS_BUTTON, callback_data="schedule:days")]
        ]
    )


def day_label(day: int) -> str:
    """Return the formatted 'DD.MM.YYYY' date string for the given event day."""
    return _DAY_DATES[day]
