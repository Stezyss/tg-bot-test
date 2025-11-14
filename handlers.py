# handlers.py
import re
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from text_service import TextService
from image_service import ImageService


# ——— КЛАВИАТУРЫ ———
main_keyboard = ReplyKeyboardMarkup([
    ["📝 Генерация текста", "🎨 Генерация изображения"],
    ["✏️ Редактор текста", "📅 Контент-план"],
    ["🔍 Предоставить информацию об НКО"]
], resize_keyboard=True)

# Для первого шага с пропуском — "Назад в главное меню"
back_skip_to_main_keyboard = ReplyKeyboardMarkup([
    ["🔙 Назад в главное меню", "⏭️ Пропустить"]
], resize_keyboard=True)

# Для первого шага без пропуска — "Назад в главное меню"
back_to_main_keyboard = ReplyKeyboardMarkup([
    ["🔙 Назад в главное меню"]
], resize_keyboard=True)

# Для подшагов с пропуском
back_skip_keyboard = ReplyKeyboardMarkup([
    ["🔙 Назад", "⏭️ Пропустить"]
], resize_keyboard=True)

# Для подшагов без пропуска
back_only_keyboard = ReplyKeyboardMarkup([
    ["🔙 Назад"]
], resize_keyboard=True)

# Для выбора стиля — «Назад» внизу по центру
style_keyboard = ReplyKeyboardMarkup([
    ["💬 Разговорный", "🏢 Официальный"],
    ["🎭 Художественный", "⚪ Без стиля"],
    ["🔙 Назад"]
], resize_keyboard=True)


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
            "Привет! Я помогу создавать посты и картинки для НКО\n\n"
            "Сначала можешь рассказать о своей организации (необязательно)",
            reply_markup=main_keyboard
        )

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        scrubbed, _ = scrub_pii(text)
        nko_info = context.user_data.get('nko_info', {})
        state = context.user_data.get('state')
        waiting = context.user_data.get('waiting')

        # ——— ОБРАБОТКА "НАЗАД В ГЛАВНОЕ МЕНЮ" (для первых шагов) ———
        if text == "🔙 Назад в главное меню":
            context.user_data['state'] = None
            context.user_data['waiting'] = None
            await update.message.reply_text("👇 Возвращаюсь в главное меню", reply_markup=main_keyboard)
            return

        # ——— ОБРАБОТКА "НАЗАД" (для подшагов) ———
        if text == "🔙 Назад":
            if state == 'nko_desc':
                context.user_data['state'] = 'nko_name'
                await update.message.reply_text("🏷️ Название НКО?", reply_markup=back_skip_to_main_keyboard)
                return
            if state == 'nko_act':
                context.user_data['state'] = 'nko_desc'
                await update.message.reply_text("📜 Краткое описание миссии?", reply_markup=back_skip_keyboard)
                return

            if waiting == 'select_style':
                context.user_data['waiting'] = 'text_prompt'
                await update.message.reply_text("📝 О чём пост? (идея в 1–2 предложения)", reply_markup=back_to_main_keyboard)
                return

            if waiting == 'plan_freq':
                context.user_data['waiting'] = 'plan_period'
                await update.message.reply_text("📆 На какой период? (неделя / месяц)", reply_markup=back_to_main_keyboard)
                return

            # Для других подшагов, если нужно
            return

        # ——— ОБРАБОТКА "ПРОПУСТИТЬ" (только в НКО) ———
        if text == "⏭️ Пропустить":
            if state == 'nko_name':
                nko_info['name'] = ''
                context.user_data['state'] = 'nko_desc'
                await update.message.reply_text("📜 Краткое описание миссии?", reply_markup=back_skip_keyboard)
            elif state == 'nko_desc':
                nko_info['description'] = ''
                context.user_data['state'] = 'nko_act'
                await update.message.reply_text("⚙️ Чем занимаетесь?", reply_markup=back_skip_keyboard)
            elif state == 'nko_act':
                nko_info['activities'] = ''
                context.user_data['nko_info'] = nko_info
                context.user_data['state'] = None
                await update.message.reply_text(
                    "✅ Информация сохранена! Теперь посты будут персональными",
                    reply_markup=main_keyboard
                )
            return

        # ——— СБОР ИНФОРМАЦИИ О НКО ———
        if text == "🔍 Предоставить информацию об НКО":
            context.user_data['state'] = 'nko_name'
            await update.message.reply_text("🏷️ Название НКО?", reply_markup=back_skip_to_main_keyboard)
            return

        if state == 'nko_name':
            nko_info['name'] = scrubbed
            context.user_data['state'] = 'nko_desc'
            await update.message.reply_text("📜 Краткое описание миссии?", reply_markup=back_skip_keyboard)
            return

        if state == 'nko_desc':
            nko_info['description'] = scrubbed
            context.user_data['state'] = 'nko_act'
            await update.message.reply_text("⚙️ Чем занимаетесь?", reply_markup=back_skip_keyboard)
            return

        if state == 'nko_act':
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
            await update.message.reply_text(
                "📝 О чём пост? (идея в 1–2 предложения)",
                reply_markup=back_to_main_keyboard
            )
            return

        if text == "🎨 Генерация изображения":
            context.user_data['waiting'] = 'image_prompt'
            await update.message.reply_text(
                "🎨 Опиши картинку:",
                reply_markup=back_to_main_keyboard
            )
            return

        if text == "✏️ Редактор текста":
            context.user_data['waiting'] = 'edit_text'
            await update.message.reply_text(
                "✏️ Пришли текст — я его улучшу",
                reply_markup=back_to_main_keyboard
            )
            return

        if text == "📅 Контент-план":
            context.user_data['waiting'] = 'plan_period'
            await update.message.reply_text(
                "📆 На какой период? (неделя / месяц)",
                reply_markup=back_to_main_keyboard
            )
            return

        # ——— ОБРАБОТКА ВВОДА ———
        if waiting == 'text_prompt':
            context.user_data['last_prompt'] = scrubbed
            await update.message.reply_text("🎨 Выбери стиль:", reply_markup=style_keyboard)
            context.user_data['waiting'] = 'select_style'
            return

        if waiting == 'select_style':
            styles = {
                "💬 Разговорный": "разговорный, дружелюбный",
                "🏢 Официальный": "официальный, строгий",
                "🎭 Художественный": "поэтичный, художественный",
                "⚪ Без стиля": None
            }
            if text in styles:
                style = styles[text]
                prompt = context.user_data.get('last_prompt', 'Сделай красивый пост для НКО')
                await update.message.reply_text("⏳ Генерирую текст...")
                result = self.text_service.generate_text(prompt, nko_info, style)
                await update.message.reply_text(f"✅ Готово:\n\n{result}", reply_markup=main_keyboard)
                context.user_data['waiting'] = None
            else:
                await update.message.reply_text("👇 Выбери стиль из кнопок ниже", reply_markup=style_keyboard)
            return

        if waiting == 'image_prompt':
            await update.message.reply_text("⏳ Генерирую...")
            img = await self.image_service.generate_image(scrubbed, nko_info)
            if img:
                await update.message.reply_photo(
                    photo=img,
                    caption="✅ Готово!",
                    reply_markup=main_keyboard
                )
            else:
                await update.message.reply_text(
                    "❌ Не получилось сгенерировать",
                    reply_markup=main_keyboard
                )
            context.user_data['waiting'] = None
            return

        if waiting == 'edit_text':
            result = self.text_service.edit_text(scrubbed, nko_info)
            await update.message.reply_text(f"✨ Улучшено:\n\n{result}", reply_markup=main_keyboard)
            context.user_data['waiting'] = None
            return

        if waiting == 'plan_period':
            context.user_data['plan_period'] = scrubbed
            context.user_data['waiting'] = 'plan_freq'
            await update.message.reply_text("🔄 Как часто публикуете?", reply_markup=back_only_keyboard)
            return

        if waiting == 'plan_freq':
            plan = self.text_service.generate_content_plan(
                context.user_data['plan_period'], scrubbed, nko_info
            )
            await update.message.reply_text(f"📋 Контент-план:\n\n{plan}", reply_markup=main_keyboard)
            context.user_data['waiting'] = None
            return

        # Если ничего не подошло
        await update.message.reply_text("👇 Выбери действие ниже", reply_markup=main_keyboard)
