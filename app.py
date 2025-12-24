import logging
import re
import os

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
from src.main_menu import *
from src.mindflow import *
from src.reflection import *
from src.reminders import *
from src.settings import *

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG
)
logging.getLogger("httpx").setLevel(logging.WARNING)


async def start_command(update, context):
    await update.message.reply_text("Привет! 🍓")
    return await handle_main_menu(update, context)


async def handle_messages(update, context):
    user_context = context.user_data.get("context", None)

    if user_context == "ENTERING_MINDFLOW":
        return await handle_mindflow_adding(update, context)

    elif user_context == "ENTERING_REFLECTION_TIME_SPENT":
        return await handle_reflection_time_spent(update, context)
    elif user_context == "ENTERING_REFLECTION_INTERRUPT":
        return await handle_reflection_interrupt(update, context)

    elif user_context == "ENTERING_REMINDER_SCHEDULED_AT":
        return await handle_reminders_scheduled_at(update, context)
    elif user_context == "ENTERING_REMINDER_HEADER":
        return await handle_reminders_header(update, context)

    elif user_context == "ENTERING_SALUTE_SPEECH_TOKEN":
        return await handle_salute_speech_entering(update, context)

    else:
        return await update.message.reply_text(
            "Что-то непонятное... 😴\n" "Попробуй ещё раз!"
        )


async def post_init(application):
    await database.init()


if __name__ == "__main__":
    api_token = os.getenv("API_TOKEN")

    application = (
        ApplicationBuilder()
        .token(api_token)
        .post_init(post_init)
        .build()
    )

    start_command_handler = CommandHandler("start", start_command)
    application.add_handler(start_command_handler)

    # MindFlow
    application.add_handler(
        MessageHandler(filters.Regex(re.compile(r"^MindFlow 🗒$")), handle_mindflow_menu)
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"^Добавить 🖊 \(M\)$")), handle_mindflow_add
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"^Смотреть 👀 \(M\)$")), handle_mindflow_show
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"^Назад ⬅️ \(M\)$")), handle_mindflow_back
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"^Вперёд ➡️ \(M\)$")), handle_mindflow_forward
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"^В начало ⬅️ \(M\)$")), handle_mindflow_begin
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"^В конец ➡️ \(M\)$")), handle_mindflow_end
        )
    )

    # Reflection
    application.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"^Reflection 💤$")), handle_reflection_menu
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"^Добавить 🖊 \(R\)$")), handle_reflection_add
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"^Смотреть 👀 \(R\)$")), handle_reflection_show
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"^Назад ⬅️ \(R\)$")), handle_reflection_back
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"^Вперёд ➡️ \(R\)$")), handle_reflection_forward
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"^В начало ⬅️ \(R\)$")), handle_reflection_begin
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"^В конец ➡️ \(R\)$")), handle_reflection_end
        )
    )

    # Напоминания
    application.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"^Напоминания 📌$")), handle_reminders_menu
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"^Добавить 🖊 \(Н\)$")), handle_reminders_add
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"^Смотреть 👀 \(Н\)$")), handle_reminders_show
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"^Назад ⬅️ \(Н\)$")), handle_reminders_back
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"^Вперёд ➡️ \(Н\)$")), handle_reminders_forward
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"^В начало ⬅️ \(Н\)$")), handle_reminders_begin
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"^В конец ➡️ \(Н\)$")), handle_reminders_end
        )
    )

    # Настройки
    application.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"^Настройки ⚙️$")), handle_settings_menu
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"^SaluteSpeech 🎉$")), handle_salute_speech
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"^В главное меню 🫆$")), handle_main_menu
        )
    )
    application.add_handler(
        MessageHandler(
            (filters.TEXT & ~filters.COMMAND) | filters.VOICE, handle_messages
        )
    )

    application.run_polling()
