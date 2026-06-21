"""
User-facing strings for the booking drill-down ("✍️ Записатись").

ParseMode.HTML is active; dynamic DB text is html.escape()d in
services.booking_service before insertion here.
"""

# Step 1 — day picker
BOOK_INTRO = "Оберіть день 👇"

# Step 2 — category picker
CATEGORY_PICKER_INTRO = "✍️ <b>День {day} ({date})</b>\n\nОберіть активність для запису 👇"

# Step 3 — sub-slot picker
SUBSLOT_PICK_TIME_PROMPT = "Оберіть зручний час 👇"
SUBSLOT_SINGLE_PROMPT = "Натисніть кнопку нижче, щоб записатись 👇"
SUBSLOT_OPENS_AT = "Запис відкривається о {time}"

# Buttons
BACK_TO_CATEGORIES_BUTTON = "⬅️ Назад до активностей"
BACK_TO_DAYS_BUTTON = "⬅️ Обрати інший день"

# Consultation slot button (leads into the per-slot consultation picker)
CONSULTATION_SLOT_BUTTON = "🩺 {time_range} · Консультації Анни Баринової"

# --- Consultation slot picker ---------------------------------------------
CONSULTATION_PICKER_HEADER = (
    "<b>Консультація Анни Баринової</b>\n\n"
    "Оберіть вільний час для індивідуальної консультації 👇"
)
CONSULTATION_SLOT_FREE = "🟢 {time}"
CONSULTATION_SLOT_TAKEN = "🔴 {time} — зайнято (черга очікування →)"
CONSULTATION_NONE_FREE = (
    "🩺 <b>Консультації Анни Баринової</b>\n\n"
    "На жаль, усі слоти наразі зайняті. "
    "Ви можете приєднатись до листа очікування на конкретний час."
)

# --- Booking confirmation card --------------------------------------------
CONFIRM_BOOKING = (
    "Підтвердьте запис 👇\n\n"
    "🗓 <b>{title}</b>\n"
    "🕒 {time_range}\n\n"
    "Ваші дані:\n"
    "👤 {full_name}\n"
    "📱 {phone}\n\n"
    "Все вірно?"
)
CONFIRM_BUTTON = "✅ Підтвердити запис"
CONFIRM_EDIT_DATA_BUTTON = "✏️ Змінити мої дані"
CONFIRM_CANCEL_BUTTON = "⬅️ Назад"
# After a successful booking — return to the same day's slot list to book more.
BACK_TO_DAY_BUTTON = "⬅️ Повернутись до Дня {day}"

# --- Booking outcome messages ---------------------------------------------
BOOKED_OK = (
    "✅ Готово! Вас записано:\n\n"
    "🗓 <b>{title}</b>\n"
    "🕒 {time_range}"
)
ALREADY_BOOKED = "Ви вже записані на «{title}» 🙂"
CONFLICT_FOUND = (
    "⚠️ На цей час у вас вже є запис:\n\n"
    "🗓 <b>{conflict_title}</b>\n"
    "🕒 {conflict_time}\n\n"
    "Не можна бути у двох місцях одночасно."
)
EXCLUSIVE_GROUP_CONFLICT_FOUND = (
    "⚠️ Ви вже записані на цей захід:\n\n"
    "🗓 <b>{conflict_title}</b>\n"
    "🕒 {conflict_time}\n\n"
    "Щоб змінити слот, скасуйте попередній запис."
)
CONSULTATION_CONFLICT_FOUND = (
    "⚠️ Ви вже записані на консультацію Анни Баринової:\n\n"
    "🗓 <b>{conflict_title}</b>\n\n"
    "Можна мати лише одну консультацію. "
    "Скасуйте поточний запис, якщо хочете обрати інший час."
)
BOOKED_OK_WAITLIST_DROPPED = (
    "✅ Готово! Вас записано:\n\n"
    "🗓 <b>{title}</b>\n"
    "🕒 {time_range}\n\n"
    "ℹ️ Ваше місце в черзі очікування на «{dropped_title}» було автоматично скасовано, "
    "оскільки можна мати лише одну консультацію."
)
WAITLIST_CONSULTATION_CONFLICT = (
    "⚠️ Ви вже перебуваєте в черзі очікування на іншу консультацію Анни Баринової. "
    "Можна чекати лише на одну консультацію одночасно."
)
WAITLIST_OFFER_CONFIRMED_SWAPPED = (
    "✅ Чудово! Вас записано на «{title}».\n"
    "🕒 {time_range}\n\n"
    "Запис на «{swapped_title}» скасовано автоматично."
)
CONFLICT_CANCEL_BUTTON = "❌ Скасувати «{conflict_title}»"
ACTIVITY_FULL_OFFER_WAITLIST = (
    "😔 На жаль, місць на «{title}» вже немає.\n\n"
    "Хочете приєднатись до листа очікування? Якщо місце звільниться, "
    "ми одразу повідомимо вас."
)
JOIN_WAITLIST_BUTTON = "🔔 Так, у лист очікування"
BOOKING_NOT_FOUND = "Не вдалося знайти цю активність. Спробуйте ще раз."

