import io

import aiofiles.os as aios
from salute_speech.speech_recognition import SaluteSpeechClient
from sqlalchemy import func, select

import src.database as database


async def get_api_token(update, context):
    try:
        user_id = update.effective_user.id

        async with database.get_session() as session:
            result = await session.execute(
                select(database.Setting)
                .where(database.Setting.user_id == user_id)
                .limit(1)
            )

            setting = result.scalar_one_or_none()
            if setting.salute_speech:
                return setting.salute_speech

    except Exception as e:
        pass


async def ensure_text_message(update, context):
    if update.message.text:
        return update.message.text

    elif update.message.voice:
        api_token = await get_api_token(update, context)
        file_id = update.message.voice.file_id
        voice_file = await context.bot.get_file(file_id)
        file_path = f"data/{file_id}.oga"
        text = None
        try:
            client = SaluteSpeechClient(client_credentials=api_token)

            await voice_file.download_to_drive(file_path)

            with open(file_path, "rb") as audio_file:
                result = await client.audio.transcriptions.create(
                    file=audio_file, language="ru-RU"
                )

                text = result.text

        except Exception:
            pass

        finally:
            await aios.remove(file_path)

            if not text:
                raise RuntimeError(
                    "Некорректный токен SaluteSpeech или не удалось распознать сообщение"
                )

            await update.message.reply_text("Распознанный текст:")
            await update.message.reply_text(text)

            return text
