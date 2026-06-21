"""
The periodic "ticker": a single job that runs every 60 seconds and drives
all time-based booking transitions.

Each pass, in order:
  1. T-30 min: reminder with location → all booked users (grouped per user
     by start_time, so two concurrent activities → one message).
     "ЗБІР ГОСТЕЙ" is excluded (walk-in, no booking).
  2. T-30 min: if free seats remain → broadcast to all non-booked users
     (one-time per activity, guarded by reminder_broadcast_sent).
  3. T-10 min: free-seat broadcast → for any activity still with free seats,
     offer to waitlist; if no waitlist, broadcast to all unbooked users.
  4. At booking_opens_at: one-time broadcast to all users about
     consultation booking opening + hardcoded PUBLIC TALK mention.
  5. Waitlist offer expiry: OFFERED past deadline → EXPIRED → next in queue.

Idempotency: reminder_sent flag on Booking;
broadcast_sent / opens_broadcast_sent / reminder_broadcast_sent flags on Activity.
"""

import html
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings
from db.base import async_session
from db.crud import bookings as bookings_crud
from db.crud import waitlist as waitlist_crud
from db.crud.activities import (
    activities_due_for_free_seat_broadcast,
    activities_due_for_opens_broadcast,
    activities_due_for_reminder_broadcast,
    get_activity_by_id,
    mark_broadcast_sent,
    mark_opens_broadcast_sent,
    mark_reminder_broadcast_sent,
)
from db.crud.bookings import user_ids_busy_during, user_ids_booked_in_group
from db.crud.users import all_user_tg_ids
from keyboards.booking import attendance_keyboard, waitlist_offer_keyboard
from services import booking_actions as actions
from texts import booking as t
from utils.time_utils import display_title, format_time, format_time_range

logger = logging.getLogger(__name__)

_TICK_SECONDS = 60


def _naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


async def _send(bot: Bot, tg_id: int, text: str, reply_markup=None) -> bool:
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
    now = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=settings.clock_offset_minutes)

    async with async_session() as session:
        just_reminded = await _process_reminders(session, bot, now)
        await _process_reminder_broadcast(session, bot, now)
        await _process_no_shows(session, bot, now, skip_ids=just_reminded)
        await _process_free_seat_broadcast(session, bot, now)
        await _process_opens_broadcast(session, bot, now)
        await _process_waitlist_expiry(session, bot, now)

    try:
        from services.sheets_service import sync_if_dirty
        await sync_if_dirty()
    except Exception:
        logger.exception("Google Sheets sync step failed")


# ---------------------------------------------------------------------------
# T-30: reminder with location to booked users
# ---------------------------------------------------------------------------

async def _process_reminders(session, bot: Bot, now: datetime) -> set[int]:
    threshold = now + timedelta(minutes=settings.reminder_minutes)
    due = await bookings_crud.bookings_due_for_reminder(session, now, threshold)

    just_reminded: set[int] = set()

    reminder_window = timedelta(minutes=settings.reminder_minutes)
    clock_offset = timedelta(minutes=settings.clock_offset_minutes)
    # Group by (user_id, start_time) so simultaneous activities → one message.
    # Skip bookings made after the reminder window opened (booked within T-30).
    by_user_start: dict[tuple, list] = defaultdict(list)
    for booking, activity in due:
        window_opened_at = _naive_utc(activity.start_time) - reminder_window
        # Apply clock offset so created_at is in virtual time, matching the activity's clock.
        virtual_created_at = _naive_utc(booking.created_at) + clock_offset
        if virtual_created_at >= window_opened_at:
            await bookings_crud.mark_reminder_sent(session, booking)
            continue
        by_user_start[(booking.user_id, activity.start_time)].append((booking, activity))

    for (user_pk, _), items in by_user_start.items():
        tg_id = await _user_tg_id(session, user_pk)
        if tg_id is None:
            continue

        if len(items) == 1:
            booking, activity = items[0]
            text = t.REMINDER.format(
                title=html.escape(display_title(activity)),
                time_range=format_time_range(activity.start_time, activity.end_time),
                location=html.escape(activity.location_text or ""),
            )
            keyboard = attendance_keyboard(booking.id)
        else:
            # Multiple activities at the same start time: one combined message, no keyboard.
            first_activity = items[0][1]
            header = t.REMINDER_MULTI_HEADER.format(
                time=format_time(first_activity.start_time)
            )
            entries = "".join(
                t.REMINDER_MULTI_ENTRY.format(
                    title=html.escape(display_title(a)),
                    location=html.escape(a.location_text or ""),
                )
                for _, a in items
            )
            text = header + entries + t.REMINDER_MULTI_FOOTER
            keyboard = None

        await _send(bot, tg_id, text, reply_markup=keyboard)
        for booking, _ in items:
            await bookings_crud.mark_reminder_sent(session, booking)
            await bookings_crud.mark_confirmation_requested(session, booking)
            just_reminded.add(booking.id)

    return just_reminded


