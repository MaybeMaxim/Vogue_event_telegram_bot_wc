from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Admin


async def list_admins(session: AsyncSession) -> list[Admin]:
    return list((await session.execute(select(Admin).order_by(Admin.created_at))).scalars().all())


async def add_admin(session: AsyncSession, tg_id: int, added_by: int) -> Admin | None:
    """Add an admin. Returns None if already exists."""
    existing = (await session.execute(select(Admin).where(Admin.tg_id == tg_id))).scalar_one_or_none()
    if existing is not None:
        return None
    admin = Admin(tg_id=tg_id, added_by_tg_id=added_by)
    session.add(admin)
    await session.commit()
    await session.refresh(admin)
    return admin


async def remove_admin(session: AsyncSession, tg_id: int) -> bool:
    """Remove an admin by tg_id. Returns True if it existed."""
    admin = (await session.execute(select(Admin).where(Admin.tg_id == tg_id))).scalar_one_or_none()
    if admin is None:
        return False
    await session.delete(admin)
    await session.commit()
    return True
