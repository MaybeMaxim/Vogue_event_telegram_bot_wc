"""
The periodic "ticker": a single job that runs every 60 seconds and drives
all time-based booking transitions. Using one periodic scan (rather than
scheduling thousands of one-off jobs) means the bot recovers correctly
after a restart — on the next tick it simply re-evaluates what's due.

Each pass, in order:
  1. Plain reminders (only for confirmation-EXEMPT activities).
  2. Attendance-confirmation requests (30 min before): CONFIRMED ->
     PENDING_CONFIRMATION, ask the user to confirm.
  3. No-show release (auto_release window): PENDING_CONFIRMATION still
     unconfirmed -> NO_SHOW, free the seat, promote the waitlist.
  4. Waitlist offer expiry: OFFERED past its deadline -> EXPIRED, offer to
     the next person.

Idempotency: reminder_sent / confirmation_sent flags and the status
transitions themselves keep each item from being processed twice.

All comparisons use timezone-aware UTC; activity start times are stored
naive-UTC (see utils.time_utils), so they're treated as UTC here.
"""

import html
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings
from db.base import async_session
from db.crud import bookings as bookings_crud
from db.crud import waitlist as waitlist_crud
from db.crud.activities import get_activity_by_id
from keyboards.booking import attendance_keyboard, waitlist_offer_keyboard
from services import booking_actions as actions
from texts import booking as t
from utils.time_utils import display_title, format_time_range

logger = logging.getLogger(__name__)

_TICK_SECONDS = 60


def _naive_utc(dt: datetime) -> datetime:
    """Return a naive-UTC datetime (matching how activity times are stored)."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


async def _send(bot: Bot, tg_id: int, text: str, reply_markup=None) -> bool:
    """Best-effort send; returns False if the user blocked the bot etc."""
    try:
        await bot.send_message(tg_id, text, reply_markup=reply_markup)
        return True
    except Exception:
        logger.exception("Ticker failed to message user %s", tg_id)
        return False


async def _user_tg_id(session, user_pk: int) -> int | None:
    from sqlalchemy import select
    from db.models import User

    user = (await session.execute(select(User).where(User.id == user_pk))).scalar_one_or_none()
    return user.tg_id if user else None


async def tick(bot: Bot) -> None:
    """One pass of the ticker. Safe to call repeatedly."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    async with async_session() as session:
        await _process_reminders(session, bot, now)
        await _process_confirmations(session, bot, now)
        await _process_no_shows(session, bot, now)
        await _process_waitlist_expiry(session, bot, now)

    # Push any booking changes to Google Sheets (no-op if disabled / clean).
    try:
        from services.sheets_service import sync_if_dirty

        await sync_if_dirty()
    except Exception:
        logger.exception("Google Sheets sync step failed")


async def _process_reminders(session, bot: Bot, now: datetime) -> None:
    threshold = now + timedelta(minutes=settings.reminder_minutes)
    due = await bookings_crud.bookings_due_for_reminder(session, now, threshold)

    for booking, activity in due:
        tg_id = await _user_tg_id(session, booking.user_id)
        if tg_id is None:
            continue
        await _send(
            bot,
            tg_id,
            t.REMINDER.format(
                title=html.escape(display_title(activity)),
                time_range=format_time_range(activity.start_time, activity.end_time),
                location=html.escape(activity.location_text),
            ),
        )
        await bookings_crud.mark_reminder_sent(session, booking)


async def _process_confirmations(session, bot: Bot, now: datetime) -> None:
    threshold = now + timedelta(minutes=settings.confirmation_minutes)
    due = await bookings_crud.bookings_due_for_confirmation(session, now, threshold)

    for booking, activity in due:
        tg_id = await _user_tg_id(session, booking.user_id)
        if tg_id is None:
            continue
        # Flip to PENDING_CONFIRMATION first so a crash mid-loop doesn't
        # re-send; the message carries the location (doubles as reminder).
        await bookings_crud.mark_confirmation_requested(session, booking)
        await _send(
            bot,
            tg_id,
            t.CONFIRMATION_REQUEST.format(
                title=html.escape(display_title(activity)),
                time_range=format_time_range(activity.start_time, activity.end_time),
                location=html.escape(activity.location_text),
            ),
            reply_markup=attendance_keyboard(booking.id),
        )


async def _process_no_shows(session, bot: Bot, now: datetime) -> None:
    threshold = now + timedelta(minutes=settings.auto_release_minutes)
    due = await bookings_crud.bookings_due_for_release(session, threshold)

    for booking, activity in due:
        await bookings_crud.mark_no_show(session, booking)

        tg_id = await _user_tg_id(session, booking.user_id)
        if tg_id is not None:
            await _send(bot, tg_id, t.NO_SHOW_RELEASED.format(title=html.escape(display_title(activity))))

        await _promote(session, bot, activity.id)


async def _process_waitlist_expiry(session, bot: Bot, now: datetime) -> None:
    for entry in await waitlist_crud.expired_offers(session, now):
        activity_id = entry.activity_id
        await waitlist_crud.mark_expired(session, entry)

        tg_id = await _user_tg_id(session, entry.user_id)
        if tg_id is not None:
            await _send(bot, tg_id, t.WAITLIST_OFFER_EXPIRED)

        await _promote(session, bot, activity_id)


async def _promote(session, bot: Bot, activity_id: int) -> None:
    """Offer a freed seat to the next waiting user and notify them."""
    entry = await actions.offer_next_in_waitlist(session, activity_id)
    if entry is None:
        return

    activity = await get_activity_by_id(session, activity_id)
    tg_id = await _user_tg_id(session, entry.user_id)
    if activity is None or tg_id is None:
        return

    await _send(
        bot,
        tg_id,
        t.WAITLIST_OFFER.format(
            title=html.escape(display_title(activity)),
            time_range=format_time_range(activity.start_time, activity.end_time),
            minutes=settings.waitlist_confirm_minutes,
        ),
        reply_markup=waitlist_offer_keyboard(entry.id),
    )


def start_ticker(bot: Bot) -> AsyncIOScheduler:
    """Create and start the AsyncIOScheduler running tick() every 60s."""
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(tick, "interval", seconds=_TICK_SECONDS, args=[bot], id="ticker", max_instances=1)
    scheduler.start()
    return scheduler
