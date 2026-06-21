"""
Handler for the "✍️ Записатись" booking flow.

Navigation:
  "✍️ Записатись"             -> day picker
  bookday:{day}                -> category picker for that day
  bookcat:{day}:{anchor_id}    -> sub-slot picker for a category
  bookconsult:{day}            -> consultation sub-slot picker
  bookact:{activity_id}        -> show booking confirmation card
  bookconfirm:{activity_id}    -> run checks + create booking
  bookwait:{activity_id}       -> show "join waitlist?" offer
  bookwaitjoin:{activity_id}   -> actually join the waitlist
  bookcancel:{booking_id}      -> cancel a conflicting booking
  bookeditdata                 -> jump to profile editing
  bookabort                    -> dismiss the current prompt
  bookdays                     -> back to day picker
  wlconfirm:{entry_id} / wldecline:{entry_id} -> respond to a waitlist offer

Booking actions live in services.booking_actions.
"""

import html
import logging
from datetime import timedelta

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.crud.activities import (
    get_activities_for_day,
    get_activity_by_id,
    get_consultation_slots,
)
from db.crud.bookings import get_booking_by_id
from db.crud.users import get_user_by_tg_id
from db.crud.waitlist import get_waitlist_entry
from db.models import Waitlist
from keyboards.booking import (
    back_only_keyboard,
    booked_ok_keyboard,
    category_picker_keyboard,
    conflict_cancelled_keyboard,
    confirm_booking_keyboard,
    conflict_keyboard,
    consultation_picker_keyboard,
    day_label,
    day_picker_keyboard,
    full_offer_waitlist_keyboard,
    subslot_picker_keyboard,
    waitlist_offer_keyboard,
)
from keyboards.main_menu import MENU_BOOK
from services import booking_actions as actions
from services.booking_service import (
    CategoryGroup,
    _category_name,
    group_into_categories,
    render_category_picker,
    render_subslot_picker,
)
from texts import booking as t
from utils.time_utils import display_title, format_time_range

router = Router(name="booking")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Navigation: day -> slot -> activity
# ---------------------------------------------------------------------------

@router.message(F.text == MENU_BOOK)
async def show_day_picker(message: Message) -> None:
    await message.answer(t.BOOK_INTRO, reply_markup=day_picker_keyboard())


@router.callback_query(F.data == "bookdays")
async def back_to_day_picker(callback: CallbackQuery) -> None:
    await callback.message.edit_text(t.BOOK_INTRO, reply_markup=day_picker_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("bookday:"))
async def show_category_picker(callback: CallbackQuery, session: AsyncSession) -> None:
    day = int(callback.data.split(":")[1])

    activities = await get_activities_for_day(session, day)
    if not activities:
        await callback.message.edit_text(t.NO_ACTIVITIES_FOR_DAY, reply_markup=day_picker_keyboard())
        await callback.answer()
        return

    categories = group_into_categories(activities)
    text = render_category_picker(day, day_label(day))
    await callback.message.edit_text(text, reply_markup=category_picker_keyboard(day, categories))
    await callback.answer()


@router.callback_query(F.data.startswith("bookcat:"))
async def show_subslot_picker(callback: CallbackQuery, session: AsyncSession) -> None:
    _, day_str, anchor_id_str = callback.data.split(":")
    day, anchor_id = int(day_str), int(anchor_id_str)

    anchor = await get_activity_by_id(session, anchor_id)
    if anchor is None:
        await callback.answer(t.NO_ACTIVITIES_FOR_DAY, show_alert=True)
        return

    # Find all activities for the day that share this category name.
    cat_name = _category_name(anchor.title)
    all_day = await get_activities_for_day(session, day)
    cat_activities = [
        (a, b) for a, b in all_day
        if not a.is_consultation_slot and _category_name(a.title) == cat_name
    ]

    if not cat_activities:
        await callback.answer(t.NO_ACTIVITIES_FOR_DAY, show_alert=True)
        return

    cat = CategoryGroup(name=cat_name, activities=cat_activities)
    text = render_subslot_picker(cat)
    await callback.message.edit_text(text, reply_markup=subslot_picker_keyboard(day, cat))
    await callback.answer()


