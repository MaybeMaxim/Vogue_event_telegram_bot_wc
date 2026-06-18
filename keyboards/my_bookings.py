"""Keyboard builder for the 📋 Мої записи section."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from db.models import Activity, Booking, Waitlist
from texts import my_bookings as t
from utils.time_utils import format_time


def _truncate(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"


def my_bookings_keyboard(
    bookings: list[tuple[Booking, Activity]],
    waitlist_entries: list[tuple[Waitlist, Activity]] | None = None,
) -> InlineKeyboardMarkup:
    """Cancel buttons for active bookings + leave-queue buttons for waitlist entries."""
    rows = [
        [
            InlineKeyboardButton(
                text=t.CANCEL_BUTTON.format(
                    time=format_time(activity.start_time),
                    title=_truncate(activity.title, 20),
                ),
                callback_data=f"mycancel:{booking.id}",
            )
        ]
        for booking, activity in bookings
    ]
    for entry, activity in (waitlist_entries or []):
        rows.append([
            InlineKeyboardButton(
                text=t.WAITLIST_LEAVE_BUTTON.format(
                    time=format_time(activity.start_time),
                    title=_truncate(activity.title, 20),
                ),
                callback_data=f"mywlleave:{entry.id}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
