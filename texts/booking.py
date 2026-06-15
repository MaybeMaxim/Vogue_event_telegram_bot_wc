"""
User-facing strings for the booking drill-down ("✍️ Записатись").

ParseMode.HTML is active; dynamic DB text is html.escape()d in
services.booking_service before insertion here.
"""

# Step 1 — day picker
BOOK_INTRO = "На який день хочете записатись? 👇"

# Step 2 — slot picker. The intro is followed by a per-slot overview
# (time + the activities in that slot), then time buttons below.
SLOT_PICKER_INTRO = "📅 <b>День {day} ({date})</b>"
SLOT_PICKER_PROMPT = "Оберіть час, щоб побачити деталі та записатись 👇"

# One block in the slot-picker overview: time header + activity names.
SLOT_OVERVIEW_BLOCK = "🕒 <b>{time_range}</b>\n{names}"

# Step 3 — activity picker (one slot)
ACTIVITY_PICKER_HEADER = "🕒 <b>{time_range}</b>"
ACTIVITY_PICKER_EXCLUSIVE_HINT = "<i>Можна обрати лише один варіант із цього часу.</i>"
ACTIVITY_PICKER_LINE = "{dot} <b>{title}</b> — {seats}"
ACTIVITY_PICKER_SPEAKER = "    👤 {speaker_name}"
ACTIVITY_PICKER_DESC = "    <i>{description}</i>"

# Buttons
BOOK_ACTIVITY_BUTTON = "✍️ Записатись на «{title}»"
WAITLIST_ACTIVITY_BUTTON = "🔔 Лист очікування: «{title}»"
BACK_TO_SLOTS_BUTTON = "⬅️ Назад до часу"
BACK_TO_DAYS_BUTTON = "⬅️ Обрати інший день"

# Consultation slot button (leads into the per-slot consultation picker)
CONSULTATION_SLOT_BUTTON = "🩺 {time_range} · Консультації Анни Барінової"

# Placeholder until booking actions / consultation picker are wired up.
BOOKING_COMING_SOON = "🚧 Запис на цю активність буде доступний найближчим часом."
CONSULTATION_COMING_SOON = "🚧 Запис на консультації буде доступний найближчим часом."

NO_ACTIVITIES_FOR_DAY = "На цей день активностей не знайдено."
