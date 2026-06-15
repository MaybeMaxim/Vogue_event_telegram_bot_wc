"""
Keyboard builders for the booking drill-down ("✍️ Записатись").

Callback-data scheme:
  bookday:{day}                       -> show slot picker for a day
  bookslot:{day}:{anchor_activity_id} -> show activity picker for a slot
                                         (anchor = first activity in the
                                         slot; its start/end identify the
                                         whole slot)
  bookact:{activity_id}               -> book a specific activity
  bookwait:{activity_id}              -> join waitlist for a full activity
  bookconsult:{day}                   -> enter consultation slot picker
  bookdays                            -> back to day picker

Encoding the anchor activity id (rather than raw timestamps) keeps
callback data well under Telegram's 64-byte limit.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import settings
from services.booking_service import Slot, slot_button_label
from texts import booking as t
from utils.status_emoji import seats_free

_DAY_DATES = {
    1: f"24.06.{settings.event_year}",
    2: f"25.06.{settings.event_year}",
}


def day_label(day: int) -> str:
    return _DAY_DATES[day]


def day_picker_keyboard() -> InlineKeyboardMarkup:
    """Step 1: choose a day to book on."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"День 1 ({_DAY_DATES[1]})", callback_data="bookday:1")],
            [InlineKeyboardButton(text=f"День 2 ({_DAY_DATES[2]})", callback_data="bookday:2")],
        ]
    )


def slot_picker_keyboard(day: int, slots: list[Slot]) -> InlineKeyboardMarkup:
    """Step 2: one button per time slot on the chosen day."""
    rows: list[list[InlineKeyboardButton]] = []

    for slot in slots:
        anchor_id = slot.activities[0][0].id

        if slot.is_consultation:
            from utils.time_utils import format_time_range

            text = t.CONSULTATION_SLOT_BUTTON.format(
                time_range=format_time_range(slot.start_time, slot.end_time)
            )
            callback_data = f"bookconsult:{day}"
        else:
            text = slot_button_label(slot)
            callback_data = f"bookslot:{day}:{anchor_id}"

        rows.append([InlineKeyboardButton(text=text, callback_data=callback_data)])

    rows.append([InlineKeyboardButton(text=t.BACK_TO_DAYS_BUTTON, callback_data="bookdays")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def activity_picker_keyboard(day: int, slot: Slot) -> InlineKeyboardMarkup:
    """Step 3: one "Записатись" / "Лист очікування" button per activity in the slot."""
    rows: list[list[InlineKeyboardButton]] = []

    for activity, booked in slot.activities:
        free = seats_free(activity.capacity, booked)
        if free > 0:
            text = t.BOOK_ACTIVITY_BUTTON.format(title=_truncate(activity.title, 28))
            callback_data = f"bookact:{activity.id}"
        else:
            text = t.WAITLIST_ACTIVITY_BUTTON.format(title=_truncate(activity.title, 26))
            callback_data = f"bookwait:{activity.id}"
        rows.append([InlineKeyboardButton(text=text, callback_data=callback_data)])

    rows.append([InlineKeyboardButton(text=t.BACK_TO_SLOTS_BUTTON, callback_data=f"bookday:{day}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _truncate(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"
