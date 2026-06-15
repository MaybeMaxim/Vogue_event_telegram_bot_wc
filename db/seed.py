"""
Seed script: populates the `activities` table with the Wellness Escape
schedule, per the CORRECTED brief (poprawki override the original TZ).

Run once after init_db():

    python -m db.seed

Re-running this script will raise if activities already exist, to avoid
accidental duplicates — delete wellness.db (or the activities rows) first
if you need to reseed during development.

--- SCHEDULE SOURCE OF TRUTH ----------------------------------------------

Day 1 (event_year-06-24):
  12:00-14:00  exclusive group "day1_slot1" (pick ONE):
      - Тест-драйв            (20)
      - Фейс-масаж            (20)
      - Екскурсія територією  (20)
  16:00-17:00  standalone:
      - Лекція "Garden Therapy" з Сонею Солтес (60)

Day 2 (event_year-06-25):
  11:00-12:00  exclusive group "day2_slot1" (pick ONE):
      - Барре                 (20)
      - Тест-драйв            (20)
  12:00-13:00  exclusive group "day2_slot2" (pick ONE):
      - Sound healing         (20)
      - Тест-драйв            (20)
  16:00-19:00  Anna Barinova individual consultations:
      - generated as 15-minute slots, capacity=1 each,
        is_consultation_slot=True, NOT part of an exclusive group
        (they don't overlap with each other by construction, and the
        "no parallel activities" rule via time-overlap already prevents
        booking a consultation that overlaps another activity).

LOCATION PLACEHOLDERS:
  Real venue locations were not specified in the brief. Each activity
  below has a placeholder location string marked "# TODO location" —
  replace these with actual venue zone names before the event so that
  reminder messages ("куди йти") are accurate.
----------------------------------------------------------------------------
"""

import asyncio
from datetime import datetime, timedelta, timezone

from zoneinfo import ZoneInfo

from config import settings
from db.base import async_session, init_db
from db.models import Activity

_TZ = ZoneInfo(settings.event_timezone)


def _dt(day: int, hour: int, minute: int = 0) -> datetime:
    """
    Build the UTC datetime for a given event day (1 or 2) and local
    (Europe/Kyiv) time.

    The result is returned as a NAIVE datetime in UTC, matching how
    SQLite/SQLAlchemy round-trips DateTime values (see
    utils.time_utils.to_local for why naive-UTC is the storage
    convention used throughout this project).
    """
    local_dt = datetime(settings.event_year, 6, 24 if day == 1 else 25, hour, minute, tzinfo=_TZ)
    return local_dt.astimezone(timezone.utc).replace(tzinfo=None)


def _consultation_slots() -> list[Activity]:
    """
    Generate Anna Barinova's individual consultation slots:
    16:00-19:00, 15-minute increments -> 12 slots, capacity 1 each.
    """
    slots: list[Activity] = []

    slot_start = _dt(2, 16, 0)
    window_end = _dt(2, 19, 0)
    slot_length = timedelta(minutes=15)

    while slot_start < window_end:
        slot_end = slot_start + slot_length

        # slot_start/slot_end are naive UTC; format the title using
        # local (event timezone) wall-clock time for readability.
        local_start = slot_start.replace(tzinfo=timezone.utc).astimezone(_TZ)
        local_end = slot_end.replace(tzinfo=timezone.utc).astimezone(_TZ)

        slots.append(
            Activity(
                title=f"Консультація Анни Барінової ({local_start.strftime('%H:%M')}-{local_end.strftime('%H:%M')})",
                day=2,
                start_time=slot_start,
                end_time=slot_end,
                capacity=1,
                description="Індивідуальна консультація з хірургинею Анною Баріновою.",
                speaker_name="Анна Барінова",
                speaker_social_url=None,
                location_text="Кабінет консультацій",  # TODO location
                exclusive_group_id=None,
                requires_confirmation=True,
                is_consultation_slot=True,
            )
        )
        slot_start = slot_end

    return slots


