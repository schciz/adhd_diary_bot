import datetime as dt
import logging
import uuid

import pandas as pd
from sqlalchemy import delete, func, select
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


async def handle_reminders_menu(update, context):
    context.user_data["context"] = None

    user_id = update.effective_user.id

    total_reminders = 0
    try:
        await remove_expired_reminders(update, context)

        async with database.get_session() as session:
            result = await session.execute(
                select(func.count())
                .select_from(database.Reminder)
                .where(database.Reminder.user_id == user_id)
            )
            total_reminders = result.scalar()

    except Exception as e:
        pass

    keyboard = [
        [KeyboardButton("Добавить 🖊 (Н)"), KeyboardButton("Смотреть 👀 (Н)")],
        [KeyboardButton("В главное меню 🫆")],
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Напоминания!",
        is_persistent=True,
    )

    await update.message.reply_text(
        "Напоминания - разгрузи свою рабочую память! 🤌\n"
        f"На данный момент записано {total_reminders} напоминаний 📌",
        reply_markup=reply_markup,
    )


async def handle_reminders_add(update, context):
    context.user_data["context"] = None

    keyboard = [
        [
            KeyboardButton("5 минут ⌚️"),
            KeyboardButton("15 минут ⌚️"),
            KeyboardButton("30 минут ⌚️"),
        ],
        [
            KeyboardButton("1 час 🕰"),
            KeyboardButton("2 часа 🕰"),
            KeyboardButton("3 часа 🕰"),
        ],
        [
            KeyboardButton("1 день 🎈"),
            KeyboardButton("2 дня 🎈"),
            KeyboardButton("3 дня 🎈"),
        ],
        [KeyboardButton("В главное меню 🫆")],
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Через сколько напомнить?",
        is_persistent=True,
    )

    await update.message.reply_text(
        "Через сколько тебе напомнить? 🤔", reply_markup=reply_markup
    )

    context.user_data["context"] = "ENTERING_REMINDER_SCHEDULED_AT"


async def handle_reminders_scheduled_at(update, context):
    context.user_data["context"] = "ENTERING_REMINDER_SCHEDULED_AT"

    due = update.message.date
    scheduled_at = update.message.text
    if scheduled_at == "5 минут ⌚️":
        due += dt.timedelta(minutes=5)
    elif scheduled_at == "15 минут ⌚️":
        due += dt.timedelta(minutes=15)
    elif scheduled_at == "30 минут ⌚️":
        due += dt.timedelta(minutes=30)
    elif scheduled_at == "1 час 🕰":
        due += dt.timedelta(hours=1)
    elif scheduled_at == "2 часа 🕰":
        due += dt.timedelta(hours=2)
    elif scheduled_at == "3 часа 🕰":
        due += dt.timedelta(hours=3)
    elif scheduled_at == "1 день 🎈":
        due += dt.timedelta(days=1)
    elif scheduled_at == "2 дня 🎈":
        due += dt.timedelta(days=2)
    elif scheduled_at == "3 дня 🎈":
        due += dt.timedelta(days=3)
    else:
        return await update.message.reply_text(
            "Время задано неправильно(\n" "Попробуйте ещё раз!"
        )

    context.user_data["due"] = due

    keyboard = [
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
        "Название напоминания? 🐇", reply_markup=ReplyKeyboardRemove()
    )

    context.user_data["context"] = "ENTERING_REMINDER_HEADER"


async def handle_reminders_header(update, context):
    context.user_data["context"] = "ENTERING_REMINDER_HEADER"

    user_id = update.effective_user.id
    chat_id = update.effective_message.chat_id
    last_modified = update.message.date.timestamp()
    scheduled_at = context.user_data["due"].timestamp()

    try:
        header = await tts.ensure_text_message(update, context)

    except Exception as e:
        return await update.message.reply_text(
            "Не удалось распознать голосовое... 😓\n" "Попробуй ещё раз!" f"\n\n{e}"
        )

    try:
        async with database.get_session() as session:
            reminder = database.Reminder(
                user_id=user_id,
                id=str(uuid.uuid4()),
                chat_id=chat_id,
                last_modified=last_modified,
                scheduled_at=scheduled_at,
                header=header,
            )
            session.add(reminder)

            context.job_queue.run_once(
                handle_reminder,
                context.user_data["due"],
                user_id=user_id,
                chat_id=chat_id,
                data=reminder.id,
            )

        await update.message.reply_text("Напоминание успешно составлено!")
        await handle_reminders_menu(update, context)

    except Exception as e:
        await update.message.reply_text(
            "Что-то пошло не так... 😓\n" "Попробуй ещё раз!" f"\n\n{e}"
        )


