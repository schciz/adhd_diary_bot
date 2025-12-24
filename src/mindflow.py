import datetime as dt
import logging

from sqlalchemy import func, select
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

import src.database as database
import src.tts as tts
from src.main_menu import *


async def handle_mindflow_menu(update, context):
    context.user_data["context"] = None

    user_id = update.effective_user.id

    total_notes = 0
    try:
        async with database.get_session() as session:
            result = await session.execute(
                select(func.count())
                .select_from(database.Mindflow)
                .where(database.Mindflow.user_id == user_id)
            )
            total_notes = result.scalar()

    except Exception as e:
        pass

    keyboard = [
        [KeyboardButton("Добавить 🖊 (M)"), KeyboardButton("Смотреть 👀 (M)")],
        [KeyboardButton("В главное меню 🫆")],
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Выбери действие в твоём MindFlow!",
        is_persistent=True,
    )

    await update.message.reply_text(
        "MindFlow - твой личный дневник мыслей! 📚\n"
        f"На данный момент у тебя {total_notes} записей 🫣",
        reply_markup=reply_markup,
    )


async def handle_mindflow_add(update, context):
    context.user_data["context"] = None

    keyboard = [[KeyboardButton("В главное меню 🫆")]]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Напиши о чём думаешь!",
        is_persistent=True,
    )

    await update.message.reply_text(
        "Напишите мысль которую хотите добавить 👀", reply_markup=reply_markup
    )

    context.user_data["context"] = "ENTERING_MINDFLOW"


async def handle_mindflow_adding(update, context):
    context.user_data["context"] = "ENTERING_MINDFLOW"

    user_id = update.effective_user.id
    last_modified = update.message.date.timestamp()

    try:
        notes = await tts.ensure_text_message(update, context)

    except Exception as e:
        return await update.message.reply_text(
            "Не удалось распознать голосовое... 😓\n" "Попробуй ещё раз!" f"\n\n{e}"
        )

    try:
        async with database.get_session() as session:
            mindflow = database.Mindflow(
                user_id=user_id, last_modified=last_modified, notes=notes
            )
            session.add(mindflow)

        await update.message.reply_text("Мысль успешно записана в MindFlow! 🎉")
        await handle_mindflow_menu(update, context)

    except Exception as e:
        await update.message.reply_text(
            "Что-то пошло не так... 😓\n" "Попробуй ещё раз!" f"\n\n{e}"
        )


async def handle_mindflow_show(update, context):
    context.user_data["context"] = None

    index = context.user_data.get("index", 0)
    user_id = update.effective_user.id

    notes = str()
    try:
        async with database.get_session() as session:
            result = await session.execute(
                select(database.Mindflow)
                .where(database.Mindflow.user_id == user_id)
                .offset(index)
                .limit(1)
            )
            mindflow = result.scalar_one_or_none()

            date_timestamp = mindflow.last_modified
            date_dt = dt.datetime.fromtimestamp(date_timestamp)
            date = date_dt.strftime("%d.%m.%Y %H:%M")

            notes = mindflow.notes

    except AttributeError:
        await update.message.reply_text(
            "В MindFlow пока что нет записей. Запишите сюда что-нибудь! 😅",
            reply_markup=ReplyKeyboardRemove(),
        )
        context.user_data["index"] = 0
        return await handle_mindflow_menu(update, context)

    except Exception as e:
        await update.message.reply_text(
            "Что-то пошло не так... 😓\n" "Попробуй ещё раз!" f"\n\n{e}"
        )
        context.user_data["index"] = 0
        return await handle_main_menu(update, context)

    keyboard = [
        [KeyboardButton("Назад ⬅️ (M)"), KeyboardButton("Вперёд ➡️ (M)")],
        [KeyboardButton("В начало ⬅️ (M)"), KeyboardButton("В конец ➡️ (M)")],
        [KeyboardButton("В главное меню 🫆")],
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Выбери вариантик!",
        is_persistent=True,
    )

    await update.message.reply_text(f"MindFlow, запись {index + 1}\n" f"Создана {date}")
    await update.message.reply_text(notes, reply_markup=reply_markup)


async def handle_mindflow_back(update, context):
    index = context.user_data.get("index", 0)
    user_id = update.effective_user.id

    try:
        async with database.get_session() as session:
            result = await session.execute(
                select(database.Mindflow)
                .where(database.Mindflow.user_id == user_id)
                .offset(index - 1)
                .limit(1)
            )
            previous_mindflow = result.scalar_one_or_none()
            if previous_mindflow and index - 1 >= 0:
                context.user_data["index"] = index - 1

    except Exception as e:
        pass

    finally:
        return await handle_mindflow_show(update, context)


async def handle_mindflow_forward(update, context):
    index = context.user_data.get("index", 0)
    user_id = update.effective_user.id

    try:
        async with database.get_session() as session:
            result = await session.execute(
                select(database.Mindflow)
                .where(database.Mindflow.user_id == user_id)
                .offset(index + 1)
                .limit(1)
            )
            next_mindflow = result.scalar_one_or_none()
            if next_mindflow:
                context.user_data["index"] = index + 1

    except Exception as e:
        pass

    finally:
        return await handle_mindflow_show(update, context)


async def handle_mindflow_begin(update, context):
    user_id = update.effective_user.id

    try:
        async with database.get_session() as session:
            result = await session.execute(
                select(database.Mindflow)
                .where(database.Mindflow.user_id == user_id)
                .offset(0)
                .limit(1)
            )
            previous_mindflow = result.scalar_one_or_none()
            if previous_mindflow:
                context.user_data["index"] = 0

    except Exception as e:
        pass

    finally:
        return await handle_mindflow_show(update, context)


async def handle_mindflow_end(update, context):
    user_id = update.effective_user.id

    try:
        async with database.get_session() as session:
            result = await session.execute(
                select(func.count())
                .select_from(database.Mindflow)
                .where(database.Mindflow.user_id == user_id)
            )
            index = result.scalar() - 1

            result = await session.execute(
                select(database.Mindflow)
                .where(database.Mindflow.user_id == user_id)
                .offset(index)
                .limit(1)
            )
            next_mindflow = result.scalar_one_or_none()
            if next_mindflow:
                context.user_data["index"] = index

    except Exception as e:
        pass

    finally:
        return await handle_mindflow_show(update, context)
