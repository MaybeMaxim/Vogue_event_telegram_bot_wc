"""
Keyboard builders for the booking drill-down ("✍️ Записатись").

Callback-data scheme:
  bookday:{day}                      -> category picker for a day
  bookcat:{day}:{anchor_activity_id} -> sub-slot picker for a category
  bookact:{activity_id}              -> booking confirmation card
  bookwait:{activity_id}             -> join waitlist for a full activity
  bookconsult:{day}                  -> consultation sub-slot picker
  bookdays                           -> back to day picker
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import settings
from services.booking_service import CategoryGroup
from texts import booking as t
from utils.status_emoji import seats_free, status_emoji
from utils.time_utils import format_time, format_time_range

_DAY_DATES = {
    1: f"24.06.{settings.event_year}",
    2: f"25.06.{settings.event_year}",
}


def day_label(day: int) -> str:
    return _DAY_DATES[day]


def day_picker_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"День 1 ({_DAY_DATES[1]})", callback_data="bookday:1")],
            [InlineKeyboardButton(text=f"День 2 ({_DAY_DATES[2]})", callback_data="bookday:2")],
        ]
    )


def category_picker_keyboard(day: int, categories: list[CategoryGroup]) -> InlineKeyboardMarkup:
    """Step 2: one button per activity category."""
    rows: list[list[InlineKeyboardButton]] = []

    for cat in categories:
        dot = status_emoji(cat.total_capacity, cat.total_booked)
        label = f"{dot} {cat.name}"

        if cat.is_consultation:
            cb = f"bookconsult:{day}"
        else:
            cb = f"bookcat:{day}:{cat.anchor_id}"

        rows.append([InlineKeyboardButton(text=label, callback_data=cb)])

    rows.append([InlineKeyboardButton(text=t.BACK_TO_DAYS_BUTTON, callback_data="bookdays")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def subslot_picker_keyboard(day: int, cat: CategoryGroup) -> InlineKeyboardMarkup:
    """
    Step 3: time-slot buttons for a chosen category.

    Multi-slot categories (test-drives, Kérastase): each sub-slot gets its
    own button showing the start time and free/total seats.
    Single-slot categories (Barre, Sound Healing): one big Записатись button.
    """
    rows: list[list[InlineKeyboardButton]] = []

    if len(cat.activities) == 1:
        # Single slot — one prominent action button
        a, booked = cat.activities[0]
        free = seats_free(a.capacity, booked)
        time_range = format_time_range(a.start_time, a.end_time)
        if free > 0:
            label = f"✅ {time_range} ({free} з {a.capacity}) — Записатись"
            cb = f"bookact:{a.id}"
        else:
            label = f"🔴 {time_range} — Лист очікування"
            cb = f"bookwait:{a.id}"
        rows.append([InlineKeyboardButton(text=label, callback_data=cb)])
    else:
        # Multiple sub-slots: 2 per row for ≤6 (test-drives), 3 per row for 12 (Kérastase)
        per_row = 2 if len(cat.activities) <= 6 else 3
        row: list[InlineKeyboardButton] = []
        for a, booked in cat.activities:
            free = seats_free(a.capacity, booked)
            time_str = format_time(a.start_time)
            if free > 0:
                # Show seat count only when capacity > 1 (skip for Kérastase cap=1)
                suffix = f" ({free}/{a.capacity})" if a.capacity > 1 else ""
                label = f"🟢 {time_str}{suffix}"
                cb = f"bookact:{a.id}"
            else:
                label = f"🔴 {time_str}"
                cb = f"bookwait:{a.id}"
            row.append(InlineKeyboardButton(text=label, callback_data=cb))
            if len(row) == per_row:
                rows.append(row)
                row = []
        if row:
            rows.append(row)

    rows.append([
        InlineKeyboardButton(text=t.BACK_TO_CATEGORIES_BUTTON, callback_data=f"bookday:{day}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def consultation_picker_keyboard(day: int, slots: list[tuple]) -> InlineKeyboardMarkup:
    """Per-slot consultation picker: one button per 20-min slot."""
    rows: list[list[InlineKeyboardButton]] = []

    row: list[InlineKeyboardButton] = []
    for activity, booked in slots:
        time_label = format_time(activity.start_time)
        free = seats_free(activity.capacity, booked)
        if free > 0:
            label = f"🟢 {time_label}"
            cb = f"bookact:{activity.id}"
        else:
            label = f"🔴 {time_label}"
            cb = f"bookwait:{activity.id}"
        row.append(InlineKeyboardButton(text=label, callback_data=cb))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append([InlineKeyboardButton(text=t.BACK_TO_CATEGORIES_BUTTON, callback_data=f"bookday:{day}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_only_keyboard(back_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb)],
        ]
    )


def confirm_booking_keyboard(activity_id: int, back_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Підтвердити запис", callback_data=f"bookconfirm:{activity_id}")],
            [InlineKeyboardButton(text="✏️ Змінити мої дані", callback_data="bookeditdata")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb)],
        ]
    )


def conflict_keyboard(
    conflict_booking_id: int, conflict_title: str, back_cb: str, target_activity_id: int | None = None
) -> InlineKeyboardMarkup:
    cancel_cb = (
        f"bookcancel:{conflict_booking_id}:{target_activity_id}"
        if target_activity_id is not None
        else f"bookcancel:{conflict_booking_id}"
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=f"❌ Скасувати «{_truncate(conflict_title, 20)}»",
                callback_data=cancel_cb,
            )],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb)],
        ]
    )


def full_offer_waitlist_keyboard(activity_id: int, back_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔔 Так, у лист очікування", callback_data=f"bookwaitjoin:{activity_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb)],
        ]
    )


def conflict_cancelled_keyboard(target_activity_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Записатись тепер", callback_data=f"bookact:{target_activity_id}")],
            [InlineKeyboardButton(text=t.BACK_TO_DAYS_BUTTON, callback_data="bookdays")],
        ]
    )


def booked_ok_keyboard(day: int, back_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"⬅️ Повернутись до Дня {day}", callback_data=back_cb)]
        ]
    )


def waitlist_offer_keyboard(entry_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Підтвердити запис", callback_data=f"wlconfirm:{entry_id}")],
            [InlineKeyboardButton(text="❌ Відмовитись", callback_data=f"wldecline:{entry_id}")],
        ]
    )


def attendance_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Я буду", callback_data=f"attyes:{booking_id}")],
            [InlineKeyboardButton(text="❌ Не зможу", callback_data=f"attno:{booking_id}")],
        ]
    )


def _truncate(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"
