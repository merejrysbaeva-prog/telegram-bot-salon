import os
import sqlite3
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# =======================
# TOKEN
# =======================
TOKEN = os.getenv("TOKEN")
print("TOKEN =", TOKEN)


# =======================
# FONT
# =======================
pdfmetrics.registerFont(TTFont("DejaVu", "DejaVuSans.ttf"))


# =======================
# DB
# =======================
conn = sqlite3.connect("salon.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    role TEXT
)
""")
conn.commit()


def set_role(user_id, role):
    cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (user_id, role))
    conn.commit()


def get_role(user_id):
    cursor.execute("SELECT role FROM users WHERE user_id=?", (user_id,))
    r = cursor.fetchone()
    return r[0] if r else None


# =======================
# KEYBOARDS
# =======================
def role_keyboard():
    return ReplyKeyboardMarkup(
        [["💅 Маникюр", "💇 Парикмахер"],
         ["💄 Визажист", "👩‍💼 Админ"]],
        resize_keyboard=True
    )


def menu():
    return ReplyKeyboardMarkup(
        [["📋 Чек-лист"],
         ["📄 Регламент PDF"],
         ["📄 Должностная инструкция PDF"]],
        resize_keyboard=True
    )


def checklist_menu():
    return ReplyKeyboardMarkup(
        [["1. Подготовка к рабочему дню"],
         ["2. Открытие"],
         ["3. Работа в течение дня"],
         ["4. Взаимодействие с персоналом"],
         ["5. Обратная связь"],
         ["6. Закрытие"],
         ["🏠 Домой"]],
        resize_keyboard=True
    )


def nav_menu():
    return ReplyKeyboardMarkup(
        [["🏠 Домой", "🔙 Назад"]],
        resize_keyboard=True
    )


# =======================
# CHECKLIST
# =======================
CHECKLIST = {
    "1. Подготовка к рабочему дню": "Подготовка к рабочему дню ...",
    "2. Открытие": "Открытие ...",
    "3. Работа в течение дня": "Работа в течение дня ...",
    "4. Взаимодействие с персоналом": "Взаимодействие с персоналом ...",
    "5. Обратная связь": "Обратная связь ...",
    "6. Закрытие": "Закрытие ..."
}


# =======================
# PDF
# =======================
def make_pdf(filename, text):
    c = canvas.Canvas(filename)
    width, height = 595, 842

    x = 40
    y = height - 40
    line_height = 12

    c.setFont("DejaVu", 9)

    for line in text.split("\n"):
        if y < 40:
            c.showPage()
            c.setFont("DejaVu", 9)
            y = height - 40

        c.drawString(x, y, line)
        y -= line_height

    c.save()
    return filename


# =======================
# TEXTS
# =======================
REGULATION_TEXT = "📄 РЕГЛАМЕНТ АДМИНИСТРАТОРА (доступ только админу)"
JOB_TEXT = "📄 ДОЛЖНОСТНАЯ ИНСТРУКЦИЯ (для остальных ролей)"


# =======================
# START
# =======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выбери роль:", reply_markup=role_keyboard())


# =======================
# HANDLER
# =======================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    # роли
    if text in ["💅 Маникюр", "💇 Парикмахер", "💄 Визажист", "👩‍💼 Админ"]:
        set_role(user_id, text)
        await update.message.reply_text("Роль сохранена", reply_markup=menu())

    # чек-лист
    elif text == "📋 Чек-лист":
        await update.message.reply_text("Выбери раздел:", reply_markup=checklist_menu())

    elif text in CHECKLIST:
        await update.message.reply_text(CHECKLIST[text], reply_markup=nav_menu())

    # домой
    elif text == "🏠 Домой":
        await update.message.reply_text("Главное меню:", reply_markup=menu())

    # назад
    elif text == "🔙 Назад":
        await update.message.reply_text("Чек-лист:", reply_markup=checklist_menu())

    # регламент (ТОЛЬКО админ)
    elif text == "📄 Регламент PDF":
        role = get_role(user_id)

        if role != "👩‍💼 Админ":
            await update.message.reply_text("⛔ Доступ только для администратора")
            return

        file = make_pdf("reglament.pdf", REGULATION_TEXT)
        await update.message.reply_document(open(file, "rb"))

    # должностная (ВСЕ КРОМЕ админа)
    elif text == "📄 Должностная инструкция PDF":
        role = get_role(user_id)

        if role == "👩‍💼 Админ":
            await update.message.reply_text("⛔ Этот документ только для персонала")
            return

        file = make_pdf("dolzhnost_admin.pdf", JOB_TEXT)
        await update.message.reply_document(open(file, "rb"))

    else:
        await update.message.reply_text("Используй кнопки")


# =======================
# RUN
# =======================
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

if __name__ == "__main__":
    app.run_polling(drop_pending_updates=True)