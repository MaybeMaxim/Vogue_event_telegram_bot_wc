"""
Handler for the 📋 Мої записи section.

Lists the user's active bookings and waitlist entries, lets them cancel
bookings or leave the waitlist. Cancelling a booking frees the seat and
promotes the next person on that activity's waitlist.
"""

import html

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.crud.activities import get_activity_by_id
from db.crud.bookings import get_booking_by_id, list_user_bookings
from db.crud.users import get_user_by_tg_id
from db.crud.waitlist import list_user_waitlist_entries, waitlist_position, get_waitlist_entry_by_id
from db.models import WaitlistStatus
from keyboards.main_menu import MENU_MY_BOOKINGS
from keyboards.my_bookings import my_bookings_keyboard
from services import booking_actions as actions
from texts import my_bookings as t
from utils.time_utils import display_title, format_time_range

router = Router(name="my_bookings")


async def _render_list(message: Message, session: AsyncSession, tg_id: int, edit: bool = False) -> None:
    user = await get_user_by_tg_id(session, tg_id)
    if user is None:
        return

    bookings = await list_user_bookings(session, user.id)
    waitlist = await list_user_waitlist_entries(session, user.id)

    if not bookings and not waitlist:
        text, markup = t.MY_BOOKINGS_EMPTY, None
    else:
        text = await _render_grouped(session, bookings, waitlist)
        markup = my_bookings_keyboard(bookings, waitlist)

    if edit:
        try:
            await message.edit_text(text, reply_markup=markup)
        except TelegramBadRequest:
            pass
    else:
        await message.answer(text, reply_markup=markup)


async def _render_grouped(session, bookings, waitlist) -> str:
    """Group bookings by day, then list waitlist entries in a separate section."""
    from collections import OrderedDict

    blocks = [t.MY_BOOKINGS_HEADER]

    if bookings:
        by_day: "OrderedDict[int, list]" = OrderedDict()
        for booking, activity in bookings:
            by_day.setdefault(activity.day, []).append((booking, activity))

        for day in sorted(by_day):
            entries = []
            for _, activity in by_day[day]:
                entry = t.BOOKING_ENTRY.format(
                    time_range=format_time_range(activity.start_time, activity.end_time),
                    title=html.escape(display_title(activity)),
                )
                if activity.location_text:
                    entry += "\n" + t.BOOKING_LOCATION.format(location=html.escape(activity.location_text))
                entries.append(entry)
            day_block = t.DAY_SECTION.format(day=day, date=_day_date(day)) + "\n\n" + "\n\n".join(entries)
            blocks.append(day_block)

    if waitlist:
        wl_lines = [t.WAITLIST_SECTION_HEADER]
        for entry, activity in waitlist:
            if entry.status == WaitlistStatus.OFFERED:
                line = t.WAITLIST_ENTRY_OFFERED.format(
                    time_range=format_time_range(activity.start_time, activity.end_time),
                    title=html.escape(display_title(activity)),
                )
            else:
                pos = await waitlist_position(session, entry)
                line = t.WAITLIST_ENTRY.format(
                    time_range=format_time_range(activity.start_time, activity.end_time),
                    title=html.escape(display_title(activity)),
                    position=pos,
                )
            wl_lines.append(line)
        blocks.append("\n".join(wl_lines))

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
    user = await get_user_by_tg_id(session, callback.from_user.id)

    if booking is None or user is None or booking.user_id != user.id:
        await callback.answer(t.CANCEL_FAILED, show_alert=True)
        return

    activity = await get_activity_by_id(session, booking.activity_id)
    title = html.escape(display_title(activity)) if activity else ""

    if activity is not None:
        from datetime import datetime, timedelta, timezone
        from config import settings
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=settings.clock_offset_minutes)
        if activity.start_time <= now_utc:
            await callback.answer(t.CANCEL_EVENT_STARTED, show_alert=True)
            return

    freed_activity = await actions.cancel_booking(session, booking)
    await callback.answer(t.CANCELLED_OK.format(title=title))

    await _render_list(callback.message, session, callback.from_user.id, edit=True)

    if freed_activity is not None:
        from handlers.booking import _promote_waitlist

        await _promote_waitlist(session, bot, freed_activity.id)


@router.callback_query(F.data.startswith("mywlleave:"))
async def leave_waitlist(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    entry_id = int(callback.data.split(":")[1])
    entry = await get_waitlist_entry_by_id(session, entry_id)

    if entry is None or entry.status not in (WaitlistStatus.WAITING, WaitlistStatus.OFFERED):
        await callback.answer(t.WAITLIST_LEAVE_FAILED, show_alert=True)
        return

    activity = await get_activity_by_id(session, entry.activity_id)
    title = html.escape(display_title(activity)) if activity else ""
    was_offered = entry.status == WaitlistStatus.OFFERED
    activity_id = entry.activity_id

    from db.crud.waitlist import mark_expired
    await mark_expired(session, entry)

    await callback.answer(t.WAITLIST_LEFT_OK.format(title=title))
    await _render_list(callback.message, session, callback.from_user.id, edit=True)

    # If the entry was OFFERED the seat intent is now freed — promote the next
    # person in queue immediately rather than waiting for the ticker.
    if was_offered:
        from handlers.booking import _promote_waitlist
        await _promote_waitlist(session, bot, activity_id)
