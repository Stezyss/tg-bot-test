import re
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from ai_service import AIService
from image_service import ImageService

phone_re = re.compile(r'(\+?\d[\d\s\-\(\)]{5,}\d)')
email_re = re.compile(r'[\w\.-]+@[\w\.-]+')
coord_re = re.compile(r'\b(\d{1,3}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)\b')

main_keyboard = [
    [KeyboardButton("Напиши текст для поста ✍️"), KeyboardButton("Создай изображение для поста 🎨")]
]
reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)

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

class BotHandlers:
    def __init__(self, ai_service: AIService, image_service: ImageService):
        self.ai_service = ai_service
        self.image_service = image_service

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = """
🚀 Быстрый старт:

1. Нажми кнопку ✍️ или 🎨
2. Опиши идею в 1-3 предложения  
3. Получи готовый контент!

🔮 Я превращу твои мысли в крутые посты!

👇 Выбирай действие:
        """
        await update.message.reply_text(text, reply_markup=reply_markup)

    async def create_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['waiting_for'] = 'text_description'
        await update.message.reply_text("Опишите событие или проект (1-3 предложения) 📝\nЯ сгенерирую варианты постов и оформление 🎯", reply_markup=reply_markup)

    async def create_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['waiting_for'] = 'image_description'
        await update.message.reply_text("Опишите событие или проект (1-3 предложения) 🎨\nЯ сгенерирую изображение по теме 🖼", reply_markup=reply_markup)

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        scrubbed, changes = scrub_pii(text)

        waiting_for = context.user_data.get('waiting_for')
        
        if waiting_for == 'text_description':
            if text not in ["Напиши текст для поста ✍️", "Создай изображение для поста 🎨"]:
                await update.message.reply_text("✅ Понял! Обрабатываю запрос... ⏳")
                context.user_data['waiting_for'] = None
                
                if changes:
                    note = "🔒 Я убрал/заменил: " + ", ".join(changes) + ".\n\n"
                else:
                    note = ""
                
                prompt = (f"Описание: {scrubbed}\n"
                          "Задача: предложи 3 варианта поста для соцсетей: короткий, средний, длинный. "
                          "Каждый вариант — заголовок (5-7 слов), текст, 3 хештега, CTA. Не используй точные локации. "
                          "Также предложи 2 варианта визуального оформления (фото/инфографика) по 3 пункта каждый.")
                ai_response = self.ai_service.generate_text(prompt)
                reply = note + "🎉 Вот что я подготовил:\n\n" + ai_response
                
                if len(reply) > 4000:
                    for i in range(0, len(reply), 3500):
                        await update.message.reply_text(reply[i:i+3500])
                else:
                    await update.message.reply_text(reply)
            else:
                context.user_data['waiting_for'] = None
                await self.process_command(update, context, text)
        
        elif waiting_for == 'image_description':
            if text not in ["Напиши текст для поста ✍️", "Создай изображение для поста 🎨"]:
                await update.message.reply_text("✅ Понял! Готовлю изображение... 🎨")
                context.user_data['waiting_for'] = None
                
                await update.message.reply_text(f"🖼️ Получил описание для изображения: {scrubbed}")
                # Заглушка для генерации изображения
            else:
                context.user_data['waiting_for'] = None
                await self.process_command(update, context, text)
        
        else:
            await self.process_command(update, context, text)

    async def process_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        if text == "Напиши текст для поста ✍️":
            await self.create_text(update, context)
        elif text == "Создай изображение для поста 🎨":
            await self.create_image(update, context)
        else:
            random_response = random.choice(random_responses)
            await update.message.reply_text(random_response, reply_markup=reply_markup)