async def handle_reminder(context):
    try:
        job = context.job
        reminder_id = job.data

        async with database.get_session() as session:
            result = await session.execute(
                select(database.Reminder)
                .where(database.Reminder.id == reminder_id)
                .limit(1)
            )
            reminder = result.scalar_one_or_none()

            chat_id = reminder.chat_id
            header = reminder.header

            await context.bot.send_message(chat_id, text=f"Напоминание: {header} 📌")

            await session.execute(
                delete(database.Reminder).where(database.Reminder.id == reminder_id)
            )

    except Exception as e:
        pass


async def remove_expired_reminders(update, context):
    async with database.get_session() as session:
        await session.execute(
            delete(database.Reminder).where(
                database.Reminder.scheduled_at < update.message.date.timestamp()
            )
        )


async def handle_reminders_show(update, context):
    context.user_data["context"] = None

    index = context.user_data.get("index", 0)
    user_id = update.effective_user.id

    notes = str()
    try:
        async with database.get_session() as session:
            result = await session.execute(
                select(database.Reminder)
                .where(database.Reminder.user_id == user_id)
                .offset(index)
                .limit(1)
            )
            reminder = result.scalar_one_or_none()

            date_timestamp = reminder.last_modified
            date_dt = dt.datetime.fromtimestamp(date_timestamp)
            date = date_dt.strftime("%d.%m.%Y %H:%M")

            due_timestamp = reminder.scheduled_at
            due_dt = dt.datetime.fromtimestamp(due_timestamp)
            due_date = due_dt.strftime("%d.%m.%Y %H:%M")

            header = reminder.header

    except AttributeError:
        await update.message.reply_text(
            "Напоминаний пока что нет. Запишите сюда что-нибудь! 😅",
            reply_markup=ReplyKeyboardRemove(),
        )
        context.user_data["index"] = 0
        return await handle_reminders_menu(update, context)

    except Exception as e:
        await update.message.reply_text(
            "Что-то пошло не так... 😓\n" "Попробуй ещё раз!" f"\n\n{e}"
        )
        context.user_data["index"] = 0
        return await handle_main_menu(update, context)

    keyboard = [
        [KeyboardButton("Назад ⬅️ (Н)"), KeyboardButton("Вперёд ➡️ (Н)")],
        [KeyboardButton("В начало ⬅️ (Н)"), KeyboardButton("В конец ➡️ (Н)")],
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
        f"Напоминание {index + 1}\n"
        f"Название: {header}\n"
        f"Создано {date}\n"
        f"Напомнит {due_date}\n",
        reply_markup=reply_markup,
    )


async def handle_reminders_back(update, context):
    index = context.user_data.get("index", 0)
    user_id = update.effective_user.id

    try:
        async with database.get_session() as session:
            result = await session.execute(
                select(database.Reminder)
                .where(database.Reminder.user_id == user_id)
                .offset(index - 1)
                .limit(1)
            )
            previous_reminder = result.scalar_one_or_none()
            if previous_reminder and index - 1 >= 0:
                context.user_data["index"] = index - 1

    except Exception as e:
        pass

    finally:
        return await handle_reminders_show(update, context)


async def handle_reminders_forward(update, context):
    index = context.user_data.get("index", 0)
    user_id = update.effective_user.id

    try:
        async with database.get_session() as session:
            result = await session.execute(
                select(database.Reminder)
                .where(database.Reminder.user_id == user_id)
                .offset(index + 1)
                .limit(1)
            )
            next_reminder = result.scalar_one_or_none()
            if next_reminder:
                context.user_data["index"] = index + 1

    except Exception as e:
        pass

    finally:
        return await handle_reminders_show(update, context)


async def handle_reminders_begin(update, context):
    user_id = update.effective_user.id

    try:
        async with database.get_session() as session:
            result = await session.execute(
                select(database.Reminder)
                .where(database.Reminder.user_id == user_id)
                .offset(0)
                .limit(1)
            )
            previous_reminder = result.scalar_one_or_none()
            if previous_reminder:
                context.user_data["index"] = 0

    except Exception as e:
        pass

    finally:
        return await handle_reminders_show(update, context)


async def handle_reminders_end(update, context):
    user_id = update.effective_user.id

    try:
        async with database.get_session() as session:
            result = await session.execute(
                select(func.count())
                .select_from(database.Reminder)
                .where(database.Reminder.user_id == user_id)
            )
            index = result.scalar() - 1

            result = await session.execute(
                select(database.Reminder)
                .where(database.Reminder.user_id == user_id)
                .offset(index)
                .limit(1)
            )
            next_reminder = result.scalar_one_or_none()
            if next_reminder:
                context.user_data["index"] = index

    except Exception as e:
        pass

    finally:
        return await handle_reminders_show(update, context)
