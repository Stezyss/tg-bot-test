# handlers/handlers_image.py
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes


style_kb = ReplyKeyboardMarkup([
    ["Реализм", "Мультяшный"], ["Акварель", "Киберпанк"], ["Свой стиль"], ["Назад"]
], resize_keyboard=True)


class ImageHandler:
    def __init__(self, image_service):
        self.isvc = image_service

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE, **kw):
        context.user_data['waiting'] = 'image_prompt'
        await update.message.reply_text("Опиши картинку:", reply_markup=ReplyKeyboardMarkup([["Назад в главное меню"]], resize_keyboard=True), **kw)

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, nco_info: dict, **kw):
        w = context.user_data.get('waiting')
        if w == 'image_prompt':
            context.user_data['image_prompt'] = text
            context.user_data['waiting'] = 'image_style'
            await update.message.reply_text("Стиль:", reply_markup=style_kb, **kw)
            return True

        if w == 'image_style':
            styles = {"Реализм": "реализм", "Мультяшный": "мультяшный", "Акварель": "акварель", "Киберпанк": "киберпанк"}
            if text in styles:
                await update.message.reply_text("Генерирую...", **kw)
                img = await self.isvc.generate_image(context.user_data['image_prompt'], nco_info, styles[text])
                from .handlers_nco import get_main_keyboard
                await (update.message.reply_photo(photo=img, reply_markup=get_main_keyboard(True), **kw)
                       if img else update.message.reply_text("Ошибка", reply_markup=get_main_keyboard(True), **kw))
                context.user_data.clear()
            elif text == "Свой стиль":
                context.user_data['waiting'] = 'custom_image_style'
                await update.message.reply_text("Свой стиль:", reply_markup=ReplyKeyboardMarkup([["Назад"]], resize_keyboard=True), **kw)
            return True

        if w == 'custom_image_style':
            await update.message.reply_text("Генерирую...", **kw)
            img = await self.isvc.generate_image(context.user_data['image_prompt'], nco_info, text)
            from .handlers_nco import get_main_keyboard
            await (update.message.reply_photo(photo=img, reply_markup=get_main_keyboard(True), **kw)
                   if img else update.message.reply_text("Ошибка", reply_markup=get_main_keyboard(True), **kw))
            context.user_data.clear()
            return True
        return False