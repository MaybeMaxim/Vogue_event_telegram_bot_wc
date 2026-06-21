"""Keyboard builders for the admin panel."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from db.models import Activity, Booking, User
from texts import admin as t
from utils.time_utils import format_time


def _truncate(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.BTN_PARTICIPANTS, callback_data="adm:participants")],
            [InlineKeyboardButton(text=t.BTN_WAITLISTS, callback_data="adm:waitlists")],
            [InlineKeyboardButton(text=t.BTN_SEARCH, callback_data="adm:search")],
            [InlineKeyboardButton(text=t.BTN_ADD, callback_data="adm:add")],
            [InlineKeyboardButton(text=t.BTN_EXPORT, callback_data="adm:export")],
            [InlineKeyboardButton(text=t.BTN_QUESTIONS, callback_data="adm:questions")],
            [InlineKeyboardButton(text="👥 Адміни", callback_data="adm:admins")],
            [InlineKeyboardButton(text=t.BTN_CLOSE, callback_data="adm:close")],
        ]
    )


def activity_list_keyboard(
    activities: list[Activity], action: str, include_consultations: bool = False
) -> InlineKeyboardMarkup:
    """
    One button per (regular) activity, callback `adm:{action}:act:{id}`.
    If include_consultations, append a single combined "Консультації" entry
    with callback `adm:{action}:consult`.
    """
    rows = [
        [
            InlineKeyboardButton(
                text=t.ACTIVITY_BTN.format(
                    day=a.day, time=format_time(a.start_time), title=_truncate(a.title, 24)
                ),
                callback_data=f"adm:{action}:act:{a.id}",
            )
        ]
        for a in activities
    ]
    if include_consultations:
        rows.append([InlineKeyboardButton(text=t.CONSULT_LIST_BTN, callback_data=f"adm:{action}:consult")])
    rows.append([InlineKeyboardButton(text=t.BTN_BACK, callback_data="adm:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def participants_keyboard(activity_id: int, participants: list[tuple[Booking, User]]) -> InlineKeyboardMarkup:
    """Each participant is a toggle button for attendance; plus back."""
    from db.models import BookingStatus

    rows = []
    for booking, user in participants:
        mark = t.ATTENDED_MARK if booking.status == BookingStatus.ATTENDED else t.NOT_ATTENDED_MARK
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{mark} {_truncate(user.full_name, 28)}",
                    callback_data=f"adm:att:{booking.id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text=t.BTN_BACK, callback_data="adm:participants")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def guest_card_keyboard(bookings: list[tuple[Booking, Activity]]) -> InlineKeyboardMarkup:
    """Cancel buttons for each of a guest's bookings (admin view), plus back to menu."""
    rows = [
        [
            InlineKeyboardButton(
                text=t.CANCEL_BOOKING_BTN.format(
                    time=format_time(activity.start_time), title=_truncate(activity.title, 18)
                ),
                callback_data=f"adm:cancelbk:{booking.id}",
            )
        ]
        for booking, activity in bookings
    ]
    rows.append([InlineKeyboardButton(text=t.BTN_BACK, callback_data="adm:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def add_guest_results_keyboard(activity_id: int, guests: list[User]) -> InlineKeyboardMarkup:
    """Pick which found guest to add to the chosen activity."""
    rows = [
        [
            InlineKeyboardButton(
                text=t.ADD_GUEST_BTN.format(name=_truncate(u.full_name, 22), phone=u.phone),
                callback_data=f"adm:addto:{activity_id}:{u.id}",
            )
        ]
        for u in guests
    ]
    rows.append([InlineKeyboardButton(text=t.BTN_BACK, callback_data="adm:add")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def export_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.EXPORT_PARTICIPANTS_BTN, callback_data="adm:exp:participants")],
            [InlineKeyboardButton(text=t.EXPORT_CONTACTS_BTN, callback_data="adm:exp:contacts")],
            [InlineKeyboardButton(text=t.GSHEET_BTN, callback_data="adm:exp:gsheet")],
            [InlineKeyboardButton(text=t.BTN_BACK, callback_data="adm:menu")],
        ]
    )


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t.BTN_BACK, callback_data="adm:menu")]]
    )