# --- Waitlist outcome messages --------------------------------------------
WAITLIST_JOINED = (
    "🔔 Вас додано до листа очікування на «{title}».\n"
    "Ваша позиція в черзі: <b>{position}</b>.\n\n"
    "Щойно звільниться місце, ми надішлемо вам запрошення підтвердити запис."
)
WAITLIST_ALREADY = "Ви вже у листі очікування на «{title}» 🙂"
WAITLIST_SEAT_AVAILABLE = "Гарні новини — місце звільнилося! Спробуйте записатись ще раз."

# --- Waitlist promotion (offer) notification ------------------------------
WAITLIST_OFFER = (
    "🎉 Звільнилося місце на «{title}»!\n"
    "🕒 {time_range}\n\n"
    "Підтвердьте, будь ласка, протягом {minutes} хв, інакше місце "
    "перейде наступному в черзі."
)
WAITLIST_OFFER_CONFLICT_WARNING = (
    "\n\n⚠️ Якщо ви підтвердите, ваш поточний запис на «{conflict_title}» "
    "(🕒 {conflict_time}) буде автоматично скасовано."
)
WAITLIST_OFFER_CONFIRM_BUTTON = "✅ Підтвердити запис"
WAITLIST_OFFER_DECLINE_BUTTON = "❌ Відмовитись"
WAITLIST_OFFER_CONFIRMED = (
    "✅ Чудово! Вас записано на «{title}». Деталі — у «📋 Мої записи»."
)
WAITLIST_OFFER_DECLINED = "Зрозуміло, місце передамо наступному. Дякуємо!"
WAITLIST_OFFER_EXPIRED = "На жаль, час підтвердження минув, і місце вже передано далі."
WAITLIST_OFFER_TAKEN = "На жаль, місце вже зайняте."

# Placeholder kept for any not-yet-wired callbacks.
BOOKING_COMING_SOON = "🚧 Ця дія буде доступна найближчим часом."

EVENT_ALREADY_STARTED = "❌ Захід вже розпочався — запис закрито."

# --- Time-driven notifications (ticker) -----------------------------------

# T-30 min: free-seat broadcast to non-booked users (sent alongside booked-user reminders).
REMINDER_FREE_SEATS = (
    "🟡 <b>Починається за 30 хвилин!</b>\n\n"
    "🗓 <b>{title}</b>\n"
    "🕒 {time_range}\n"
    "📍 {location}\n\n"
    "Ще є вільні місця — запишіться у «✍️ Записатись» ⚡️"
)

