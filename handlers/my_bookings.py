"""
Handler for the 📋 Мої записи section.

Lists the user's active bookings and lets them cancel any of them.
Cancelling frees the seat and promotes the next person on that
activity's waitlist (reusing the booking-flow helper).
"""

import html

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.crud.activities import get_activity_by_id
from db.crud.bookings import get_booking_by_id, list_user_bookings
from db.crud.users import get_user_by_tg_id
from keyboards.main_menu import MENU_MY_BOOKINGS
from keyboards.my_bookings import my_bookings_keyboard
from services import booking_actions as actions
from texts import my_bookings as t
from utils.time_utils import format_time_range

router = Router(name="my_bookings")


async def _render_list(message: Message, session: AsyncSession, tg_id: int, edit: bool = False) -> None:
    user = await get_user_by_tg_id(session, tg_id)
    if user is None:
        return

    bookings = await list_user_bookings(session, user.id)

    if not bookings:
        text, markup = t.MY_BOOKINGS_EMPTY, None
    else:
        text = _render_grouped(bookings)
        markup = my_bookings_keyboard(bookings)

    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)


def _render_grouped(bookings) -> str:
    """Group bookings by event day, each under a day header, sorted by time."""
    from collections import OrderedDict

    by_day: "OrderedDict[int, list]" = OrderedDict()
    for booking, activity in bookings:
        by_day.setdefault(activity.day, []).append((booking, activity))

    blocks = [t.MY_BOOKINGS_HEADER]
    for day in sorted(by_day):
        lines = [t.DAY_SECTION.format(day=day, date=_day_date(day))]
        for _, activity in by_day[day]:
            entry = t.BOOKING_ENTRY.format(
                time_range=format_time_range(activity.start_time, activity.end_time),
                title=html.escape(activity.title),
            )
            if activity.location_text:
                entry += "\n" + t.BOOKING_LOCATION.format(location=html.escape(activity.location_text))
            lines.append(entry)
        blocks.append("\n".join(lines))

    return "\n\n".join(blocks)


def _day_date(day: int) -> str:
    return f"24.06.{settings.event_year}" if day == 1 else f"25.06.{settings.event_year}"


@router.message(F.text == MENU_MY_BOOKINGS)
async def open_my_bookings(message: Message, session: AsyncSession) -> None:
    await _render_list(message, session, message.from_user.id)


@router.callback_query(F.data.startswith("mycancel:"))
async def cancel_my_booking(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    booking_id = int(callback.data.split(":")[1])
    booking = await get_booking_by_id(session, booking_id)

    if booking is None:
        await callback.answer(t.CANCEL_FAILED, show_alert=True)
        return

    activity = await get_activity_by_id(session, booking.activity_id)
    title = html.escape(activity.title) if activity else ""

    freed_activity = await actions.cancel_booking(session, booking)
    await callback.answer(t.CANCELLED_OK.format(title=title))

    # Re-render the updated list in place.
    await _render_list(callback.message, session, callback.from_user.id, edit=True)

    # Promote the next waitlisted user for the freed seat.
    if freed_activity is not None:
        from handlers.booking import _promote_waitlist

        await _promote_waitlist(session, bot, freed_activity.id)
