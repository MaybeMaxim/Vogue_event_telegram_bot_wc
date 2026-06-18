"""
CRUD helpers for the admin panel: participant lists, search, attendance,
manual booking management, and data for exports.
"""

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Activity, Booking, BookingStatus, User, Waitlist, WaitlistStatus

# Statuses that mean the guest currently holds a place on an activity.
_PRESENT_STATUSES = (
    BookingStatus.CONFIRMED,
    BookingStatus.PENDING_CONFIRMATION,
    BookingStatus.ATTENDED,
)


async def all_activities(session: AsyncSession) -> list[Activity]:
    """Every activity, ordered by day then start time."""
    stmt = select(Activity).order_by(Activity.day, Activity.start_time, Activity.id)
    return list((await session.execute(stmt)).scalars().all())


async def regular_activities(session: AsyncSession) -> list[Activity]:
    """Non-consultation activities, ordered by day/time."""
    stmt = (
        select(Activity)
        .where(Activity.is_consultation_slot.is_(False))
        .order_by(Activity.day, Activity.start_time, Activity.id)
    )
    return list((await session.execute(stmt)).scalars().all())


async def consultation_activities(session: AsyncSession) -> list[Activity]:
    """Consultation slot activities, ordered by start time."""
    stmt = (
        select(Activity)
        .where(Activity.is_consultation_slot.is_(True))
        .order_by(Activity.start_time, Activity.id)
    )
    return list((await session.execute(stmt)).scalars().all())


async def consultation_participants(session: AsyncSession) -> list[tuple[Booking, User, Activity]]:
    """
    All booked consultation slots across the whole consultation window,
    each with guest + the specific slot activity, ordered by slot time.
    """
    stmt = (
        select(Booking, User, Activity)
        .join(User, Booking.user_id == User.id)
        .join(Activity, Booking.activity_id == Activity.id)
        .where(Activity.is_consultation_slot.is_(True), Booking.status.in_(_PRESENT_STATUSES))
        .order_by(Activity.start_time)
    )
    return [(b, u, a) for b, u, a in (await session.execute(stmt)).all()]


async def participants_for_activity(
    session: AsyncSession, activity_id: int
) -> list[tuple[Booking, User]]:
    """
    Active bookings for an activity, each with the guest, ordered by guest name.
    """
    stmt = (
        select(Booking, User)
        .join(User, Booking.user_id == User.id)
        .where(Booking.activity_id == activity_id, Booking.status.in_(_PRESENT_STATUSES))
        .order_by(User.full_name)
    )
    return [(b, u) for b, u in (await session.execute(stmt)).all()]


async def waitlist_for_activity(
    session: AsyncSession, activity_id: int
) -> list[tuple[Waitlist, User]]:
    """Waiting/offered waitlist entries for an activity, in FIFO order, with guests."""
    stmt = (
        select(Waitlist, User)
        .join(User, Waitlist.user_id == User.id)
        .where(
            Waitlist.activity_id == activity_id,
            Waitlist.status.in_((WaitlistStatus.WAITING, WaitlistStatus.OFFERED)),
        )
        .order_by(Waitlist.created_at)
    )
    return [(w, u) for w, u in (await session.execute(stmt)).all()]


async def search_guests(session: AsyncSession, query: str) -> list[User]:
    """
    Find guests by name or phone, more flexibly than a single LIKE:

    - Phone: digits are extracted from the query and matched against the
      digits of stored phones (so "098 492" or "+38 098" both work).
    - Name: the query is split into words; every word must appear somewhere
      in the full name (case-insensitive), so word order doesn't matter
      ("Іван Петренко" matches "Петренко Іван").
    """
    import re as _re

    raw = query.strip()
    if not raw:
        return []

    digits = _re.sub(r"\D", "", raw)

    conditions = []

    # Phone match: compare digit-only forms. SQLite lacks regexp_replace, so
    # strip the common separators with nested REPLACE.
    if len(digits) >= 3:
        phone_digits = func.replace(
            func.replace(
                func.replace(func.replace(func.replace(User.phone, "+", ""), " ", ""), "-", ""),
                "(", "",
            ),
            ")", "",
        )
        conditions.append(phone_digits.like(f"%{digits}%"))

    # Name match: each word must be a substring of the full name.
    words = [w for w in raw.split() if w]
    if words:
        name_cond = and_(*[User.full_name.ilike(f"%{w}%") for w in words])
        conditions.append(name_cond)

    if not conditions:
        conditions.append(User.full_name.ilike(f"%{raw}%"))

    stmt = (
        select(User)
        .where(or_(*conditions))
        .order_by(User.full_name)
        .limit(25)
    )
    return list((await session.execute(stmt)).scalars().all())


async def guest_bookings(session: AsyncSession, user_id: int) -> list[tuple[Booking, Activity]]:
    """A guest's active bookings with their activities, ordered by time."""
    stmt = (
        select(Booking, Activity)
        .join(Activity, Booking.activity_id == Activity.id)
        .where(Booking.user_id == user_id, Booking.status.in_(_PRESENT_STATUSES))
        .order_by(Activity.start_time)
    )
    return [(b, a) for b, a in (await session.execute(stmt)).all()]


async def set_attendance(session: AsyncSession, booking: Booking, attended: bool) -> None:
    """Mark a booking ATTENDED, or revert it to CONFIRMED."""
    booking.status = BookingStatus.ATTENDED if attended else BookingStatus.CONFIRMED
    await session.commit()


async def all_active_bookings(session: AsyncSession) -> list[tuple[Booking, User, Activity]]:
    """Every active booking with guest + activity — used for exports."""
    stmt = (
        select(Booking, User, Activity)
        .join(User, Booking.user_id == User.id)
        .join(Activity, Booking.activity_id == Activity.id)
        .where(Booking.status.in_(_PRESENT_STATUSES))
        .order_by(Activity.day, Activity.start_time, User.full_name)
    )
    return [(b, u, a) for b, u, a in (await session.execute(stmt)).all()]


async def all_guests(session: AsyncSession) -> list[User]:
    """Every registered guest, ordered by name — used for the contacts export."""
    stmt = select(User).order_by(User.full_name)
    return list((await session.execute(stmt)).scalars().all())