# T-30 min: reminder + confirmation request for a single activity.
REMINDER = (
    "⏰ <b>Нагадування!</b> До початку 30 хвилин.\n\n"
    "🗓 <b>{title}</b>\n"
    "🕒 {time_range}\n"
    "📍 {location}\n\n"
    "Будь ласка, підтвердіть участь протягом 15 хвилин.\n\n"
    "У разі відсутності підтвердження місце буде передано гостям із листа очікування."
)

# T-30 min: reminder when multiple activities start at the same time.
REMINDER_MULTI_HEADER = "⏰ <b>Нагадування!</b> О {time} починаються активності, на які ви записались:\n"
REMINDER_MULTI_ENTRY = "\n🗓 <b>{title}</b>\n📍 {location}"
REMINDER_MULTI_FOOTER = "\n\nБудь ласка, підтвердіть участь протягом 15 хвилин.\n\nУ разі відсутності підтвердження місця будуть передані гостям із листа очікування."

# T-15 min: confirmation request.
CONFIRMATION_REQUEST = (
    "⏰ До початку 30 хвилин:\n\n"
    "🗓 <b>{title}</b>\n"
    "🕒 {time_range}\n"
    "📍 {location}\n\n"
    "Підтвердьте, будь ласка, що будете — у вас є 15 хвилин, інакше місце звільниться для інших."
)

# T-10 min: free seat broadcast to all users.
FREE_SEAT_BROADCAST = (
    "🟢 <b>З'явилось вільне місце!</b>\n\n"
    "🗓 <b>{title}</b>\n"
    "🕒 {time_range}\n"
    "📍 {location}\n\n"
    "Починається за 10 хвилин! Запишіться у розділі «✍️ Записатись» ⚡️"
)

# At booking_opens_at: broadcast to all users (consultation booking just opened + PUBLIC TALK started).
OPENS_BROADCAST = (
    "🎤 Щойно розпочався <b>PUBLIC TALK: Секрети збереження молодості й новації пластичної хірургії</b>\n"
    "Спікерка: Анна Баринова\n"
    "📍 Лекторій, 5 поверх\n\n"
    "🗓 Також щойно відкрився запис на <b>індивідуальні консультації Анни Баринової</b>!\n"
    "Перейдіть у «✍️ Записатись» → День 1."
)
CONFIRM_ATTENDANCE_BUTTON = "✅ Підтвердити участь"
CANT_MAKE_BUTTON = "❌ Скасувати бронювання"

ATTENDANCE_CONFIRMED = "✅ Дякуємо! Чекаємо на вас 🙂"
ATTENDANCE_DECLINED = "Зрозуміло, дякуємо що попередили. Місце передамо іншим."
ATTENDANCE_EXPIRED = "На жаль, час підтвердження минув."

NO_SHOW_RELEASED = (
    "⌛️ Ви не підтвердили участь, тож місце на «{title}» звільнено.\n"
    "Якщо плани змінились — можете записатись знову, якщо є вільні місця."
)

BOOKING_ABORTED = "Скасовано."
EDIT_DATA_PROMPT = "Оновіть дані в профілі, а потім поверніться до запису 🙂"
CONFLICT_CANCELLED_TRY_AGAIN_BUTTON = "✍️ Записатись тепер"
CONFLICT_CANCELLED = "Попередній запис скасовано. Тепер можете обрати інший варіант 🙂"
WAITLIST_JOINED_WITH_CONFLICT = (
    "🔔 Вас додано до листа очікування на «{title}».\n"
    "Ваша позиція в черзі: <b>{position}</b>.\n\n"
    "⚠️ Якщо місце звільниться, ваш поточний запис на «{conflict_title}» буде автоматично скасовано."
)

NO_ACTIVITIES_FOR_DAY = "На цей день активностей не знайдено."
ALL_ACTIVITIES_STARTED = "Усі заходи цього дня вже розпочались. Записів більше немає."
BOOKING_NOT_OPEN_YET = "⏳ Запис відкривається о <b>{opens_at}</b>."
