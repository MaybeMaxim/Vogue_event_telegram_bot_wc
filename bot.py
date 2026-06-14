import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from db.base import async_session, init_db
from handlers.registration import router as registration_router
from handlers.schedule import router as schedule_router
from middlewares.registration_check import RegistrationRequiredMiddleware


class DbSessionMiddleware:
    """Injects a fresh AsyncSession into handler data for every update."""

    async def __call__(self, handler, event, data):
        async with async_session() as session:
            data["session"] = session
            return await handler(event, data)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    await init_db()

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(DbSessionMiddleware())
    dp.update.middleware(RegistrationRequiredMiddleware())

    dp.include_router(registration_router)
    dp.include_router(schedule_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