# ---------------------------------------------------------------------------
# T-30: free-seat broadcast to non-booked users
# ---------------------------------------------------------------------------

async def _process_reminder_broadcast(session, bot: Bot, now: datetime) -> None:
    threshold = now + timedelta(minutes=settings.reminder_minutes)
    activities = await activities_due_for_reminder_broadcast(session, now, threshold)

    if not activities:
        return

    from sqlalchemy import select
    from db.models import User

    rows = (await session.execute(select(User.id, User.tg_id))).all()

    from db.crud.activities import get_booked_count
    for activity in activities:
        # Only broadcast if there are free seats; always mark sent so we don't retry.
        booked_count = await get_booked_count(session, activity.id)
        free = activity.capacity - booked_count
        await mark_reminder_broadcast_sent(session, activity)
        if free <= 0:
            continue

        excluded = await user_ids_busy_during(session, activity.start_time, activity.end_time)
        if activity.exclusive_group_id:
            excluded |= await user_ids_booked_in_group(session, activity.exclusive_group_id)

        text = t.REMINDER_FREE_SEATS.format(
            title=html.escape(display_title(activity)),
            time_range=format_time_range(activity.start_time, activity.end_time),
            location=html.escape(activity.location_text or ""),
        )

        for user_pk, tg_id in rows:
            if user_pk not in excluded:
                await _send(bot, tg_id, text)


# ---------------------------------------------------------------------------
# T-15: release unconfirmed bookings → NO_SHOW + promote waitlist
# ---------------------------------------------------------------------------

async def _process_no_shows(session, bot: Bot, now: datetime, skip_ids: set[int] = frozenset()) -> None:
    threshold = now + timedelta(minutes=settings.auto_release_minutes)
    due = await bookings_crud.bookings_due_for_release(session, now, threshold)

    for booking, activity in due:
        if booking.id in skip_ids:
            continue
        await bookings_crud.mark_no_show(session, booking)

        tg_id = await _user_tg_id(session, booking.user_id)
        if tg_id is not None:
            await _send(bot, tg_id, t.NO_SHOW_RELEASED.format(
                title=html.escape(display_title(activity))
            ))

        await _promote(session, bot, activity.id)


# ---------------------------------------------------------------------------
# T-10: free-seat broadcast
# ---------------------------------------------------------------------------

async def _process_free_seat_broadcast(session, bot: Bot, now: datetime) -> None:
    threshold = now + timedelta(minutes=settings.free_seat_broadcast_minutes)
    candidates = await activities_due_for_free_seat_broadcast(session, now, threshold)

    for activity, booked in candidates:
        # Try waitlist first; if someone is offered a seat, don't broadcast.
        offered = await _promote(session, bot, activity.id)
        await mark_broadcast_sent(session, activity)

        if offered:
            continue

        # No waitlist → still free seats → broadcast to all unbooked users.
        free = activity.capacity - booked
        if free <= 0:
            continue

        from sqlalchemy import select
        from db.models import User
        rows = (await session.execute(select(User.id, User.tg_id))).all()

        text = t.FREE_SEAT_BROADCAST.format(
            title=html.escape(display_title(activity)),
            time_range=format_time_range(activity.start_time, activity.end_time),
            location=html.escape(activity.location_text or ""),
        )

        excluded = await user_ids_busy_during(session, activity.start_time, activity.end_time)
        if activity.exclusive_group_id:
            excluded |= await user_ids_booked_in_group(session, activity.exclusive_group_id)
        for user_pk, tg_id in rows:
            if user_pk not in excluded:
                await _send(bot, tg_id, text)


