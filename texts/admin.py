"""User-facing strings for the admin panel."""

NOT_ADMIN = "Ця команда доступна лише адміністраторам."

ADMIN_MENU = "🛠 <b>Адмін-панель</b>\n\nОберіть розділ 👇"

# Menu buttons
BTN_PARTICIPANTS = "📋 Списки учасників"
BTN_WAITLISTS = "🕒 Листи очікування"
BTN_SEARCH = "🔍 Пошук гостя"
BTN_ADD = "➕ Додати гостя"
BTN_EXPORT = "📊 Експорт"
BTN_QUESTIONS = "🤍 Питання SEX WELLNESS TALK"
BTN_BACK = "⬅️ Назад"
BTN_CLOSE = "✅ Закрити"

QUESTIONS_HEADER = "🤍 <b>Питання SEX WELLNESS TALK</b> — {count} шт.\n\n"
QUESTIONS_EMPTY = "🤍 <b>Питання SEX WELLNESS TALK</b>\n\nЗапитань поки немає."
QUESTION_ITEM = "{num}. {text}\n"

# Activity picker (shared by participants / waitlists / manual add)
PICK_ACTIVITY = "Оберіть активність 👇"
ACTIVITY_BTN = "Д{day} · {time} · {title}"
CONSULT_LIST_BTN = "Консультації Анни Баринової"

# Participant list
PARTICIPANTS_HEADER = "📋 <b>{title}</b>\n🕒 {time_range}\nЗайнято: {count} з {capacity}\n"
PARTICIPANTS_EMPTY = "На цю активність ще ніхто не записаний."
PARTICIPANT_LINE = "{idx}. {mark} <b>{name}</b>\n     📱 {phone}"
ATTENDED_MARK = "✅"
NOT_ATTENDED_MARK = "▫️"
TOGGLE_HINT = "\nНатисніть на гостя, щоб відмітити присутність."

# Combined consultations participant list
CONSULT_PARTICIPANTS_HEADER = "<b>Консультації Анни Баринової</b>\nЗаписано слотів: {count} з {total}\n"
CONSULT_PARTICIPANT_LINE = "🕒 {time} {mark} <b>{name}</b> — 📱 {phone}"

# Waitlist view
WAITLIST_HEADER = "🕒 <b>Лист очікування — {title}</b>\n{time_range}\n"
WAITLIST_EMPTY = "Лист очікування порожній."
WAITLIST_LINE = "{idx}. <b>{name}</b> — 📱 {phone} {status}"
WL_STATUS_OFFERED = "(запропоновано)"
WL_STATUS_WAITING = ""

# Search
SEARCH_PROMPT = "🔍 Введіть прізвище або номер телефону гостя:"
SEARCH_EMPTY = "Нічого не знайдено за запитом «{query}»."
SEARCH_RESULT_HEADER = "Знайдено гостей: {count}"
GUEST_CARD = (
    "👤 <b>{name}</b>\n"
    "📱 {phone}\n"
    "📧 {email}\n\n"
    "<b>Записи:</b>\n{bookings}"
)
GUEST_NO_BOOKINGS = "— немає записів —"
GUEST_BOOKING_LINE = "• Д{day} {time} — {title}"

# Manual add
ADD_PICK_ACTIVITY = "➕ Оберіть активність, на яку додати гостя 👇"
ADD_SEARCH_PROMPT = "Введіть прізвище або телефон гостя, якого додати на «{title}»:"
ADD_PICK_GUEST = "Оберіть гостя 👇"
ADD_GUEST_BTN = "{name} · {phone}"
ADDED_OK = "✅ {name} доданий(а) на «{title}»."
ADD_CONFLICT = "⚠️ У гостя вже є запис на цей час: «{conflict}»."
ADD_ALREADY = "Гість вже записаний на «{title}»."
ADD_FULL_FORCED = "⚠️ Місць немає, але гостя додано понад ліміт (ручне додавання)."

# Manual cancel (from guest card)
CANCEL_BOOKING_BTN = "❌ Скасувати: {time} {title}"
CANCELLED_OK = "Запис скасовано."

# Attendance toggle feedback
ATT_MARKED = "Відмічено присутність: {name}"
ATT_UNMARKED = "Знято відмітку присутності: {name}"

# Export
EXPORT_MENU = "📊 <b>Експорт</b>\n\nОберіть, що експортувати 👇"
EXPORT_PARTICIPANTS_BTN = "👥 Списки учасників (по активностях)"
EXPORT_CONTACTS_BTN = "📇 Контакти всіх гостей"
EXPORT_GENERATING = "Готую файл… ⏳"
EXPORT_PARTICIPANTS_CAPTION = "Списки учасників — актуально на {stamp}"
EXPORT_CONTACTS_CAPTION = "Контакти гостей — актуально на {stamp}"

# Google Sheets
GSHEET_BTN = "🔗 Google Таблиця (онлайн)"
GSHEET_LINK = "🔗 <b>Жива таблиця Google</b>\n\nОновлюється автоматично:\n{url}"
GSHEET_UNAVAILABLE = (
    "Google Таблиця наразі недоступна. Перевірте налаштування "
    "(GSHEETS_ENABLED, файл облікових даних) або скористайтесь експортом у файл."
)
