"""
Aggregates all registration-related routers into one, so bot.py
only needs a single include_router() call for the whole flow.
"""

from aiogram import Router

from handlers.registration import confirm, email, phone, start

router = Router(name="registration")

# Order matters where states are shared between modules:
# confirm.py's edit-button callbacks must be registered before
# start.py/phone.py's text handlers for the same states, so that
# callback queries are matched first (different update type, but
# keeping the registration order explicit avoids any ambiguity).
router.include_router(confirm.router)
router.include_router(start.router)
router.include_router(phone.router)
router.include_router(email.router)
