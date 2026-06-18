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


def consultation_picker_keyboard(day: int, slots: list[tuple]) -> InlineKeyboardMarkup:
    """
    Per-slot consultation picker: one button per 15-min slot.

    `slots` is a list of (Activity, booked_count) for the consultation
    slots, ordered by start time. Free slots are bookable; taken ones
    offer the waitlist.
    """
    from utils.time_utils import format_time

    rows: list[list[InlineKeyboardButton]] = []

    for activity, booked in slots:
        time_label = format_time(activity.start_time)
        if seats_free(activity.capacity, booked) > 0:
            rows.append([
                InlineKeyboardButton(
                    text=t.CONSULTATION_SLOT_FREE.format(time=time_label),
                    callback_data=f"bookact:{activity.id}",
                )
            ])
        else:
            rows.append([
                InlineKeyboardButton(
                    text=t.CONSULTATION_SLOT_TAKEN.format(time=time_label),
                    callback_data=f"bookwait:{activity.id}",
                )
            ])

    rows.append([InlineKeyboardButton(text=t.BACK_TO_DAYS_BUTTON, callback_data=f"bookday:{day}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_booking_keyboard(activity_id: int, back_cb: str) -> InlineKeyboardMarkup:
    """Confirmation card: confirm / edit data / back to where the user came from."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.CONFIRM_BUTTON, callback_data=f"bookconfirm:{activity_id}")],
            [InlineKeyboardButton(text=t.CONFIRM_EDIT_DATA_BUTTON, callback_data="bookeditdata")],
            [InlineKeyboardButton(text=t.CONFIRM_CANCEL_BUTTON, callback_data=back_cb)],
        ]
    )


def conflict_keyboard(
    conflict_booking_id: int, conflict_title: str, back_cb: str, target_activity_id: int | None = None
) -> InlineKeyboardMarkup:
    """Offer to cancel the conflicting booking, or go back."""
    cancel_cb = (
        f"bookcancel:{conflict_booking_id}:{target_activity_id}"
        if target_activity_id is not None
        else f"bookcancel:{conflict_booking_id}"
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t.CONFLICT_CANCEL_BUTTON.format(conflict_title=_truncate(conflict_title, 20)),
                    callback_data=cancel_cb,
                )
            ],
            [InlineKeyboardButton(text=t.CONFIRM_CANCEL_BUTTON, callback_data=back_cb)],
        ]
    )


def full_offer_waitlist_keyboard(activity_id: int, back_cb: str) -> InlineKeyboardMarkup:
    """When an activity is full: offer to join the waitlist, or go back."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.JOIN_WAITLIST_BUTTON, callback_data=f"bookwaitjoin:{activity_id}")],
            [InlineKeyboardButton(text=t.CONFIRM_CANCEL_BUTTON, callback_data=back_cb)],
        ]
    )


def conflict_cancelled_keyboard(target_activity_id: int) -> InlineKeyboardMarkup:
    """After cancelling a conflicting booking: offer to proceed with the originally wanted activity."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.CONFLICT_CANCELLED_TRY_AGAIN_BUTTON, callback_data=f"bookact:{target_activity_id}")],
            [InlineKeyboardButton(text=t.BACK_TO_DAYS_BUTTON, callback_data="bookdays")],
        ]
    )


def booked_ok_keyboard(day: int, back_cb: str) -> InlineKeyboardMarkup:
    """Shown after a successful booking: return to where the user came from (same day)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.BACK_TO_DAY_BUTTON.format(day=day), callback_data=back_cb)]
        ]
    )


def waitlist_offer_keyboard(entry_id: int) -> InlineKeyboardMarkup:
    """Buttons sent to a promoted waitlist user: confirm / decline the freed spot."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.WAITLIST_OFFER_CONFIRM_BUTTON, callback_data=f"wlconfirm:{entry_id}")],
            [InlineKeyboardButton(text=t.WAITLIST_OFFER_DECLINE_BUTTON, callback_data=f"wldecline:{entry_id}")],
        ]
    )


def attendance_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    """Attendance-confirmation buttons sent 30 min before an activity."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.CONFIRM_ATTENDANCE_BUTTON, callback_data=f"attyes:{booking_id}")],
            [InlineKeyboardButton(text=t.CANT_MAKE_BUTTON, callback_data=f"attno:{booking_id}")],
        ]
    )


def _truncate(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"
