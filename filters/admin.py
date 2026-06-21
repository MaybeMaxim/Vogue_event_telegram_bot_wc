"""
Filter restricting handlers to admin users.

Admins come from two sources:
  1. config.settings.admin_ids — static list in .env (always authoritative)
  2. _extra_admins — in-memory set loaded from DB on startup and updated
     when admins are added/removed via /addadmin and /removeadmin.

Use load_db_admins() once at startup, then add_admin_to_cache() /
remove_admin_from_cache() to keep the set in sync without DB queries per
update.
"""

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from config import settings

_extra_admins: set[int] = set()


def is_admin(tg_id: int) -> bool:
    return tg_id in settings.admin_ids or tg_id in _extra_admins


def add_admin_to_cache(tg_id: int) -> None:
    _extra_admins.add(tg_id)


def remove_admin_from_cache(tg_id: int) -> None:
    _extra_admins.discard(tg_id)


async def load_db_admins() -> None:
    """Call once at startup to populate the cache from DB."""
    from db.base import async_session
    from db.crud.admins import list_admins
    async with async_session() as session:
        for admin in await list_admins(session):
            _extra_admins.add(admin.tg_id)


class IsAdmin(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        return user is not None and is_admin(user.id)
