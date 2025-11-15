# handlers/handlers_text_create.py
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes


text_mode_kb = ReplyKeyboardMarkup([
    ["Свободный текст", "Структурированная форма"],
    ["Назад в главное меню"]
], resize_keyboard=True)

post_type_kb = ReplyKeyboardMarkup([
    ["Анонс", "Новости"], ["Призыв к действию", "Отчет"], ["Назад"]
], resize_keyboard=True)

style_kb = ReplyKeyboardMarkup([
    ["Разговорный", "Официальный"], ["Художественный", "Без стиля"], ["Назад"]
], resize_keyboard=True)


class TextCreateHandler:
    def __init__(self, text_service):
        self.ts = text_service

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE, **kw):
        context.user_data['waiting'] = 'text_mode'
        await update.message.reply_text("Режим:", reply_markup=text_mode_kb, **kw)

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, nco_info: dict, **kw):
        w = context.user_data.get('waiting')
        if w == 'text_mode':
            if text == "Свободный текст":
                context.user_data.update({'text_mode': 'free', 'waiting': 'text_prompt'})
                await update.message.reply_text("Запрос:", reply_markup=ReplyKeyboardMarkup([["Назад в главное меню"]], resize_keyboard=True), **kw)
            elif text == "Структурированная форма":
                context.user_data.update({'text_mode': 'structured', 'waiting': 'select_post_type'})
                await update.message.reply_text("Тип поста:", reply_markup=post_type_kb, **kw)
            return True

        if w == 'select_post_type':
            types = {"Анонс": "анонс", "Новости": "новости", "Призыв к действию": "призыв", "Отчет": "отчет"}
            if text in types:
                context.user_data.update({'post_type': types[text], 'waiting': 'text_prompt'})
                await update.message.reply_text("Детали:", reply_markup=ReplyKeyboardMarkup([["Назад в главное меню"]], resize_keyboard=True), **kw)
            return True

        if w == 'text_prompt':
            prompt = text
            if context.user_data.get('text_mode') == 'structured':
                prompt = f"Пост: {context.user_data['post_type']}. {prompt}"
            context.user_data['text_prompt'] = prompt
            context.user_data['waiting'] = 'select_style'
            await update.message.reply_text("Стиль:", reply_markup=style_kb, **kw)
            return True

        if w == 'select_style':
            styles = {"Разговорный": "разговорный", "Официальный": "официальный", "Художественный": "художественный", "Без стиля": None}
            if text in styles:
                await update.message.reply_text("Генерирую...", **kw)
                result = self.ts.generate_text(context.user_data['text_prompt'], nco_info, styles[text])
                from .handlers_nco import get_main_keyboard
                await update.message.reply_text(result, reply_markup=get_main_keyboard(True), **kw)
                context.user_data.clear()
            return True
        return False