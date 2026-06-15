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
from scheduler.locks import activity_lock


# --- Result types ----------------------------------------------------------

@dataclass
class BookingResult:
    """Outcome of a create-booking attempt."""

    status: str  # one of the OUTCOME_* constants below
    booking: Booking | None = None
    conflict_booking: Booking | None = None
    conflict_activity: Activity | None = None


OUTCOME_CONFIRMED = "confirmed"
OUTCOME_ALREADY_BOOKED = "already_booked"
OUTCOME_CONFLICT = "conflict"          # overlapping/exclusive booking exists
OUTCOME_FULL = "full"                  # no seats; user may join the waitlist
OUTCOME_NOT_FOUND = "not_found"


@dataclass
class WaitlistJoinResult:
    status: str  # WL_* constants
    position: int | None = None


WL_JOINED = "joined"
WL_ALREADY_WAITING = "already_waiting"
WL_ALREADY_BOOKED = "already_booked"
WL_SEAT_AVAILABLE = "seat_available"   # not full anymore -> should just book
WL_NOT_FOUND = "not_found"


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

    async with activity_lock(activity_id):
        occupied = await bookings_crud.count_occupied_seats(session, activity_id)
        if occupied >= activity.capacity:
            return BookingResult(status=OUTCOME_FULL)

        booking = await bookings_crud.create_booking(session, user_id, activity_id)

    return BookingResult(status=OUTCOME_CONFIRMED, booking=booking)


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

    async with activity_lock(activity_id):
        occupied = await bookings_crud.count_occupied_seats(session, activity_id)
        if occupied < activity.capacity:
            return WaitlistJoinResult(status=WL_SEAT_AVAILABLE)

        entry = await waitlist_crud.add_to_waitlist(session, user_id, activity_id)

    position = await waitlist_crud.waitlist_position(session, entry)
    return WaitlistJoinResult(status=WL_JOINED, position=position)


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
            datetime.now(timezone.utc) + timedelta(minutes=settings.waitlist_confirm_minutes)
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

    async with activity_lock(entry.activity_id):
        occupied = await bookings_crud.count_occupied_seats(session, entry.activity_id)
        if occupied >= activity.capacity:
            # Seat vanished again (shouldn't normally happen since the
            # offer reserved intent, but stay safe).
            return BookingResult(status=OUTCOME_FULL)

        booking = await bookings_crud.create_booking(session, entry.user_id, entry.activity_id)
        await waitlist_crud.mark_confirmed(session, entry)

    return BookingResult(status=OUTCOME_CONFIRMED, booking=booking)
