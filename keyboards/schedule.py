"""
Keyboard builders for the schedule view (📅 Розклад).
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
            [
                InlineKeyboardButton(
                    text=t.DAY_BUTTON.format(day=1, date=_DAY_DATES[1]),
                    callback_data="schedule:day:1",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t.DAY_BUTTON.format(day=2, date=_DAY_DATES[2]),
                    callback_data="schedule:day:2",
                )
            ],
        ]
    )


def day_view_keyboard(activities: list[tuple]) -> InlineKeyboardMarkup:
    """
    Keyboard shown under a day's schedule.

    One row per regular (non-consultation) activity with a
    "Записатись" / "У лист очікування" button labeled with that
    activity's title (so it's clear which card the button belongs to),
    followed by a "back to days" row.

    `activities` is the same list of (Activity, booked_count) tuples
    used to render the schedule text.
    """
    rows: list[list[InlineKeyboardButton]] = []

    for activity, booked in activities:
        if activity.is_consultation_slot:
            continue

        free = activity.capacity - booked
        label = _truncate(activity.title, 24)

        if free > 0:
            text = f"{t.BOOK_BUTTON} · {label}"
            callback_data = f"book:{activity.id}"
        else:
            text = f"{t.WAITLIST_BUTTON} · {label}"
            callback_data = f"waitlist:{activity.id}"

        rows.append([InlineKeyboardButton(text=text, callback_data=callback_data)])

    rows.append([InlineKeyboardButton(text=t.BACK_TO_DAYS_BUTTON, callback_data="schedule:days")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def _truncate(text: str, max_length: int) -> str:
    """Shorten a title for use as a button label, adding an ellipsis if cut."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"


def day_label(day: int) -> str:
    """Return the formatted 'DD.MM.YYYY' date string for the given event day."""
    return _DAY_DATES[day]
