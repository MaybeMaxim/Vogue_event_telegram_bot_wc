"""
All user-facing strings for the read-only schedule view (📅 Розклад).

This view is now PURELY read-only — booking happens under
"✍️ Записатись" (see texts/booking.py). The schedule just shows a
clean, well-spaced overview of both days with availability dots.

NOTE on formatting: the bot runs with ParseMode.HTML (see bot.py), so
these templates use <b>, <a href="...">, etc. Any dynamic values
(activity titles, speaker names) MUST be passed through html.escape()
first — see services.schedule_service.
"""

SCHEDULE_INTRO = "Оберіть день, щоб переглянути розклад 👇"

DAY_BUTTON = "День {day} ({date})"

DAY_HEADER = "📅 <b>Розклад — День {day} ({date})</b>"

# Time-slot header. The exclusive hint is appended when the activities
# in the slot are mutually exclusive alternatives.
TIME_SLOT_HEADER = "🕒 <b>{time_range}</b>"
TIME_SLOT_EXCLUSIVE_HINT = "  <i>· оберіть один варіант</i>"

# One activity line: status dot + title + seat count, all on one line
# for a tight, scannable layout. {dot} is the 🟢/🟡/🔴 emoji.
ACTIVITY_LINE = "{dot} <b>{title}</b> — {seats}"

# Speaker sub-line under an activity (only when a speaker is set).
ACTIVITY_SPEAKER_LINE = "    👤 {speaker_name}"

# Description sub-line under an activity (only when a description is set).
ACTIVITY_DESC_LINE = "    <i>{description}</i>"

# Collapsed summary for the Barinova consultation block.
CONSULTATION_LINE = "{dot} <b>{title}</b> — {seats}"

NO_ACTIVITIES_FOR_DAY = "На цей день активностей не знайдено."

BACK_TO_DAYS_BUTTON = "⬅️ Обрати інший день"

# Footer hint pointing users to where booking actually happens.
BOOK_HINT = "\n💡 Щоб записатись, відкрийте «✍️ Записатись» у меню."
