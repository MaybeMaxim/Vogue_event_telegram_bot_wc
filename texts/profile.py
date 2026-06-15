"""
User-facing strings for the ⚙️ Профіль section (view + edit profile).
"""

PROFILE_VIEW = (
    "⚙️ <b>Ваш профіль</b>\n\n"
    "👤 Ім'я: {full_name}\n"
    "📱 Телефон: {phone}\n"
    "📧 Email: {email}\n\n"
    "Можете відредагувати будь-яке поле 👇"
)

EDIT_NAME_BUTTON = "✏️ Змінити ім'я"
EDIT_PHONE_BUTTON = "✏️ Змінити телефон"
EDIT_EMAIL_BUTTON = "✏️ Змінити email"
CLOSE_BUTTON = "✅ Готово"

ASK_NEW_NAME = "Введіть нове ім'я та прізвище у форматі «Прізвище Ім'я»:"
ASK_NEW_PHONE = "Введіть новий номер телефону у форматі +380XXXXXXXXX:"
ASK_NEW_EMAIL = "Введіть новий email:"

INVALID_NAME = (
    "Здається, це не схоже на ім'я та прізвище 🙂\n"
    "Введіть повне ім'я у форматі «Прізвище Ім'я», наприклад: Коваленко Олена"
)
INVALID_PHONE = "Це не схоже на номер телефону 📵\nВведіть у форматі +380XXXXXXXXX."
INVALID_EMAIL = "Це не схоже на email-адресу 📧\nНаприклад: example@gmail.com"

NAME_UPDATED = "✅ Ім'я оновлено."
PHONE_UPDATED = "✅ Номер телефону оновлено."
EMAIL_UPDATED = "✅ Email оновлено."

CLOSED = "✅ Профіль збережено. Якщо потрібно, ви завжди можете відредагувати дані в розділі «⚙️ Профіль»."

# Cancel an in-progress field edit.
CANCEL_EDIT_BUTTON = "❌ Скасувати"
EDIT_CANCELLED = "Редагування скасовано."
