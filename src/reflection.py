import datetime as dt
import logging

import pandas as pd
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
from src.main_menu import *


async def handle_reflection_menu(update, context):
    context.user_data["context"] = None

    user_id = update.effective_user.id

    total_hyperfocuses = 0
    positive_hyperfocuses = 0
    try:
        df = await database.load_to_df(select(database.Reflection))
        df = df[df["user_id"] == user_id]
        total_hyperfocuses = len(df)
        positive_hyperfocuses = len(df[df["is_interrupt_successfull"] == True])

    except Exception as e:
        pass

    keyboard = [
        [KeyboardButton("Добавить 🖊 (R)"), KeyboardButton("Смотреть 👀 (R)")],
        [KeyboardButton("В главное меню 🫆")],
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Выбери действие в Reflection!",
        is_persistent=True,
    )

    await update.message.reply_text(
        "Reflection - твой способ отслеживать залипания! ✌️\n"
        f"На данный момент отслежено {total_hyperfocuses} залипаний 🫣, из них {positive_hyperfocuses} - положительные 👀",
        reply_markup=reply_markup,
    )


async def handle_reflection_add(update, context):
    context.user_data["context"] = None

    keyboard = [
        [
            KeyboardButton("Быстро ⌛️\n(<= 2 ч.)"),
            KeyboardButton("Средне 🕰\n(<= 6 ч.)"),
            KeyboardButton("Долго ♾️\n(<= 12 ч.)"),
        ],
        [KeyboardButton("В главное меню 🫆")],
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Напиши длительность залипания!",
        is_persistent=True,
    )

    await update.message.reply_text(
        "Напишите длительность залипания 👀", reply_markup=reply_markup
    )

    context.user_data["context"] = "ENTERING_REFLECTION_TIME_SPENT"


async def handle_reflection_time_spent(update, context):
    context.user_data["context"] = "ENTERING_REFLECTION_TIME_SPENT"

    time_spent = update.message.text
    if time_spent not in [
        "Быстро ⌛️\n(<= 2 ч.)",
        "Средне 🕰\n(<= 6 ч.)",
        "Долго ♾️\n(<= 12 ч.)",
    ]:
        return await update.message.reply_text(
            "Время залипания задано неправильно(\n" "Попробуйте ещё раз!"
        )
    elif time_spent == "Быстро ⌛️\n(<= 2 ч.)":
        time_spent_int = 0
    elif time_spent == "Средне 🕰\n(<= 6 ч.)":
        time_spent_int = 1
    elif time_spent == "Долго ♾️\n(<= 12 ч.)":
        time_spent_int = 2
    context.user_data["time_spent"] = time_spent_int

    keyboard = [
        [KeyboardButton("Нет 😒"), KeyboardButton("Да 😎")],
        [KeyboardButton("В главное меню 🫆")],
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Удалось?",
        is_persistent=True,
    )

    await update.message.reply_text(
        "Удалось ли прервать залипание? 🐇", reply_markup=reply_markup
    )

    context.user_data["context"] = "ENTERING_REFLECTION_INTERRUPT"


async def handle_reflection_interrupt(update, context):
    context.user_data["context"] = "ENTERING_REFLECTION_INTERRUPT"

    interrupt = update.message.text
    if interrupt not in ["Нет 😒", "Да 😎"]:
        return await update.message.reply_text(
            "Успешность прерывания задана неправильно(\n" "Попробуйте ещё раз!"
        )
    elif interrupt == "Нет 😒":
        successfull = False
    elif interrupt == "Да 😎":
        successfull = True

    user_id = update.effective_user.id
    last_modified = update.message.date.timestamp()
    time_spent = context.user_data["time_spent"]
    is_interrupt_successfull = successfull

    try:
        async with database.get_session() as session:
            reflection = database.Reflection(
                user_id=user_id,
                last_modified=last_modified,
                time_spent=time_spent,
                is_interrupt_successfull=is_interrupt_successfull,
            )
            session.add(reflection)

        await update.message.reply_text("Залипание успешно записано в Reflection! 🎉")
        await handle_reflection_menu(update, context)

    except Exception as e:
        await update.message.reply_text(
            "Что-то пошло не так... 😓\n" "Попробуй ещё раз!" f"\n\n{e}"
        )