# ---------------------------------------------------------------------------
# At booking_opens_at: "consultations open" broadcast
# ---------------------------------------------------------------------------

async def _process_opens_broadcast(session, bot: Bot, now: datetime) -> None:
    activities = await activities_due_for_opens_broadcast(session, now)

    if not activities:
        return

    # Send once per tick (multiple consultation slots share the same opens_at,
    # so deduplicate by opens_at value before sending).
    sent_opens_at: set = set()
    all_tg_ids = await all_user_tg_ids(session)

    for activity in activities:
        opens_key = activity.booking_opens_at
        if opens_key not in sent_opens_at:
            sent_opens_at.add(opens_key)
            for tg_id in all_tg_ids:
                await _send(bot, tg_id, t.OPENS_BROADCAST)
        await mark_opens_broadcast_sent(session, activity)


# ---------------------------------------------------------------------------
# Waitlist offer expiry
# ---------------------------------------------------------------------------

async def _process_waitlist_expiry(session, bot: Bot, now: datetime) -> None:
    for entry in await waitlist_crud.expired_offers(session, now):
        activity_id = entry.activity_id
        await waitlist_crud.mark_expired(session, entry)

        tg_id = await _user_tg_id(session, entry.user_id)
        if tg_id is not None:
            await _send(bot, tg_id, t.WAITLIST_OFFER_EXPIRED)

        await _promote(session, bot, activity_id)


# ---------------------------------------------------------------------------
# Shared: promote next waitlist entry and notify them
# ---------------------------------------------------------------------------

async def _promote(session, bot: Bot, activity_id: int) -> bool:
    """Offer the next person in the waitlist. Returns True if someone was offered."""
    entry = await actions.offer_next_in_waitlist(session, activity_id)
    if entry is None:
        return False

    activity = await get_activity_by_id(session, activity_id)
    tg_id = await _user_tg_id(session, entry.user_id)
    if activity is None or tg_id is None:
        return True  # entry was offered, just couldn't notify

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
    return True


# ---------------------------------------------------------------------------
# Scheduler setup
# ---------------------------------------------------------------------------

async def startup_flush() -> None:
    """
    Called once on bot startup. Silently marks all broadcast flags for
    activities already inside their notification windows, so the first
    real tick doesn't retroactively spam everyone.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=settings.clock_offset_minutes)

    from sqlalchemy import select, update
    from db.models import Activity

    async with async_session() as session:
        reminder_threshold = now + timedelta(minutes=settings.reminder_minutes)
        free_threshold = now + timedelta(minutes=settings.free_seat_broadcast_minutes)

        from db.models import Booking, BookingStatus
        # Mark reminder_sent on all bookings already in the T-30 window so they
        # don't get a confirmation request on the first tick after startup.
        await session.execute(
            update(Booking)
            .where(
                Booking.status == BookingStatus.CONFIRMED,
                Booking.reminder_sent.is_(False),
                Booking.activity_id.in_(
                    select(Activity.id).where(
                        Activity.start_time > now,
                        Activity.start_time <= reminder_threshold,
                    )
                ),
            )
            .values(reminder_sent=True)
        )
        # Mark reminder_broadcast_sent for anything already in the T-30 window.
        await session.execute(
            update(Activity)
            .where(
                Activity.start_time > now,
                Activity.start_time <= reminder_threshold,
                Activity.reminder_broadcast_sent.is_(False),
            )
            .values(reminder_broadcast_sent=True)
        )
        # Mark broadcast_sent for anything already in the T-10 window.
        await session.execute(
            update(Activity)
            .where(
                Activity.start_time > now,
                Activity.start_time <= free_threshold,
                Activity.broadcast_sent.is_(False),
            )
            .values(broadcast_sent=True)
        )
        # Mark opens_broadcast_sent for booking windows that have already opened.
        await session.execute(
            update(Activity)
            .where(
                Activity.booking_opens_at.isnot(None),
                Activity.booking_opens_at <= now,
                Activity.opens_broadcast_sent.is_(False),
            )
            .values(opens_broadcast_sent=True)
        )
        await session.commit()
    logger.info("Ticker startup flush complete (now=%s UTC)", now.strftime("%H:%M"))


def start_ticker(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(tick, "interval", seconds=_TICK_SECONDS, args=[bot], id="ticker", max_instances=1)
    scheduler.start()
    return scheduler
