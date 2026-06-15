"""
CRUD helpers for the Waitlist model (FIFO queue per activity).

Ordering is by created_at within (activity_id, status=WAITING). The
service layer handles promotion logic; these are the raw queries.
"""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Waitlist, WaitlistStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def get_waitlist_entry(session: AsyncSession, user_id: int, activity_id: int) -> Waitlist | None:
    """Return the user's non-terminal waitlist entry for an activity, if any."""
    stmt = select(Waitlist).where(
        Waitlist.user_id == user_id,
        Waitlist.activity_id == activity_id,
        Waitlist.status.in_((WaitlistStatus.WAITING, WaitlistStatus.OFFERED)),
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def add_to_waitlist(session: AsyncSession, user_id: int, activity_id: int) -> Waitlist:
    """Append a user to an activity's waitlist (status WAITING)."""
    entry = Waitlist(user_id=user_id, activity_id=activity_id, status=WaitlistStatus.WAITING)
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


async def waitlist_position(session: AsyncSession, entry: Waitlist) -> int:
    """1-based position of a WAITING entry in its activity's FIFO queue."""
    stmt = select(func.count(Waitlist.id)).where(
        Waitlist.activity_id == entry.activity_id,
        Waitlist.status == WaitlistStatus.WAITING,
        Waitlist.created_at < entry.created_at,
    )
    return int((await session.execute(stmt)).scalar_one()) + 1


async def next_waiting(session: AsyncSession, activity_id: int) -> Waitlist | None:
    """Return the head of an activity's WAITING queue (oldest), or None."""
    stmt = (
        select(Waitlist)
        .where(Waitlist.activity_id == activity_id, Waitlist.status == WaitlistStatus.WAITING)
        .order_by(Waitlist.created_at)
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def mark_offered(session: AsyncSession, entry: Waitlist, expires_at: datetime) -> None:
    """Move an entry to OFFERED with a confirmation deadline."""
    entry.status = WaitlistStatus.OFFERED
    entry.offer_sent_at = _utcnow()
    entry.offer_expires_at = expires_at
    await session.commit()


async def mark_confirmed(session: AsyncSession, entry: Waitlist) -> None:
    """Mark a waitlist entry CONFIRMED (a Booking was created for it)."""
    entry.status = WaitlistStatus.CONFIRMED
    await session.commit()


async def mark_expired(session: AsyncSession, entry: Waitlist) -> None:
    """Mark a waitlist offer EXPIRED (user didn't confirm in time / declined)."""
    entry.status = WaitlistStatus.EXPIRED
    await session.commit()


async def remove_from_waitlist(session: AsyncSession, entry: Waitlist) -> None:
    """Mark a waitlist entry EXPIRED to remove it from active consideration."""
    entry.status = WaitlistStatus.EXPIRED
    await session.commit()


async def expired_offers(session: AsyncSession, now: datetime) -> list[Waitlist]:
    """OFFERED entries whose confirmation deadline has passed."""
    stmt = select(Waitlist).where(
        Waitlist.status == WaitlistStatus.OFFERED,
        Waitlist.offer_expires_at.isnot(None),
        Waitlist.offer_expires_at <= now,
    )
    return list((await session.execute(stmt)).scalars().all())
