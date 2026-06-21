"""
User-facing strings for the 💬 Підтримка (support) section.
"""

SUPPORT_INTRO = (
    "💬 <b>Підтримка</b>\n\n"
    "Чим можемо допомогти? Оберіть один із варіантів 👇"
)

CONTACT_ORGANIZER_BUTTON = "📞 Зв'язок з організаторами"
SEND_MESSAGE_BUTTON = "✉️ Надіслати повідомлення"
ASK_SEXOLOGIST_BUTTON = "🌸 Запитати сексолога"
REPORT_BUG_BUTTON = "🐞 Повідомити про помилку"
BACK_BUTTON = "⬅️ Назад"
CLOSE_BUTTON = "✅ Закрити"
CANCEL_BUTTON = "❌ Скасувати"

# Contact organizer screen
CONTACT_ORGANIZER = (
    "📞 <b>Зв'язок з організаторами</b>\n\n"
    "Напишіть ваше запитання — представник організаторів зв'яжеться з вами.\n\n"
    "Для вирішення екстрених питань:\n"
    "<b>{contact}</b>"
)

# Write-to-organizer FSM prompt
ORG_MESSAGE_PROMPT = (
    "✉️ <b>Повідомлення організаторам</b>\n\n"
    "Напишіть ваше запитання або повідомлення — ми передамо його команді."
)
ORG_MESSAGE_SENT = (
    "✅ Дякуємо! Ми отримали ваше повідомлення і вже працюємо над його вирішенням."
)

# Report a bug/mistake flow
REPORT_BUG_PROMPT = (
    "🐞 <b>Повідомлення про помилку</b>\n\n"
    "Опишіть, будь ласка, що пішло не так — що ви робили і що сталося. "
    "Це допоможе нам швидко все виправити."
)
BUG_SENT = "✅ Дякуємо! Ми отримали ваше повідомлення і розберемось якнайшвидше."

# Shown if delivery failed (misconfiguration).
SUBMISSION_FAILED = "⚠️ Не вдалося надіслати повідомлення. Спробуйте, будь ласка, пізніше."

CANCELLED = "Скасовано."

# Forwarded to the support chat (not shown to the user).
FWD_BUG = "🐞 <b>Повідомлення про помилку</b>\nВід: {user} (id <code>{tg_id}</code>)\n\n{text}"
FWD_ORG = "✉️ <b>Повідомлення організаторам</b>\nВід: {user} (id <code>{tg_id}</code>)\n\n{text}"
