"""Schedule rendering — returns hardcoded text from texts/schedule.py."""

from texts.schedule import SCHEDULE


def render_day_schedule(day: int) -> str:
    return SCHEDULE[day]