@router.callback_query(F.data.startswith("bookconsult:"))
async def show_consultation_picker(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show the individual 15-min consultation slots."""
    day = int(callback.data.split(":")[1])

    slots = await get_consultation_slots(session, day)
    if not slots:
        await callback.answer(t.NO_ACTIVITIES_FOR_DAY, show_alert=True)
        return

    any_free = any(a.capacity - booked > 0 for a, booked in slots)
    first_a, last_a = slots[0][0], slots[-1][0]
    time_range = format_time_range(first_a.start_time, last_a.end_time)

    if any_free:
        text = t.CONSULTATION_PICKER_HEADER
    else:
        text = t.CONSULTATION_NONE_FREE

    await callback.message.edit_text(text, reply_markup=consultation_picker_keyboard(day, slots))
    await callback.answer()


# ---------------------------------------------------------------------------
# Booking confirmation card
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("bookact:"))
async def show_confirm_card(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show the confirmation card with the user's saved details."""
    activity_id = int(callback.data.split(":")[1])

    activity = await get_activity_by_id(session, activity_id)
    user = await get_user_by_tg_id(session, callback.from_user.id)
    if activity is None or user is None:
        await callback.answer(t.BOOKING_NOT_FOUND, show_alert=True)
        return

    text = t.CONFIRM_BOOKING.format(
        title=html.escape(display_title(activity)),
        time_range=format_time_range(activity.start_time, activity.end_time),
        full_name=html.escape(user.full_name),
        phone=html.escape(user.phone),
    )
    await callback.message.edit_text(
        text, reply_markup=confirm_booking_keyboard(activity_id, _back_cb(activity))
    )
    await callback.answer()


def _back_cb(activity) -> str:
    """Back callback from the confirm card: consultation picker or sub-slot picker."""
    if activity.is_consultation_slot:
        return f"bookconsult:{activity.day}"
    return f"bookcat:{activity.day}:{activity.id}"


@router.callback_query(F.data == "bookabort")
async def abort_booking(callback: CallbackQuery) -> None:
    await callback.message.edit_text(t.BOOKING_ABORTED)
    await callback.answer()


@router.callback_query(F.data == "bookeditdata")
async def edit_data_from_booking(callback: CallbackQuery, session: AsyncSession) -> None:
    """Shortcut to the profile card so the user can fix their details, then come back to book."""
    from handlers.profile import _show_profile

    await callback.message.edit_text(t.EDIT_DATA_PROMPT)
    await _show_profile(callback.message, session, callback.from_user.id)
    await callback.answer()


# ---------------------------------------------------------------------------
# Create booking
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("bookconfirm:"))
async def confirm_booking(callback: CallbackQuery, session: AsyncSession) -> None:
    """Run all checks and create the booking, rendering the appropriate outcome."""
    from datetime import datetime, timezone

    activity_id = int(callback.data.split(":")[1])
    user = await get_user_by_tg_id(session, callback.from_user.id)
    if user is None:
        await callback.answer(t.BOOKING_NOT_FOUND, show_alert=True)
        return

    # Check booking window before running business logic.
    activity_pre = await get_activity_by_id(session, activity_id)
    if activity_pre is not None:
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=settings.clock_offset_minutes)

        if activity_pre.start_time <= now_utc:
            await callback.message.edit_text(
                t.EVENT_ALREADY_STARTED,
                reply_markup=back_only_keyboard(_back_cb(activity_pre)),
            )
            await callback.answer()
            return

        if activity_pre.booking_opens_at is not None and now_utc < activity_pre.booking_opens_at:
            from zoneinfo import ZoneInfo
            opens_local = activity_pre.booking_opens_at.replace(
                tzinfo=timezone.utc
            ).astimezone(ZoneInfo(settings.event_timezone))
            await callback.message.edit_text(
                t.BOOKING_NOT_OPEN_YET.format(opens_at=opens_local.strftime("%H:%M")),
                reply_markup=back_only_keyboard(_back_cb(activity_pre)),
            )
            await callback.answer()
            return

    result = await actions.try_create_booking(session, user.id, activity_id)
    activity = await get_activity_by_id(session, activity_id)
    back_cb = _back_cb(activity) if activity else "bookdays"

    if result.status == actions.OUTCOME_CONFIRMED:
        if result.dropped_waitlist_entry is not None:
            dropped_act = result.dropped_waitlist_activity
            await callback.message.edit_text(
                t.BOOKED_OK_WAITLIST_DROPPED.format(
                    title=html.escape(display_title(activity)),
                    time_range=format_time_range(activity.start_time, activity.end_time),
                    dropped_title=html.escape(display_title(dropped_act)) if dropped_act else "?",
                ),
                reply_markup=booked_ok_keyboard(activity.day, f"bookday:{activity.day}"),
            )
        else:
            await callback.message.edit_text(
                t.BOOKED_OK.format(
                    title=html.escape(display_title(activity)),
                    time_range=format_time_range(activity.start_time, activity.end_time),
                ),
                reply_markup=booked_ok_keyboard(activity.day, f"bookday:{activity.day}"),
            )
    elif result.status == actions.OUTCOME_ALREADY_BOOKED:
        await callback.message.edit_text(
            t.ALREADY_BOOKED.format(title=html.escape(display_title(activity))),
            reply_markup=booked_ok_keyboard(activity.day, f"bookday:{activity.day}"),
        )
    elif result.status == actions.OUTCOME_CONFLICT:
        ca = result.conflict_activity
        if ca is None:
            await callback.message.edit_text(t.BOOKING_NOT_FOUND)
        else:
            await callback.message.edit_text(
                t.CONFLICT_FOUND.format(
                    conflict_title=html.escape(display_title(ca)),
                    conflict_time=format_time_range(ca.start_time, ca.end_time),
                ),
                reply_markup=conflict_keyboard(result.conflict_booking.id, display_title(ca), back_cb, activity_id),
            )
    elif result.status == actions.OUTCOME_EXCLUSIVE_GROUP_CONFLICT:
        ca = result.conflict_activity
        if ca is None:
            await callback.message.edit_text(t.BOOKING_NOT_FOUND)
        else:
            await callback.message.edit_text(
                t.EXCLUSIVE_GROUP_CONFLICT_FOUND.format(
                    conflict_title=html.escape(display_title(ca)),
                    conflict_time=format_time_range(ca.start_time, ca.end_time),
                ),
                reply_markup=conflict_keyboard(result.conflict_booking.id, display_title(ca), back_cb, activity_id),
            )
    elif result.status == actions.OUTCOME_CONSULTATION_CONFLICT:
        ca = result.conflict_activity
        if ca is None:
            await callback.message.edit_text(t.BOOKING_NOT_FOUND)
        else:
            await callback.message.edit_text(
                t.CONSULTATION_CONFLICT_FOUND.format(
                    conflict_title=html.escape(display_title(ca)),
                ),
                reply_markup=conflict_keyboard(result.conflict_booking.id, display_title(ca), back_cb, activity_id),
            )
    elif result.status == actions.OUTCOME_FULL:
        await callback.message.edit_text(
            t.ACTIVITY_FULL_OFFER_WAITLIST.format(title=html.escape(display_title(activity))),
            reply_markup=full_offer_waitlist_keyboard(activity_id, back_cb),
        )
    else:
        await callback.message.edit_text(t.BOOKING_NOT_FOUND)

    await callback.answer()


