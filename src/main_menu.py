import logging

from sqlalchemy import func, select
from telegram import KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

import src.database as database


async def handle_main_menu(update, context):
    context.user_data["context"] = None
    context.user_data["index"] = 0

    keyboard = [
        [KeyboardButton("MindFlow 🗒"), KeyboardButton("Reflection 💤")],
        [KeyboardButton("Напоминания 📌")],
        [KeyboardButton("Настройки ⚙️")],
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Куда пойдём? 👀",
        is_persistent=True,
    )

    await update.message.reply_text(
        "Это главное меню твоего СДВГ дневника! 👾",
        reply_markup=reply_markup,
    )

    try:
        await remove_expired_reminders(update, context)

    except Exception:
        pass
