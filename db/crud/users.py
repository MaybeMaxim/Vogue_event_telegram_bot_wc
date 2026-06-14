from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User


async def get_user_by_tg_id(session: AsyncSession, tg_id: int) -> User | None:
    """Return the registered profile for this Telegram user, or None."""
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    tg_id: int,
    full_name: str,
    phone: str,
    email: str,
) -> User:
    """
    Persist a new user profile and return it.

    Idempotent on tg_id: if a profile for this tg_id already exists
    (e.g. the user double-tapped "save", or two updates raced each
    other), the existing profile is returned instead of raising —
    registration should never fail just because it already succeeded.
    """
    user = User(tg_id=tg_id, full_name=full_name, phone=phone, email=email)
    session.add(user)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await get_user_by_tg_id(session, tg_id)
        if existing is not None:
            return existing
        raise

    await session.refresh(user)
    return user
