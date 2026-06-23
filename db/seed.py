"""
Seed script: populates the `activities` table for Vogue Ukraine Wellness Escape
(24-25.06) per the confirmed technical requirements.

Run once after init_db():

    python -m db.seed

Re-running will refuse if any activities already exist.

--- SCHEDULE ---------------------------------------------------------------

Day 1 (24.06):
  12:00-13:00  Мінітест-драйв sub-slots × 3 (12:00/12:20/12:40, cap=3 each, паркінг)
               Босоніж: прогулянка з Дар'єю Білодід (cap=20, понтон)
  13:00-14:00  Мінітест-драйв sub-slots × 3 (13:00/13:20/13:40, cap=3 each, паркінг)
               Wellness Walk (13:00, cap=20, зона реєстрації)
               Wellness Walk (13:30, cap=20, зона реєстрації)
  12:00-16:00  Kérastase hair-care slots (every 20 min 12:00→15:40, cap=1 each)
  16:20-18:40  Консультації Анни Барінової (8 × 20-min, cap=1, кімн.101 1-й пов.)
               booking_opens_at = 15:30 local
  17:00-18:00  Garden Therapy з Сонею Солтес (cap=60, Edem Garden)

Day 2 (25.06):
  11:30-12:30  Мінітест-драйв sub-slots × 3 (11:30/11:50/12:10, cap=3 each, паркінг)
               Барре з Катериною Кухар (cap=20, понтон)
  12:30-13:30  Мінітест-драйв sub-slots × 3 (12:30/12:50/13:10, cap=3 each, паркінг)
               Sound Healing (cap=20, лекторій 5 пов.)
  12:00-16:00  Kérastase hair-care slots (every 20 min 12:00→15:40, cap=1 each)
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
    """Naive UTC datetime for a given event day (1=day1, 2=day2) and local time."""
    calendar_day = settings.event_day1 if day == 1 else settings.event_day2
    local_dt = datetime(settings.event_year, settings.event_month, calendar_day, hour, minute, tzinfo=_TZ)
    return local_dt.astimezone(timezone.utc).replace(tzinfo=None)


def _testdrive_slots(day: int, starts: list[tuple[int, int]], group_id: str) -> list[Activity]:
    """Generate mini test-drive sub-slots (20 min each, cap=3)."""
    slots = []
    for hour, minute in starts:
        start = _dt(day, hour, minute)
        end = start + timedelta(minutes=20)
        local_start = start.replace(tzinfo=timezone.utc).astimezone(_TZ)
        local_end = end.replace(tzinfo=timezone.utc).astimezone(_TZ)
        slots.append(Activity(
            title=f"Тест-драйв MINI Countryman ({local_start.strftime('%H:%M')}-{local_end.strftime('%H:%M')})",
            day=day,
            start_time=start,
            end_time=end,
            capacity=3,
            description="Короткий ознайомчий тест-драйв MINI Countryman з інструктором (20 хв).",
            speaker_name=None,
            speaker_social_url=None,
            location_text="Паркінг + рецепція",
            exclusive_group_id=group_id,
            requires_confirmation=True,
            is_consultation_slot=False,
            booking_opens_at=None,
        ))
    return slots


def _kerastase_slots(day: int) -> list[Activity]:
    """Generate Kérastase hair-care slots: every 20 min 12:00-15:40, cap=1."""
    group_id = f"d{day}_kerastase"
    slots = []
    start = _dt(day, 12, 0)
    window_end = _dt(day, 16, 0)
    step = timedelta(minutes=20)
    while start < window_end:
        end = start + step
        local_start = start.replace(tzinfo=timezone.utc).astimezone(_TZ)
        local_end = end.replace(tzinfo=timezone.utc).astimezone(_TZ)
        slots.append(Activity(
            title=f"Kérastase: діагностика волосся ({local_start.strftime('%H:%M')}-{local_end.strftime('%H:%M')})",
            day=day,
            start_time=start,
            end_time=end,
            capacity=1,
            description="Індивідуальна діагностика стану волосся та доглядова процедура від Kérastase.",
            speaker_name=None,
            speaker_social_url=None,
            location_text="5-й поверх",
            exclusive_group_id=group_id,
            requires_confirmation=False,
            is_consultation_slot=False,
            booking_opens_at=None,
        ))
        start = end
    return slots


def _consultation_slots() -> list[Activity]:
    """
    8 consultation slots on Day 1: 16:20-18:40 in 20-min increments, cap=1 each.
    Booking unlocks at 15:30 local time on Day 1.
    """
    opens_at = _dt(1, 15, 30)
    slots = []
    start = _dt(1, 16, 0)
    slot_end_boundary = _dt(1, 19, 0)  # 9 slots: 16:00/16:20/16:40/17:00/17:20/17:40/18:00/18:20/18:40
    step = timedelta(minutes=20)
    while start < slot_end_boundary:
        end = start + step
        local_start = start.replace(tzinfo=timezone.utc).astimezone(_TZ)
        local_end = end.replace(tzinfo=timezone.utc).astimezone(_TZ)
        slots.append(Activity(
            title=f"Консультація Анни Барінової ({local_start.strftime('%H:%M')}-{local_end.strftime('%H:%M')})",
            day=1,
            start_time=start,
            end_time=end,
            capacity=1,
            description="Індивідуальна консультація з лікарем-хірургом Анною Баріновою.",
            speaker_name="Анна Барінова",
            speaker_social_url=None,
            location_text="Кімната 101, 1-й поверх",
            exclusive_group_id=None,
            requires_confirmation=True,
            is_consultation_slot=True,
            booking_opens_at=opens_at,
        ))
        start = end
    return slots


def build_seed_activities() -> list[Activity]:
    activities: list[Activity] = []

    # ------------------------------------------------------------------
    # Day 1  12:00-13:00 block  (group d1_slot1)
    # ------------------------------------------------------------------
    activities.extend(_testdrive_slots(1, [(12, 0), (12, 20), (12, 40)], "d1_slot1"))

    activities.append(Activity(
        title="Розминка з Дар'єю Білодід",
        day=1,
        start_time=_dt(1, 12, 0),
        end_time=_dt(1, 13, 0),
        capacity=20,
        description="Розслаблювальна розминка босоніж з олімпійською призеркою з дзюдо Дар'єю Білодід.",
        speaker_name="Дар'я Білодід",
        speaker_social_url=None,
        location_text="Понтон",
        exclusive_group_id="d1_slot1",
        requires_confirmation=True,
        is_consultation_slot=False,
        booking_opens_at=None,
    ))

    # ------------------------------------------------------------------
    # Day 1  13:00-14:00 block  (group d1_slot2)
    # ------------------------------------------------------------------
    activities.extend(_testdrive_slots(1, [(13, 0), (13, 20), (13, 40)], "d1_slot2"))

    activities.append(Activity(
        title="Wellness Walk (13:00-13:30)",
        day=1,
        start_time=_dt(1, 13, 0),
        end_time=_dt(1, 13, 30),
        capacity=20,
        description="Наснажлива прогулянка з флористкою Юлією Борисенко та шеф-редакторкою vogue.ua Віолеттою Федоровою.",
        speaker_name="Юлія Борисенко та Віолетта Федорова",
        speaker_social_url=None,
        location_text="Рецепція",
        exclusive_group_id="d1_slot2",
        requires_confirmation=True,
        is_consultation_slot=False,
        booking_opens_at=None,
    ))
    activities.append(Activity(
        title="Wellness Walk (13:30-14:00)",
        day=1,
        start_time=_dt(1, 13, 30),
        end_time=_dt(1, 14, 0),
        capacity=20,
        description="Наснажлива прогулянка з флористкою Юлією Борисенко та шеф-редакторкою vogue.ua Віолеттою Федоровою.",
        speaker_name="Юлія Борисенко та Віолетта Федорова",
        speaker_social_url=None,
        location_text="Рецепція",
        exclusive_group_id="d1_slot2",
        requires_confirmation=True,
        is_consultation_slot=False,
        booking_opens_at=None,
    ))

    # ------------------------------------------------------------------
    # Day 1  Kérastase slots (12:00-15:40, every 20 min)
    # ------------------------------------------------------------------
    activities.extend(_kerastase_slots(1))

    # ------------------------------------------------------------------
    # Day 1  17:00-18:00  Garden Therapy
    # ------------------------------------------------------------------
    activities.append(Activity(
        title='Garden Therapy із Сонею Солтес',
        day=1,
        start_time=_dt(1, 17, 0),
        end_time=_dt(1, 18, 0),
        capacity=60,
        description="Тактильна сесія взаємодії з рослинами з стилісткою та ентузіасткою гарден-терапії Софією Солтес.",
        speaker_name="Софія Солтес",
        speaker_social_url=None,
        location_text="Edem Garden",
        exclusive_group_id=None,
        requires_confirmation=True,
        is_consultation_slot=False,
        booking_opens_at=None,
    ))

    # ------------------------------------------------------------------
    # Day 1  Consultation slots (16:20-18:40, opens 15:30)
    # ------------------------------------------------------------------
    activities.extend(_consultation_slots())

    # ------------------------------------------------------------------
    # Day 2  11:30-12:30 block  (group d2_slot1)
    # ------------------------------------------------------------------
    activities.extend(_testdrive_slots(2, [(11, 30), (11, 50), (12, 10)], "d2_slot1"))

    activities.append(Activity(
        title="Клас барре з Катериною Кухар",
        day=2,
        start_time=_dt(2, 11, 30),
        end_time=_dt(2, 12, 30),
        capacity=20,
        description="Клас барре із прима-балериною Катериною Кухар для гнучкості, постави та тонусу.",
        speaker_name="Катерина Кухар",
        speaker_social_url=None,
        location_text="Понтон",
        exclusive_group_id="d2_slot1",
        requires_confirmation=True,
        is_consultation_slot=False,
        booking_opens_at=None,
    ))

    # ------------------------------------------------------------------
    # Day 2  12:30-13:30 block  (group d2_slot2)
    # ------------------------------------------------------------------
    activities.extend(_testdrive_slots(2, [(12, 30), (12, 50), (13, 10)], "d2_slot2"))

    activities.append(Activity(
        title="Практика Sound Healing",
        day=2,
        start_time=_dt(2, 12, 30),
        end_time=_dt(2, 13, 30),
        capacity=20,
        description="Звукова медитація зі співочими чашами для глибокого розслаблення від Divya Svara.",
        speaker_name="Divya Svara",
        speaker_social_url=None,
        location_text="Edem Garden",
        exclusive_group_id="d2_slot2",
        requires_confirmation=True,
        is_consultation_slot=False,
        booking_opens_at=None,
    ))

    # ------------------------------------------------------------------
    # Day 2  Kérastase slots (12:00-15:40, every 20 min)
    # ------------------------------------------------------------------
    activities.extend(_kerastase_slots(2))

    return activities


async def seed() -> None:
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
