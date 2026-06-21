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
from handlers.booking import router as booking_router
from handlers.my_bookings import router as my_bookings_router
from handlers.profile import router as profile_router
from handlers.support import router as support_router
from handlers.question import router as question_router
from handlers.admin import router as admin_router
from filters.admin import load_db_admins
from middlewares.registration_check import RegistrationRequiredMiddleware
from middlewares.menu_state_reset import MenuStateResetMiddleware
from scheduler.ticker import start_ticker, startup_flush


class DbSessionMiddleware:
    """Injects a fresh AsyncSession into handler data for every update."""

    async def __call__(self, handler, event, data):
        async with async_session() as session:
            data["session"] = session
            return await handler(event, data)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    await init_db()
    await load_db_admins()
    await startup_flush()

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    start_ticker(bot)

    dp.update.middleware(DbSessionMiddleware())
    dp.update.middleware(RegistrationRequiredMiddleware())

    # Inner middleware on the message observer: FSM `state` is guaranteed
    # to be in `data` here, which it is not at the raw-update level.
    dp.message.middleware(MenuStateResetMiddleware())

    dp.include_router(admin_router)
    dp.include_router(registration_router)
    dp.include_router(schedule_router)
    dp.include_router(booking_router)
    dp.include_router(my_bookings_router)
    dp.include_router(profile_router)
    dp.include_router(support_router)
    dp.include_router(question_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
