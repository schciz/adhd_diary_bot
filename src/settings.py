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
from src.main_menu import *


async def handle_settings_menu(update, context):
    context.user_data["context"] = None

    keyboard = [
        [KeyboardButton("SaluteSpeech 🎉")],
        [KeyboardButton("В главное меню 🫆")],
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Что настроим? 👀",
        is_persistent=True,
    )

    await update.message.reply_text(
        "Что будем настраивать? 👾",
        reply_markup=reply_markup,
    )


async def handle_salute_speech(update, context):
    context.user_data["context"] = None

    keyboard = [
        [KeyboardButton("В главное меню 🫆")],
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Напиши токен!",
        is_persistent=True,
    )

    await update.message.reply_text(
        "Напиши SaluteSpeech API Token",
        reply_markup=reply_markup,
    )

    context.user_data["context"] = "ENTERING_SALUTE_SPEECH_TOKEN"


async def handle_salute_speech_entering(update, context):
    context.user_data["context"] = "ENTERING_SALUTE_SPEECH_TOKEN"

    if not update.message:
        return await update.message.reply_text(
            "Токен задан неверно!\n" "Попробуйте ещё раз!"
        )

    user_id = update.effective_user.id
    salute_speech = update.message.text

    try:
        async with database.get_session() as session:
            result = await session.execute(
                select(database.Setting)
                .where(database.Setting.user_id == user_id)
                .limit(1)
            )

            setting = result.scalar_one_or_none()
            if not setting:
                setting = database.Setting(user_id=user_id, salute_speech=salute_speech)

                session.add(setting)

            setting.salute_speech = salute_speech

        await update.message.reply_text("SaluteSpeech Token успешно записан! 🎉")
        await handle_settings_menu(update, context)

    except Exception as e:
        await update.message.reply_text(
            "Что-то пошло не так... 😓\n" "Попробуй ещё раз!" f"\n\n{e}"
        )