async def handle_reflection_show(update, context):
    context.user_data["context"] = None

    index = context.user_data.get("index", 0)
    user_id = update.effective_user.id

    notes = str()
    try:
        async with database.get_session() as session:
            result = await session.execute(
                select(database.Reflection)
                .where(database.Reflection.user_id == user_id)
                .offset(index)
                .limit(1)
            )
            reflection = result.scalar_one_or_none()

            date_timestamp = reflection.last_modified
            date_dt = dt.datetime.fromtimestamp(date_timestamp)
            date = date_dt.strftime("%d.%m.%Y %H:%M")

            successfull = "нет :("
            if reflection.is_interrupt_successfull:
                successfull = "да :)"

    except AttributeError:
        await update.message.reply_text(
            "В Reflection пока что нет залипаний. Запишите сюда что-нибудь! 😅",
            reply_markup=ReplyKeyboardRemove(),
        )
        context.user_data["index"] = 0
        return await handle_reflection_menu(update, context)

    except Exception as e:
        await update.message.reply_text(
            "Что-то пошло не так... 😓\n" "Попробуй ещё раз!" f"\n\n{e}"
        )
        context.user_data["index"] = 0
        return await handle_main_menu(update, context)

    keyboard = [
        [KeyboardButton("Назад ⬅️ (R)"), KeyboardButton("Вперёд ➡️ (R)")],
        [KeyboardButton("В начало ⬅️ (R)"), KeyboardButton("В конец ➡️ (R)")],
        [KeyboardButton("В главное меню 🫆")],
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Выбери вариантик!",
        is_persistent=True,
    )

    await update.message.reply_text(
        f"Reflection, залипание {index + 1}\n"
        f"Создано {date}\n"
        f"Удалось ли прервать: {successfull}",
        reply_markup=reply_markup,
    )


async def handle_reflection_back(update, context):
    index = context.user_data.get("index", 0)
    user_id = update.effective_user.id

    try:
        async with database.get_session() as session:
            result = await session.execute(
                select(database.Reflection)
                .where(database.Reflection.user_id == user_id)
                .offset(index - 1)
                .limit(1)
            )
            previous_reflection = result.scalar_one_or_none()
            if previous_reflection and index - 1 >= 0:
                context.user_data["index"] = index - 1

    except Exception as e:
        pass

    finally:
        return await handle_reflection_show(update, context)


async def handle_reflection_forward(update, context):
    index = context.user_data.get("index", 0)
    user_id = update.effective_user.id

    try:
        async with database.get_session() as session:
            result = await session.execute(
                select(database.Reflection)
                .where(database.Reflection.user_id == user_id)
                .offset(index + 1)
                .limit(1)
            )
            next_reflection = result.scalar_one_or_none()
            if next_reflection:
                context.user_data["index"] = index + 1

    except Exception as e:
        pass

    finally:
        return await handle_reflection_show(update, context)


async def handle_reflection_begin(update, context):
    user_id = update.effective_user.id

    try:
        async with database.get_session() as session:
            result = await session.execute(
                select(database.Reflection)
                .where(database.Reflection.user_id == user_id)
                .offset(0)
                .limit(1)
            )
            previous_reflection = result.scalar_one_or_none()
            if previous_reflection:
                context.user_data["index"] = 0

    except Exception as e:
        pass

    finally:
        return await handle_reflection_show(update, context)


async def handle_reflection_end(update, context):
    user_id = update.effective_user.id

    try:
        async with database.get_session() as session:
            result = await session.execute(
                select(func.count())
                .select_from(database.Reflection)
                .where(database.Reflection.user_id == user_id)
            )
            index = result.scalar() - 1

            result = await session.execute(
                select(database.Reflection)
                .where(database.Reflection.user_id == user_id)
                .offset(index)
                .limit(1)
            )
            next_reflection = result.scalar_one_or_none()
            if next_reflection:
                context.user_data["index"] = index

    except Exception as e:
        pass

    finally:
        return await handle_reflection_show(update, context)
