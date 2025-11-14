# file: bot.py
import os
import re
import logging
import random
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Загружаем переменные из .env файла
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")

# --- Простая PII-очистка ---
phone_re = re.compile(r'(\+?\d[\d\s\-\(\)]{5,}\d)')
email_re = re.compile(r'[\w\.-]+@[\w\.-]+')
coord_re = re.compile(r'\b(\d{1,3}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)\b')

# Клавиатура для Reply-кнопок
main_keyboard = [
    [KeyboardButton("Напиши текст для поста ✍️"), KeyboardButton("Создай изображение для поста 🎨")]
]
reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)

# Простая настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Список случайных ответов когда команда не опознана
random_responses = [
    "Эх, если бы я был поумнее... 🧠 А пока давай использовать кнопки!",
    "Я в замешательстве 🫣 Лучше нажми на кнопку, я так точнее пойму",
    "Кажется, ты открываешь во мне новые возможности... ⚡ Но пока только кнопки понимаю 🤖",
    "Ой-ой, что-то пошло не так! 😅 Давай начнем с кнопок?",
    "Мой искусственный интеллект в ступоре... 🤖💥 Выбери действие ниже!",
    "Так-так, давай попробуем еще разок! 🔄 Используй кнопки, пожалуйста",
    "Упс! Кажется, я не распознал команду 🚫 Давай попробуем с кнопок?",
    "Ой, прости! 😇 Я немного запутался. Может, выберешь кнопку?",
    "Мой мозг-процессор завис... ⏳ Лучше используй кнопки ниже!"
]

def scrub_pii(text: str) -> (str, list):
    changes = []
    t = phone_re.sub("[контакт]", text)
    if t != text:
        changes.append("телефон/контакт удалён")
    text = t
    t = email_re.sub("[email]", text)
    if t != text:
        changes.append("email удалён")
    text = t
    t = coord_re.sub("[координаты]", text)
    if t != text:
        changes.append("координаты удалены")
    return text, changes

# --- Заглушка для генерации ИИ ---
def generate_with_ai(prompt: str) -> str:
    """
    Здесь должна быть интеграция с реальным AI API.
    Для прототипа - возвращаем фейковый ответ.
    """
    # В реальном коде: запрос к OpenAI/Anthropic с prompt, парсинг результата
    return ("[Вариант 1]\nКороткий пост на основе: " + prompt[:1200] + "\n\n"
            "[Вариант 2]\nСредний пост...\n\n"
            "[Вариант 3]\nДлинный пост...")

# --- Хендлеры ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
🚀 Быстрый старт:

1. Нажми кнопку ✍️ или 🎨
2. Опиши идею в 1-3 предложения  
3. Получи готовый контент!

🔮 Я превращу твои мысли в крутые посты!

👇 Выбирай действие:
    """
    await update.message.reply_text(text, reply_markup=reply_markup)

async def create_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Сохраняем состояние, что ждем описание для текста
    context.user_data['waiting_for'] = 'text_description'
    await update.message.reply_text("Опишите событие или проект (1-3 предложения) 📝\nЯ сгенерирую варианты постов и оформление 🎯", reply_markup=reply_markup)

async def create_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Сохраняем состояние, что ждем описание для изображения
    context.user_data['waiting_for'] = 'image_description'
    await update.message.reply_text("Опишите событие или проект (1-3 предложения) 🎨\nЯ сгенерирую изображение по теме 🖼", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    text = update.message.text
    scrubbed, changes = scrub_pii(text)

    # Проверяем, не находимся ли мы в состоянии ожидания описания
    waiting_for = context.user_data.get('waiting_for')
    
    if waiting_for == 'text_description':
        # Если ждем описание для текста и это не команда
        if text not in ["Напиши текст для поста ✍️", "Создай изображение для поста 🎨"]:
            await update.message.reply_text("✅ Понял! Обрабатываю запрос... ⏳")
            # Сбрасываем состояние
            context.user_data['waiting_for'] = None
            
            # Здесь будет логика обработки описания для текста
            if changes:
                note = "🔒 Я убрал/заменил: " + ", ".join(changes) + ".\n\n"
            else:
                note = ""
            
            prompt = (f"Описание: {scrubbed}\n"
                      "Задача: предложи 3 варианта поста для соцсетей: короткий, средний, длинный. "
                      "Каждый вариант — заголовок (5-7 слов), текст, 3 хештега, CTA. Не используй точные локации. "
                      "Также предложи 2 варианта визуального оформления (фото/инфографика) по 3 пункта каждый.")
            ai_response = generate_with_ai(prompt)
            reply = note + "🎉 Вот что я подготовил:\n\n" + ai_response
            
            # Отправляем ответ
            if len(reply) > 4000:
                for i in range(0, len(reply), 3500):
                    await update.message.reply_text(reply[i:i+3500])
            else:
                await update.message.reply_text(reply)
        else:
            # Если это команда, обрабатываем как обычно
            context.user_data['waiting_for'] = None
            await process_command(update, context, text)
    
    elif waiting_for == 'image_description':
        # Если ждем описание для изображения и это не команда
        if text not in ["Напиши текст для поста ✍️", "Создай изображение для поста 🎨"]:
            await update.message.reply_text("✅ Понял! Готовлю изображение... 🎨")
            # Сбрасываем состояние
            context.user_data['waiting_for'] = None
            
            # Здесь будет логика обработки описания для изображения
            await update.message.reply_text(f"🖼️ Получил описание для изображения: {scrubbed}")
            # Дополнительная логика генерации изображения...
            
        else:
            # Если это команда, обрабатываем как обычно
            context.user_data['waiting_for'] = None
            await process_command(update, context, text)
    
    else:
        # Обычная обработка команд
        await process_command(update, context, text)

async def process_command(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Обработка основных команд"""
    if text == "Напиши текст для поста ✍️":
        await create_text(update, context)
    elif text == "Создай изображение для поста 🎨":
        await create_image(update, context)
    else:
        # Выбираем случайный ответ из списка
        random_response = random.choice(random_responses)
        await update.message.reply_text(random_response, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на inline-кнопки"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text=f"Вы выбрали: {query.data}")

def main():
    print("Бот запускается...")
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("Бот работает и готов принимать сообщения")
    app.run_polling()

if __name__ == "__main__":
    main()