@router.callback_query(F.data.startswith("bookcancel:"))
async def cancel_conflicting(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    """Cancel a conflicting booking the user chose to drop, then promote any waitlist."""
    parts = callback.data.split(":")
    booking_id = int(parts[1])
    target_activity_id = int(parts[2]) if len(parts) > 2 else None

    booking = await get_booking_by_id(session, booking_id)
    if booking is None:
        await callback.answer(t.BOOKING_NOT_FOUND, show_alert=True)
        return

    activity = await actions.cancel_booking(session, booking)

    if target_activity_id is not None:
        await callback.message.edit_text(
            t.CONFLICT_CANCELLED,
            reply_markup=conflict_cancelled_keyboard(target_activity_id),
        )
    else:
        await callback.message.edit_text(t.CONFLICT_CANCELLED)
    await callback.answer()

    if activity is not None:
        await _promote_waitlist(session, bot, activity.id)


# ---------------------------------------------------------------------------
# Waitlist join
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("bookwait:"))
async def offer_waitlist(callback: CallbackQuery, session: AsyncSession) -> None:
    """A full activity's button was tapped: offer to join the waitlist."""
    activity_id = int(callback.data.split(":")[1])
    activity = await get_activity_by_id(session, activity_id)
    if activity is None:
        await callback.answer(t.BOOKING_NOT_FOUND, show_alert=True)
        return

    await callback.message.edit_text(
        t.ACTIVITY_FULL_OFFER_WAITLIST.format(title=html.escape(display_title(activity))),
        reply_markup=full_offer_waitlist_keyboard(activity_id, _back_cb(activity)),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bookwaitjoin:"))
async def join_waitlist(callback: CallbackQuery, session: AsyncSession) -> None:
    from datetime import datetime, timezone
    activity_id = int(callback.data.split(":")[1])
    user = await get_user_by_tg_id(session, callback.from_user.id)
    activity = await get_activity_by_id(session, activity_id)
    if user is None or activity is None:
        await callback.answer(t.BOOKING_NOT_FOUND, show_alert=True)
        return

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=settings.clock_offset_minutes)
    if activity.start_time <= now_utc:
        await callback.answer(t.EVENT_ALREADY_STARTED, show_alert=True)
        return

    result = await actions.try_join_waitlist(session, user.id, activity_id)
    title = html.escape(display_title(activity))
    back_kb = booked_ok_keyboard(activity.day, f"bookday:{activity.day}")

    if result.status == actions.WL_JOINED:
        if result.conflict_activity is not None:
            await callback.message.edit_text(
                t.WAITLIST_JOINED_WITH_CONFLICT.format(
                    title=title,
                    position=result.position,
                    conflict_title=html.escape(display_title(result.conflict_activity)),
                ),
                reply_markup=back_kb,
            )
        else:
            await callback.message.edit_text(
                t.WAITLIST_JOINED.format(title=title, position=result.position),
                reply_markup=back_kb,
            )
    elif result.status == actions.WL_ALREADY_WAITING:
        await callback.message.edit_text(t.WAITLIST_ALREADY.format(title=title), reply_markup=back_kb)
    elif result.status == actions.WL_ALREADY_BOOKED:
        await callback.message.edit_text(t.ALREADY_BOOKED.format(title=title), reply_markup=back_kb)
    elif result.status == actions.WL_SEAT_AVAILABLE:
        await callback.message.edit_text(t.WAITLIST_SEAT_AVAILABLE, reply_markup=back_kb)
    elif result.status == actions.WL_CONSULTATION_CONFLICT:
        await callback.message.edit_text(t.WAITLIST_CONSULTATION_CONFLICT, reply_markup=back_kb)
    else:
        await callback.message.edit_text(t.BOOKING_NOT_FOUND)

    await callback.answer()


