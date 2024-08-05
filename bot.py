import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import start_polling
from config import settings
import openai
import aiohttp
import os
from gtts import gTTS

logging.basicConfig(level=logging.INFO)

bot = Bot(token=settings.telegram_token)
dp = Dispatcher(bot)

openai.api_key = settings.openai_api_key

def text_to_speech(text, output_file):
    """Функция для преобразования текста в речь и сохранения в файл"""
    tts = gTTS(text=text, lang='ru')
    tts.save(output_file)

def transcribe_audio(audio_file_path):
    """Функция для транскрипции аудио в текст"""
    try:
        with open(audio_file_path, "rb") as audio_file:
            response = openai.Audio.transcribe(
                model="whisper-1",  # Убедитесь, что используете правильный модельный идентификатор
                file=audio_file
            )
            return response['text']
    except Exception as e:
        logging.error(f"Error during transcription: {e}")
        return "Не удалось распознать аудио."

def get_chatgpt_response(text):
    """Функция для получения ответа от ChatGPT"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Используйте доступную модель
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": text},
            ]
        )
        return response.choices[0].message['content']
    except Exception as e:
        logging.error(f"Error during chat completion: {e}")
        return "Не удалось получить ответ."

@dp.message_handler(content_types=types.ContentType.VOICE)
async def handle_voice_message(message: types.Message):
    logging.info("Received voice message")
    voice = await message.voice.get_file()
    file_path = voice.file_path

    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://api.telegram.org/file/bot{settings.telegram_token}/{file_path}') as resp:
            audio_data = await resp.read()

    # Сохранение аудио файла временно
    audio_file_path = "temp.ogg"
    with open(audio_file_path, "wb") as audio_file:
        audio_file.write(audio_data)

    # Использование Whisper для преобразования голоса в текст
    text = transcribe_audio(audio_file_path)

    # Удаление временного аудио файла
    os.remove(audio_file_path)

    # Отправка запроса в OpenAI Assistant API
    answer = get_chatgpt_response(text)

    # Преобразование ответа в речь и сохранение в файл
    tts_audio_file_path = "response.mp3"
    text_to_speech(answer, tts_audio_file_path)

    # Отправка аудиофайла пользователю
    with open(tts_audio_file_path, "rb") as audio_file:
        await message.reply_voice(voice=audio_file)

    # Удаление временного аудио файла
    os.remove(tts_audio_file_path)

if __name__ == "__main__":
    start_polling(dp, skip_updates=True)
