"""
CRUD helpers for the Activity model.

`get_activities_for_day` returns activities together with their current
"occupied seats" count — i.e. bookings that still hold a seat. A seat is
considered occupied for any status except CANCELLED/NO_SHOW, since
PENDING_CONFIRMATION and ATTENDED bookings still represent a held spot.
"""

from sqlalchemy import func, select
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
