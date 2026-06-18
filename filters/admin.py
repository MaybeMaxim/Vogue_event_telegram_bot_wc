"""
Filter restricting handlers to configured admin user IDs.

Usage:
    from filters.admin import IsAdmin
    @router.message(IsAdmin(), Command("admin"))

Admins are listed in config.settings.admin_ids.
"""

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from config import settings


class IsAdmin(BaseFilter):
    """Passes only if the acting user's Telegram id is in admin_ids."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        return user is not None and user.id in settings.admin_ids
