"""
All user-facing strings for the schedule view (📅 Розклад).

As with texts/registration.py, expect this wording to change --
handlers must reference these constants, not inline strings.

NOTE on formatting: the bot runs with ParseMode.HTML (see bot.py), so
these templates use <b>, <a href="...">, etc. Any *dynamic* values
inserted into these templates (activity titles, speaker names) MUST be
passed through html.escape() first — see services.schedule_service.
"""

SCHEDULE_INTRO = "Оберіть день, щоб переглянути розклад 👇"

DAY_BUTTON = "День {day} ({date})"

DAY_HEADER = "📅 <b>Розклад — День {day} ({date})</b>"

TIME_SLOT_HEADER = "🕒 <b>{time_range}</b>"

# Appended to TIME_SLOT_HEADER when the activities in this slot are
# mutually exclusive alternatives (only one can be booked).
TIME_SLOT_EXCLUSIVE_HINT = " · оберіть один варіант"

# One activity card within a time slot. {title} is bold; {availability}
# is the 🟢/🟡/🔴 + seat-count line from utils.status_emoji.
ACTIVITY_CARD = "  <b>{title}</b>\n    {availability}"

# Optional speaker line, appended to a card if present. If the speaker
# has a social link, {speaker_name} is wrapped in <a href="..."> by
# services.schedule_service; otherwise it's plain text.
ACTIVITY_SPEAKER_LINE = "    👤 {speaker_name}"

# Summary line for the Barinova consultation block (collapsed, not
# expanded into 12 individual cards in the full-schedule view).
CONSULTATION_SUMMARY = (
    "🕒 <b>{time_range}</b>\n"
    "  <b>{title}</b>\n"
    "    {availability_summary}\n"
    "    Запис на конкретний слот — у розділі «🩺 Консультація хірурга»"
)

NO_ACTIVITIES_FOR_DAY = "На цей день активностей не знайдено."

BACK_TO_DAYS_BUTTON = "⬅️ Обрати інший день"

# Per-activity inline booking buttons.
BOOK_BUTTON = "✍️ Записатись"
WAITLIST_BUTTON = "🔔 У лист очікування"

# Shown when the booking flow isn't wired up yet (placeholder for this step).
BOOKING_COMING_SOON = "🚧 Запис на цю активність буде доступний найближчим часом."