# ---------------------------------------------------------------------------
# Waitlist offer responses (confirm / decline)
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("wlconfirm:"))
async def waitlist_confirm(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    entry_id = int(callback.data.split(":")[1])
    entry = await _get_offered_entry(session, entry_id)
    if entry is None:
        await callback.message.edit_text(t.WAITLIST_OFFER_EXPIRED)
        await callback.answer()
        return

    activity = await get_activity_by_id(session, entry.activity_id)
    result = await actions.confirm_waitlist_offer(session, entry)

    if result.status == actions.OUTCOME_CONFIRMED:
        if result.swapped_from_activity is not None:
            await callback.message.edit_text(
                t.WAITLIST_OFFER_CONFIRMED_SWAPPED.format(
                    title=html.escape(display_title(activity)),
                    time_range=format_time_range(activity.start_time, activity.end_time),
                    swapped_title=html.escape(display_title(result.swapped_from_activity)),
                )
            )
            # The auto-cancelled booking freed a seat on the other activity —
            # promote its waitlist so that seat doesn't go to waste.
            if result.swapped_from_booking is not None:
                await _promote_waitlist(session, bot, result.swapped_from_booking.activity_id)
        else:
            await callback.message.edit_text(
                t.WAITLIST_OFFER_CONFIRMED.format(title=html.escape(display_title(activity)))
            )
    else:
        await callback.message.edit_text(t.WAITLIST_OFFER_TAKEN)
    await callback.answer()


@router.callback_query(F.data.startswith("wldecline:"))
async def waitlist_decline(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    from db.crud.waitlist import mark_expired

    entry_id = int(callback.data.split(":")[1])
    entry = await _get_offered_entry(session, entry_id)
    if entry is None:
        await callback.answer()
        return

    activity_id = entry.activity_id
    await mark_expired(session, entry)
    await callback.message.edit_text(t.WAITLIST_OFFER_DECLINED)
    await callback.answer()

    # The declined offer freed the intent; offer the seat to the next person.
    await _promote_waitlist(session, bot, activity_id)


# ---------------------------------------------------------------------------
# Attendance confirmation (responses to the 30-min ticker request)
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("attyes:"))
async def attendance_confirm(callback: CallbackQuery, session: AsyncSession) -> None:
    """User confirmed they'll attend -> booking back to CONFIRMED."""
    from db.crud.bookings import mark_attendance_confirmed
    from db.models import BookingStatus

    booking_id = int(callback.data.split(":")[1])
    booking = await get_booking_by_id(session, booking_id)

    if booking is None or booking.status != BookingStatus.PENDING_CONFIRMATION:
        await callback.message.edit_text(t.ATTENDANCE_EXPIRED)
        await callback.answer()
        return

    await mark_attendance_confirmed(session, booking)
    await callback.message.edit_text(t.ATTENDANCE_CONFIRMED)
    await callback.answer()


@router.callback_query(F.data.startswith("attno:"))
async def attendance_decline(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    """User can't make it -> release the seat now and promote the waitlist."""
    from db.models import BookingStatus

    booking_id = int(callback.data.split(":")[1])
    booking = await get_booking_by_id(session, booking_id)

    if booking is None or booking.status not in (
        BookingStatus.PENDING_CONFIRMATION,
        BookingStatus.CONFIRMED,
    ):
        await callback.message.edit_text(t.ATTENDANCE_EXPIRED)
        await callback.answer()
        return

    freed_activity = await actions.cancel_booking(session, booking)
    await callback.message.edit_text(t.ATTENDANCE_DECLINED)
    await callback.answer()

    if freed_activity is not None:
        await _promote_waitlist(session, bot, freed_activity.id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_offered_entry(session: AsyncSession, entry_id: int) -> Waitlist | None:
    """Fetch a waitlist entry by id only if it's still in OFFERED state."""
    from sqlalchemy import select
    from db.models import WaitlistStatus

    entry = (
        await session.execute(select(Waitlist).where(Waitlist.id == entry_id))
    ).scalar_one_or_none()
    if entry is None or entry.status != WaitlistStatus.OFFERED:
        return None
    return entry


async def _promote_waitlist(session: AsyncSession, bot: Bot, activity_id: int) -> None:
    """
    Offer a just-freed seat to the next waiting user (if any) and notify them.
    If they already hold a conflicting booking the offer message warns them
    upfront that accepting will cancel it.
    """
    from db.crud.bookings import find_consultation_booking, find_time_conflict

    entry = await actions.offer_next_in_waitlist(session, activity_id)
    if entry is None:
        return

    activity = await get_activity_by_id(session, activity_id)
    user = await _get_user_by_pk(session, entry.user_id)
    if activity is None or user is None:
        return

    # Check whether the user currently has a conflicting booking so we can
    # warn them in the offer message before they confirm.
    if activity.is_consultation_slot:
        conflict_bk = await find_consultation_booking(session, entry.user_id, exclude_activity_id=activity_id)
    else:
        conflict_bk = await find_time_conflict(session, entry.user_id, activity.start_time, activity.end_time)

    conflict_warning = ""
    if conflict_bk is not None:
        conflict_act = await get_activity_by_id(session, conflict_bk.activity_id)
        if conflict_act is not None:
            conflict_warning = t.WAITLIST_OFFER_CONFLICT_WARNING.format(
                conflict_title=html.escape(display_title(conflict_act)),
                conflict_time=format_time_range(conflict_act.start_time, conflict_act.end_time),
            )

    try:
        await bot.send_message(
            user.tg_id,
            t.WAITLIST_OFFER.format(
                title=html.escape(display_title(activity)),
                time_range=format_time_range(activity.start_time, activity.end_time),
                minutes=settings.waitlist_confirm_minutes,
            ) + conflict_warning,
            reply_markup=waitlist_offer_keyboard(entry.id),
        )
    except Exception:
        logger.exception("Failed to notify waitlist user %s for activity %s", user.tg_id, activity_id)


async def _get_user_by_pk(session: AsyncSession, user_pk: int):
    """Fetch a User by primary key (waitlist/booking store user_id as the PK)."""
    from sqlalchemy import select
    from db.models import User

    return (await session.execute(select(User).where(User.id == user_pk))).scalar_one_or_none()
