"""
CRUD helpers for the Activity model.

`get_activities_for_day` returns activities together with their current
"occupied seats" count — i.e. bookings that still hold a seat. A seat is
considered occupied for any status except CANCELLED/NO_SHOW, since
PENDING_CONFIRMATION and ATTENDED bookings still represent a held spot.
"""

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Activity, Booking, BookingStatus

# Statuses that still occupy a seat.
_OCCUPYING_STATUSES = (
    BookingStatus.CONFIRMED,
    BookingStatus.PENDING_CONFIRMATION,
    BookingStatus.ATTENDED,
)


async def get_activities_for_day(session: AsyncSession, day: int) -> list[tuple[Activity, int]]:
    """
    Return all activities for the given day (1 or 2), ordered by start
    time, each paired with its current occupied-seat count.
    """
    booked_subquery = (
        select(
            Booking.activity_id.label("activity_id"),
            func.count(Booking.id).label("booked"),
        )
        .where(Booking.status.in_(_OCCUPYING_STATUSES))
        .group_by(Booking.activity_id)
        .subquery()
    )

    stmt = (
        select(Activity, func.coalesce(booked_subquery.c.booked, 0))
        .outerjoin(booked_subquery, booked_subquery.c.activity_id == Activity.id)
        .where(Activity.day == day)
        .order_by(Activity.start_time, Activity.id)
    )

    result = await session.execute(stmt)
    return [(activity, int(booked)) for activity, booked in result.all()]


async def get_activity_by_id(session: AsyncSession, activity_id: int) -> Activity | None:
    """Return a single activity by id, or None."""
    result = await session.execute(select(Activity).where(Activity.id == activity_id))
    return result.scalar_one_or_none()


async def get_booked_count(session: AsyncSession, activity_id: int) -> int:
    """Return the current number of occupied seats for a single activity."""
    stmt = select(func.count(Booking.id)).where(
        Booking.activity_id == activity_id,
        Booking.status.in_(_OCCUPYING_STATUSES),
    )
    result = await session.execute(stmt)
    return int(result.scalar_one())


async def get_activities_in_group(
    session: AsyncSession, exclusive_group_id: str
) -> list[tuple[Activity, int]]:
    """
    Return all activities sharing an exclusive_group_id, ordered by
    start_time, each paired with occupied-seat count.
    """
    booked_subquery = (
        select(
            Booking.activity_id.label("activity_id"),
            func.count(Booking.id).label("booked"),
        )
        .where(Booking.status.in_(_OCCUPYING_STATUSES))
        .group_by(Booking.activity_id)
        .subquery()
    )
    stmt = (
        select(Activity, func.coalesce(booked_subquery.c.booked, 0))
        .outerjoin(booked_subquery, booked_subquery.c.activity_id == Activity.id)
        .where(Activity.exclusive_group_id == exclusive_group_id)
        .order_by(Activity.start_time, Activity.id)
    )
    result = await session.execute(stmt)
    return [(activity, int(booked)) for activity, booked in result.all()]


async def get_activities_in_slot(
    session: AsyncSession, day: int, start_time, end_time
) -> list[tuple[Activity, int]]:
    """
    Return the activities sharing one exact (start_time, end_time) window
    on the given day, each paired with its occupied-seat count.

    Used by the booking drill-down once a user has picked a time slot.
    """
    all_activities = await get_activities_for_day(session, day)
    return [
        (activity, booked)
        for activity, booked in all_activities
        if activity.start_time == start_time and activity.end_time == end_time
    ]


async def get_consultation_slots(session: AsyncSession, day: int) -> list[tuple[Activity, int]]:
    """Return all consultation-slot activities for a day, ordered by start time, with seat counts."""
    all_activities = await get_activities_for_day(session, day)
    return [(a, booked) for a, booked in all_activities if a.is_consultation_slot]


async def activities_due_for_free_seat_broadcast(
    session: AsyncSession, now, threshold
) -> list[tuple[Activity, int]]:
    """
    Activities starting within (now, threshold] that still have free seats
    and haven't had the free-seat broadcast sent yet.
    Returns (activity, booked_count) pairs.
    """
    booked_subquery = (
        select(
            Booking.activity_id.label("activity_id"),
            func.count(Booking.id).label("booked"),
        )
        .where(Booking.status.in_(_OCCUPYING_STATUSES))
        .group_by(Booking.activity_id)
        .subquery()
    )
    booked_col = func.coalesce(booked_subquery.c.booked, 0)
    stmt = (
        select(Activity, booked_col)
        .outerjoin(booked_subquery, booked_subquery.c.activity_id == Activity.id)
        .where(
            Activity.start_time > now,
            Activity.start_time <= threshold,
            Activity.broadcast_sent.is_(False),
            Activity.is_consultation_slot.is_(False),
            ~Activity.title.ilike("ЗБІР ГОСТЕЙ%"),
            booked_col < Activity.capacity,
        )
    )
    return [(a, int(b)) for a, b in (await session.execute(stmt)).all()]


async def mark_broadcast_sent(session: AsyncSession, activity: Activity) -> None:
    activity.broadcast_sent = True
    await session.commit()


async def activities_due_for_opens_broadcast(
    session: AsyncSession, now
) -> list[Activity]:
    """
    Activities whose booking_opens_at has just arrived (<=now) and
    haven't had the opens broadcast sent yet.
    """
    stmt = select(Activity).where(
        Activity.booking_opens_at.isnot(None),
        Activity.booking_opens_at <= now,
        Activity.opens_broadcast_sent.is_(False),
    )
    return list((await session.execute(stmt)).scalars().all())


async def mark_opens_broadcast_sent(session: AsyncSession, activity: Activity) -> None:
    activity.opens_broadcast_sent = True
    await session.commit()


async def activities_due_for_reminder_broadcast(
    session: AsyncSession, now, threshold
) -> list[Activity]:
    """
    Non-consultation activities starting within (now, threshold] that
    haven't had the T-30 non-booked broadcast sent yet.
    """
    stmt = select(Activity).where(
        Activity.start_time > now,
        Activity.start_time <= threshold,
        Activity.reminder_broadcast_sent.is_(False),
        Activity.is_consultation_slot.is_(False),
        ~Activity.title.ilike("ЗБІР ГОСТЕЙ%"),
    )
    return list((await session.execute(stmt)).scalars().all())


async def mark_reminder_broadcast_sent(session: AsyncSession, activity: Activity) -> None:
    activity.reminder_broadcast_sent = True
    await session.commit()
