"""
CRUD helpers for the Booking model.

Seat accounting: a booking "occupies a seat" for any status except
CANCELLED / NO_SHOW (see _OCCUPYING_STATUSES). Capacity checks and the
booking-vs-cancel race are guarded by a per-activity lock at the service
layer (services.booking_service) — these functions are the raw queries.
"""

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Activity, Booking, BookingStatus

_OCCUPYING_STATUSES = (
    BookingStatus.CONFIRMED,
    BookingStatus.PENDING_CONFIRMATION,
    BookingStatus.ATTENDED,
)

# Statuses that mean "the user currently holds this booking" — used to
# detect duplicate / conflicting bookings (waitlist is tracked separately).
_ACTIVE_STATUSES = _OCCUPYING_STATUSES


async def count_occupied_seats(session: AsyncSession, activity_id: int) -> int:
    """Number of seats currently held for an activity."""
    stmt = select(func.count(Booking.id)).where(
        Booking.activity_id == activity_id,
        Booking.status.in_(_OCCUPYING_STATUSES),
    )
    return int((await session.execute(stmt)).scalar_one())


async def get_active_booking(session: AsyncSession, user_id: int, activity_id: int) -> Booking | None:
    """Return the user's active booking for this activity, if any."""
    stmt = select(Booking).where(
        Booking.user_id == user_id,
        Booking.activity_id == activity_id,
        Booking.status.in_(_ACTIVE_STATUSES),
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def find_time_conflict(
    session: AsyncSession, user_id: int, start_time, end_time
) -> Booking | None:
    """
    Return one of the user's active bookings whose activity time range
    overlaps [start_time, end_time), or None.

    Overlap test: existing.start < new.end AND existing.end > new.start.
    This catches both same-slot alternatives (e.g. barre vs test-drive)
    and any other overlapping activity, satisfying the "no parallel
    activities" rule regardless of exclusive_group_id.
    """
    stmt = (
        select(Booking)
        .join(Activity, Booking.activity_id == Activity.id)
        .where(
            Booking.user_id == user_id,
            Booking.status.in_(_ACTIVE_STATUSES),
            and_(Activity.start_time < end_time, Activity.end_time > start_time),
        )
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def create_booking(session: AsyncSession, user_id: int, activity_id: int) -> Booking:
    """Create a CONFIRMED booking. Caller must have checked capacity under a lock."""
    booking = Booking(user_id=user_id, activity_id=activity_id, status=BookingStatus.CONFIRMED)
    session.add(booking)
    await session.commit()
    await session.refresh(booking)
    return booking


async def cancel_booking(session: AsyncSession, booking: Booking) -> None:
    """Mark a booking CANCELLED (frees its seat)."""
    booking.status = BookingStatus.CANCELLED
    await session.commit()


async def get_booking_by_id(session: AsyncSession, booking_id: int) -> Booking | None:
    """Fetch a booking by id."""
    return (await session.execute(select(Booking).where(Booking.id == booking_id))).scalar_one_or_none()


async def list_user_bookings(session: AsyncSession, user_id: int) -> list[tuple[Booking, Activity]]:
    """
    Return the user's active bookings paired with their activities,
    ordered by the activity start time.
    """
    stmt = (
        select(Booking, Activity)
        .join(Activity, Booking.activity_id == Activity.id)
        .where(Booking.user_id == user_id, Booking.status.in_(_ACTIVE_STATUSES))
        .order_by(Activity.start_time, Activity.id)
    )
    return [(b, a) for b, a in (await session.execute(stmt)).all()]


# --- Ticker query helpers --------------------------------------------------

async def bookings_due_for_reminder(session: AsyncSession, now, threshold) -> list[tuple[Booking, Activity]]:
    """
    CONFIRMED bookings for confirmation-EXEMPT activities whose start is
    within the reminder window and that haven't been reminded yet.

    (Activities that require confirmation get their location via the
    confirmation request instead, so they're excluded here to avoid
    double-messaging.)
    """
    stmt = (
        select(Booking, Activity)
        .join(Activity, Booking.activity_id == Activity.id)
        .where(
            Booking.status == BookingStatus.CONFIRMED,
            Booking.reminder_sent.is_(False),
            Activity.requires_confirmation.is_(False),
            Activity.start_time > now,
            Activity.start_time <= threshold,
        )
    )
    return [(b, a) for b, a in (await session.execute(stmt)).all()]


async def bookings_due_for_confirmation(session: AsyncSession, now, threshold) -> list[tuple[Booking, Activity]]:
    """
    CONFIRMED bookings for confirmation-REQUIRED activities whose start is
    within the confirmation window and that haven't been asked yet.
    """
    stmt = (
        select(Booking, Activity)
        .join(Activity, Booking.activity_id == Activity.id)
        .where(
            Booking.status == BookingStatus.CONFIRMED,
            Booking.confirmation_sent.is_(False),
            Activity.requires_confirmation.is_(True),
            Activity.start_time > now,
            Activity.start_time <= threshold,
        )
    )
    return [(b, a) for b, a in (await session.execute(stmt)).all()]


async def bookings_due_for_release(session: AsyncSession, threshold) -> list[tuple[Booking, Activity]]:
    """
    PENDING_CONFIRMATION bookings still unconfirmed whose start is within
    the auto-release window — these become no-shows and free their seats.
    """
    stmt = (
        select(Booking, Activity)
        .join(Activity, Booking.activity_id == Activity.id)
        .where(
            Booking.status == BookingStatus.PENDING_CONFIRMATION,
            Activity.start_time <= threshold,
        )
    )
    return [(b, a) for b, a in (await session.execute(stmt)).all()]


async def mark_reminder_sent(session: AsyncSession, booking: Booking) -> None:
    booking.reminder_sent = True
    await session.commit()


async def mark_confirmation_requested(session: AsyncSession, booking: Booking) -> None:
    """Move to PENDING_CONFIRMATION and flag both sent markers."""
    booking.status = BookingStatus.PENDING_CONFIRMATION
    booking.confirmation_sent = True
    booking.reminder_sent = True  # confirmation request doubles as the reminder
    await session.commit()


async def mark_attendance_confirmed(session: AsyncSession, booking: Booking) -> None:
    """User confirmed they'll attend -> back to CONFIRMED."""
    from datetime import datetime, timezone

    booking.status = BookingStatus.CONFIRMED
    booking.confirmed_at = datetime.now(timezone.utc)
    await session.commit()


async def mark_no_show(session: AsyncSession, booking: Booking) -> None:
    """Unconfirmed in time -> NO_SHOW (frees the seat)."""
    booking.status = BookingStatus.NO_SHOW
    await session.commit()
