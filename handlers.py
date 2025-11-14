# handlers.py
import re
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from text_service import TextService
from image_service import ImageService


# НОВАЯ КЛАВИАТУРА ПО ВАШЕМУ ТЗ
main_keyboard = ReplyKeyboardMarkup([
    ["📝 Генерация текста", "🎨 Генерация изображения"],
    ["✏️ Редактор текста", "📅 Контент-план"],
    ["🔍 Предоставить информацию об НКО"]  # Большая кнопка на всю строку
], resize_keyboard=True)

style_markup = InlineKeyboardMarkup([
    [InlineKeyboardButton("💬 Разговорный", callback_data="style_casual")],
    [InlineKeyboardButton("🏢 Официальный", callback_data="style_formal")],
    [InlineKeyboardButton("🎭 Художественный", callback_data="style_artistic")],
    [InlineKeyboardButton("⚪ Без стиля", callback_data="style_skip")]
])

def scrub_pii(text: str):
    text = re.sub(r'\+\d[\d\s\-\(\)]{8,}', '[телефон]', text)
    text = re.sub(r'[\w\.-]+@[\w\.-]+', '[email]', text)
    text = re.sub(r'\b\d{1,3}\.\d+\s*,\s*-?\d{1,3}\.\d+\b', '[координаты]', text)
    return text, []


class BotHandlers:
    def __init__(self, text_service: TextService, image_service: ImageService):
        self.text_service = text_service
        self.image_service = image_service

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data.clear()
        context.user_data['nko_info'] = {}
        await update.message.reply_text(
            "👋 Привет! Я помогу создавать посты и картинки для НКО\n\n"
            "📋 Сначала можешь рассказать о своей организации (необязательно)",
            reply_markup=main_keyboard
        )

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        scrubbed, _ = scrub_pii(text)
        nko_info = context.user_data.get('nko_info', {})

        # ——— СБОР ИНФОРМАЦИИ О НКО ———
        if text == "🔍 Предоставить информацию об НКО":
            context.user_data['state'] = 'nko_name'
            await update.message.reply_text("🏷️ Название НКО?")
            return

        if context.user_data.get('state') == 'nko_name':
            nko_info['name'] = scrubbed
            context.user_data['state'] = 'nko_desc'
            await update.message.reply_text("📄 Краткое описание миссии?")
            return

        if context.user_data.get('state') == 'nko_desc':
            nko_info['description'] = scrubbed
            context.user_data['state'] = 'nko_act'
            await update.message.reply_text("🔄 Чем занимаетесь?")
            return

        if context.user_data.get('state') == 'nko_act':
            nko_info['activities'] = scrubbed
            context.user_data['nko_info'] = nko_info
            context.user_data['state'] = None
            await update.message.reply_text(
                "✅ Информация сохранена! Теперь посты будут персональными",
                reply_markup=main_keyboard
            )
            return

        # ——— ОСНОВНЫЕ ДЕЙСТВИЯ ———
        if text == "📝 Генерация текста":
            context.user_data['waiting'] = 'text_prompt'
            await update.message.reply_text("💡 О чём пост? (идея в 1–2 предложения)")
            return

        if text == "🎨 Генерация изображения":
            context.user_data['waiting'] = 'image_prompt'
            await update.message.reply_text("🎨 Опиши картинку:")
            return

        if text == "✏️ Редактор текста":
            context.user_data['waiting'] = 'edit_text'
            await update.message.reply_text("📝 Пришли текст — я его улучшу")
            return

        if text == "📅 Контент-план":
            context.user_data['waiting'] = 'plan_period'
            await update.message.reply_text("📆 На какой период? (неделя / месяц)")
            return

        # ——— ОБРАБОТКА ВВОДА ———
        if context.user_data.get('waiting') == 'text_prompt':
            context.user_data['last_prompt'] = scrubbed
            await update.message.reply_text("🎨 Выбери стиль:", reply_markup=style_markup)
            return

        if context.user_data.get('waiting') == 'image_prompt':
            await update.message.reply_text("⏳ Генерирую...")
            img = await self.image_service.generate_image(scrubbed, nko_info)
            if img:
                await update.message.reply_photo(img, caption="✅ Готово!")
            else:
                await update.message.reply_text("❌ Не получилось сгенерировать")
            context.user_data['waiting'] = None
            await update.message.reply_text("✅ Готово!", reply_markup=main_keyboard)
            return

        if context.user_data.get('waiting') == 'edit_text':
            result = self.text_service.edit_text(scrubbed, nko_info)
            await update.message.reply_text(f"✨ Улучшено:\n\n{result}", reply_markup=main_keyboard)
            context.user_data['waiting'] = None
            return

        if context.user_data.get('waiting') == 'plan_period':
            context.user_data['plan_period'] = scrubbed
            context.user_data['waiting'] = 'plan_freq'
            await update.message.reply_text("🔄 Как часто публикуете?")
            return

        if context.user_data.get('waiting') == 'plan_freq':
            plan = self.text_service.generate_content_plan(
                context.user_data['plan_period'], scrubbed, nko_info
            )
            await update.message.reply_text(f"📋 Контент-план:\n\n{plan}", reply_markup=main_keyboard)
            context.user_data['waiting'] = None
            return

        # Если ничего не подошло
        await update.message.reply_text("👇 Выбери действие ниже", reply_markup=main_keyboard)

    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data

        if data.startswith("style_"):
            styles = {
                "style_casual": "разговорный, дружелюбный",
                "style_formal": "официальный, строгий",
                "style_artistic": "поэтичный, художественный",
                "style_skip": None
            }
            style = styles[data]
            prompt = context.user_data.get('last_prompt', 'Сделай красивый пост для НКО')
            nko_info = context.user_data.get('nko_info', {})

            await query.edit_message_text("⏳ Генерирую текст...")
            result = self.text_service.generate_text(prompt, nko_info, style)
            await query.edit_message_text(f"✅ Готово:\n\n{result}")