def build_seed_activities() -> list[Activity]:
    """Return the full list of Activity rows to insert."""
    activities: list[Activity] = []

    # ------------------------------------------------------------------
    # Day 1, 12:00-14:00 — exclusive group "day1_slot1"
    # ------------------------------------------------------------------
    day1_start = _dt(1, 12, 0)
    day1_end = _dt(1, 14, 0)

    activities.append(
        Activity(
            title="Тест-драйв",
            day=1,
            start_time=day1_start,
            end_time=day1_end,
            capacity=20,
            description="Спробуйте автомобіль на тестовому маршруті разом з інструктором.",
            speaker_name=None,
            speaker_social_url=None,
            location_text="Зона тест-драйву",  # TODO location
            exclusive_group_id="day1_slot1",
            requires_confirmation=True,
            is_consultation_slot=False,
        )
    )
    activities.append(
        Activity(
            title="Фейс-масаж",
            day=1,
            start_time=day1_start,
            end_time=day1_end,
            capacity=20,
            description="Розслаблюючий масаж обличчя від професійних майстрів.",
            speaker_name=None,
            speaker_social_url=None,
            location_text="Зона фейс-масажу",  # TODO location
            exclusive_group_id="day1_slot1",
            requires_confirmation=True,
            is_consultation_slot=False,
        )
    )
    activities.append(
        Activity(
            title="Екскурсія територією",
            day=1,
            start_time=day1_start,
            end_time=day1_end,
            capacity=20,
            description="Прогулянка територією заходу з гідом.",
            speaker_name=None,
            speaker_social_url=None,
            location_text="Збір біля головного входу",  # TODO location
            exclusive_group_id="day1_slot1",
            requires_confirmation=True,
            is_consultation_slot=False,
        )
    )

    # ------------------------------------------------------------------
    # Day 1, 16:00-17:00 — standalone lecture
    # ------------------------------------------------------------------
    activities.append(
        Activity(
            title='Лекція "Garden Therapy" із Сонею Солтес',
            day=1,
            start_time=_dt(1, 16, 0),
            end_time=_dt(1, 17, 0),
            capacity=60,
            description="Про терапевтичну силу садівництва та зв'язок із природою.",
            speaker_name="Соня Солтес",
            speaker_social_url=None,
            location_text="Лекційний зал",  # TODO location
            exclusive_group_id=None,
            requires_confirmation=True,
            is_consultation_slot=False,
        )
    )

    # ------------------------------------------------------------------
    # Day 2, 11:00-12:00 — exclusive group "day2_slot1"
    # ------------------------------------------------------------------
    day2_slot1_start = _dt(2, 11, 0)
    day2_slot1_end = _dt(2, 12, 0)

    activities.append(
        Activity(
            title="Барре",
            day=2,
            start_time=day2_slot1_start,
            end_time=day2_slot1_end,
            capacity=20,
            description="Заняття біля станка для гнучкості, постави та тонусу м'язів.",
            speaker_name=None,
            speaker_social_url=None,
            location_text="Зала для групових занять",  # TODO location
            exclusive_group_id="day2_slot1",
            requires_confirmation=True,
            is_consultation_slot=False,
        )
    )
    activities.append(
        Activity(
            title="Тест-драйв",
            day=2,
            start_time=day2_slot1_start,
            end_time=day2_slot1_end,
            capacity=20,
            description="Спробуйте автомобіль на тестовому маршруті разом з інструктором.",
            speaker_name=None,
            speaker_social_url=None,
            location_text="Зона тест-драйву",  # TODO location
            exclusive_group_id="day2_slot1",
            requires_confirmation=True,
            is_consultation_slot=False,
        )
    )

    # ------------------------------------------------------------------
    # Day 2, 12:00-13:00 — exclusive group "day2_slot2"
    # ------------------------------------------------------------------
    day2_slot2_start = _dt(2, 12, 0)
    day2_slot2_end = _dt(2, 13, 0)

    activities.append(
        Activity(
            title="Sound healing",
            day=2,
            start_time=day2_slot2_start,
            end_time=day2_slot2_end,
            capacity=20,
            description="Звукова медитація зі співочими чашами для глибокого розслаблення.",
            speaker_name=None,
            speaker_social_url=None,
            location_text="Зала для звукових практик",  # TODO location
            exclusive_group_id="day2_slot2",
            requires_confirmation=True,
            is_consultation_slot=False,
        )
    )
    activities.append(
        Activity(
            title="Тест-драйв",
            day=2,
            start_time=day2_slot2_start,
            end_time=day2_slot2_end,
            capacity=20,
            description="Спробуйте автомобіль на тестовому маршруті разом з інструктором.",
            speaker_name=None,
            speaker_social_url=None,
            location_text="Зона тест-драйву",  # TODO location
            exclusive_group_id="day2_slot2",
            requires_confirmation=True,
            is_consultation_slot=False,
        )
    )

    # ------------------------------------------------------------------
    # Day 2, 16:00-19:00 — Anna Barinova consultation slots
    # ------------------------------------------------------------------
    activities.extend(_consultation_slots())

    return activities


async def seed() -> None:
    """Insert the seed activities, refusing to run if any already exist."""
    await init_db()

    async with async_session() as session:
        from sqlalchemy import select

        existing = await session.execute(select(Activity.id).limit(1))
        if existing.first() is not None:
            print(
                "Activities table is not empty — skipping seed. "
                "Delete wellness.db (or the activities rows) to reseed."
            )
            return

        activities = build_seed_activities()
        session.add_all(activities)
        await session.commit()

        print(f"Seeded {len(activities)} activities.")


if __name__ == "__main__":
    asyncio.run(seed())
