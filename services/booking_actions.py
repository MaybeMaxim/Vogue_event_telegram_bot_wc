"""
Booking action logic: the side-effectful operations behind the booking
UI (create / cancel / join waitlist / promote from waitlist).

Concurrency: every operation that reads then changes an activity's seat
count holds that activity's lock (scheduler.locks.activity_lock) so the
"two people grab the last seat" race can't happen.

Each public function returns a small result object describing the
outcome, so the handler layer can pick the right user-facing message
without embedding business rules.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.crud import bookings as bookings_crud
from db.crud import waitlist as waitlist_crud
from db.crud.activities import get_activity_by_id
from db.models import Activity, Booking, Waitlist
from db.crud.bookings import find_consultation_booking, get_booking_in_exclusive_group
from db.crud.waitlist import find_consultation_waitlist_entry
from scheduler.locks import activity_lock


def _mark_sheets_dirty() -> None:
    """Flag the Google Sheets sync to refresh (no-op if Sheets disabled)."""
    try:
        from services.sheets_service import mark_dirty

        mark_dirty()
    except Exception:
        pass


# --- Result types ----------------------------------------------------------

@dataclass
class BookingResult:
    """Outcome of a create-booking attempt."""

    status: str  # one of the OUTCOME_* constants below
    booking: Booking | None = None
    conflict_booking: Booking | None = None
    conflict_activity: Activity | None = None
    # Set when a consultation-slot waitlist entry was auto-dropped on booking.
    dropped_waitlist_entry: Waitlist | None = None
    dropped_waitlist_activity: Activity | None = None
    # Set when a conflicting consultation booking was auto-cancelled on waitlist confirm.
    swapped_from_booking: Booking | None = None
    swapped_from_activity: Activity | None = None


OUTCOME_CONFIRMED = "confirmed"
OUTCOME_ALREADY_BOOKED = "already_booked"
OUTCOME_CONFLICT = "conflict"                          # time-overlapping booking exists
OUTCOME_EXCLUSIVE_GROUP_CONFLICT = "exclusive_group_conflict"  # same event, different sub-slot
OUTCOME_CONSULTATION_CONFLICT = "consultation_conflict"  # already booked a consultation slot
OUTCOME_FULL = "full"                                  # no seats; user may join the waitlist
OUTCOME_NOT_FOUND = "not_found"


@dataclass
class WaitlistJoinResult:
    status: str  # WL_* constants
    position: int | None = None
    # Set when the user is already booked for a conflicting activity;
    # shown as a warning so they know confirming the offer will cancel it.
    conflict_booking: Booking | None = None
    conflict_activity: Activity | None = None


WL_JOINED = "joined"
WL_ALREADY_WAITING = "already_waiting"
WL_ALREADY_BOOKED = "already_booked"
WL_SEAT_AVAILABLE = "seat_available"       # not full anymore -> should just book
WL_NOT_FOUND = "not_found"
WL_CONSULTATION_CONFLICT = "consultation_conflict"  # already waitlisted/booked for another consult slot


# --- Create booking ---------------------------------------------------------

async def try_create_booking(session: AsyncSession, user_id: int, activity_id: int) -> BookingResult:
    """
    Attempt to book a user onto an activity, running all checks in order:
      1. activity exists
      2. not already booked this exact activity
      3. no overlapping/exclusive active booking
      4. capacity available (checked + written under the activity lock)

    Returns a BookingResult describing the outcome.
    """
    activity = await get_activity_by_id(session, activity_id)
    if activity is None:
        return BookingResult(status=OUTCOME_NOT_FOUND)

    existing = await bookings_crud.get_active_booking(session, user_id, activity_id)
    if existing is not None:
        return BookingResult(status=OUTCOME_ALREADY_BOOKED, booking=existing)

    conflict = await bookings_crud.find_time_conflict(
        session, user_id, activity.start_time, activity.end_time
    )
    if conflict is not None:
        conflict_activity = await get_activity_by_id(session, conflict.activity_id)
        return BookingResult(
            status=OUTCOME_CONFLICT,
            conflict_booking=conflict,
            conflict_activity=conflict_activity,
        )

    # Exclusive groups (e.g. Kérastase sub-slots, test-drive sub-slots):
    # user can hold only one booking per group, even if slots don't overlap in time.
    if activity.exclusive_group_id is not None:
        group_conflict = await get_booking_in_exclusive_group(
            session, user_id, activity.exclusive_group_id, exclude_activity_id=activity_id
        )
        if group_conflict is not None:
            group_activity = await get_activity_by_id(session, group_conflict.activity_id)
            return BookingResult(
                status=OUTCOME_EXCLUSIVE_GROUP_CONFLICT,
                conflict_booking=group_conflict,
                conflict_activity=group_activity,
            )

    # Consultation slots are exclusive: one per user across all slots.
    if activity.is_consultation_slot:
        consult_conflict = await find_consultation_booking(
            session, user_id, exclude_activity_id=activity_id
        )
        if consult_conflict is not None:
            consult_activity = await get_activity_by_id(session, consult_conflict.activity_id)
            return BookingResult(
                status=OUTCOME_CONSULTATION_CONFLICT,
                conflict_booking=consult_conflict,
                conflict_activity=consult_activity,
            )

    # Detect any consultation waitlist entry to drop, but don't expire it yet —
    # we wait until we know the booking will actually succeed (inside the lock).
    dropped_wl = None
    dropped_wl_activity = None
    if activity.is_consultation_slot:
        dropped_wl = await find_consultation_waitlist_entry(
            session, user_id, exclude_activity_id=activity_id
        )
        if dropped_wl is not None:
            dropped_wl_activity = await get_activity_by_id(session, dropped_wl.activity_id)

    async with activity_lock(activity_id):
        occupied = await bookings_crud.count_occupied_seats(session, activity_id)
        if occupied >= activity.capacity:
            return BookingResult(status=OUTCOME_FULL)

        # Seat is confirmed available — now safe to drop the other waitlist spot.
        if dropped_wl is not None:
            await waitlist_crud.mark_expired(session, dropped_wl)

        booking = await bookings_crud.create_booking(session, user_id, activity_id)

    _mark_sheets_dirty()
    return BookingResult(
        status=OUTCOME_CONFIRMED,
        booking=booking,
        dropped_waitlist_entry=dropped_wl,
        dropped_waitlist_activity=dropped_wl_activity,
    )


# --- Cancel booking ---------------------------------------------------------

async def cancel_booking(session: AsyncSession, booking: Booking) -> Activity | None:
    """
    Cancel a booking (frees its seat) under the activity lock, then return
    the activity so the caller can trigger waitlist promotion. Returns the
    Activity, or None if it no longer exists.
    """
    activity_id = booking.activity_id

    async with activity_lock(activity_id):
        await bookings_crud.cancel_booking(session, booking)

    _mark_sheets_dirty()
    return await get_activity_by_id(session, activity_id)


# --- Waitlist join ----------------------------------------------------------

async def try_join_waitlist(session: AsyncSession, user_id: int, activity_id: int) -> WaitlistJoinResult:
    """
    Attempt to add a user to an activity's waitlist.

    Guards: already booked, already waiting, or a seat is actually free
    (in which case the caller should just book instead of waitlisting).
    """
    activity = await get_activity_by_id(session, activity_id)
    if activity is None:
        return WaitlistJoinResult(status=WL_NOT_FOUND)

    if await bookings_crud.get_active_booking(session, user_id, activity_id) is not None:
        return WaitlistJoinResult(status=WL_ALREADY_BOOKED)

    if await waitlist_crud.get_waitlist_entry(session, user_id, activity_id) is not None:
        return WaitlistJoinResult(status=WL_ALREADY_WAITING)

    # Consultation slots: block joining the waitlist if already waitlisted for a
    # different consultation slot (can't queue for two at once). Being *booked*
    # for another slot is allowed — the existing booking will be auto-cancelled
    # when the offer is accepted.
    if activity.is_consultation_slot:
        if await find_consultation_waitlist_entry(session, user_id, exclude_activity_id=activity_id) is not None:
            return WaitlistJoinResult(status=WL_CONSULTATION_CONFLICT)

    # Detect any conflicting active booking (time overlap or consultation slot)
    # so we can warn the user up front that it will be cancelled on offer accept.
    conflict_bk = None
    conflict_act = None
    if activity.is_consultation_slot:
        conflict_bk = await find_consultation_booking(session, user_id, exclude_activity_id=activity_id)
    else:
        conflict_bk = await bookings_crud.find_time_conflict(
            session, user_id, activity.start_time, activity.end_time
        )
    if conflict_bk is not None:
        conflict_act = await get_activity_by_id(session, conflict_bk.activity_id)

    async with activity_lock(activity_id):
        occupied = await bookings_crud.count_occupied_seats(session, activity_id)
        if occupied < activity.capacity:
            return WaitlistJoinResult(status=WL_SEAT_AVAILABLE)

        entry = await waitlist_crud.add_to_waitlist(session, user_id, activity_id)

    position = await waitlist_crud.waitlist_position(session, entry)
    _mark_sheets_dirty()
    return WaitlistJoinResult(
        status=WL_JOINED,
        position=position,
        conflict_booking=conflict_bk,
        conflict_activity=conflict_act,
    )


# --- Waitlist promotion (called after a seat frees up) ----------------------

async def offer_next_in_waitlist(session: AsyncSession, activity_id: int) -> Waitlist | None:
    """
    If a seat is free and someone is WAITING, mark the head of the queue
    OFFERED with a confirmation deadline and return that entry (so the
    caller can notify them). Returns None if no seat is free or the queue
    is empty.

    Held under the activity lock so a freed seat is offered to exactly one
    person.
    """
    async with activity_lock(activity_id):
        activity = await get_activity_by_id(session, activity_id)
        if activity is None:
            return None

        occupied = await bookings_crud.count_occupied_seats(session, activity_id)
        if occupied >= activity.capacity:
            return None

        entry = await waitlist_crud.next_waiting(session, activity_id)
        if entry is None:
            return None

        # Store as naive UTC to match how activity times and the ticker's
        # `now` are represented (SQLite has no real tz-aware type).
        expires_at = (
            datetime.now(timezone.utc)
            + timedelta(minutes=settings.clock_offset_minutes)
            + timedelta(minutes=settings.waitlist_confirm_minutes)
        ).replace(tzinfo=None)
        await waitlist_crud.mark_offered(session, entry, expires_at)
        return entry


async def confirm_waitlist_offer(session: AsyncSession, entry: Waitlist) -> BookingResult:
    """
    Convert an OFFERED waitlist entry into a real CONFIRMED booking, under
    the activity lock (re-checking capacity in case it changed).
    """
    activity = await get_activity_by_id(session, entry.activity_id)
    if activity is None:
        return BookingResult(status=OUTCOME_NOT_FOUND)

    swapped_booking = None
    swapped_activity = None

    async with activity_lock(entry.activity_id):
        occupied = await bookings_crud.count_occupied_seats(session, entry.activity_id)
        if occupied >= activity.capacity:
            # Seat vanished again (shouldn't normally happen since the
            # offer reserved intent, but stay safe).
            return BookingResult(status=OUTCOME_FULL)

        # Auto-cancel any conflicting active booking so the user doesn't end up
        # double-booked. For consultation slots check by slot type; for all other
        # activities check by time overlap.
        if activity.is_consultation_slot:
            existing_conflict = await find_consultation_booking(
                session, entry.user_id, exclude_activity_id=entry.activity_id
            )
        else:
            existing_conflict = await bookings_crud.find_time_conflict(
                session, entry.user_id, activity.start_time, activity.end_time
            )
        if existing_conflict is not None:
            swapped_activity = await get_activity_by_id(session, existing_conflict.activity_id)
            swapped_booking = existing_conflict
            await bookings_crud.cancel_booking(session, existing_conflict)

        booking = await bookings_crud.create_booking(session, entry.user_id, entry.activity_id)
        await waitlist_crud.mark_confirmed(session, entry)

    _mark_sheets_dirty()
    return BookingResult(
        status=OUTCOME_CONFIRMED,
        booking=booking,
        swapped_from_booking=swapped_booking,
        swapped_from_activity=swapped_activity,
    )
