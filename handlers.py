# handlers.py
import re
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from text_service import TextService
from image_service import ImageService


# ───── КЛАВИАТУРЫ С ЭМОДЗИ ───────────────────────────────────────────────────────
main_keyboard = ReplyKeyboardMarkup([
    ["📝 Генерация текста", "🎨 Генерация изображения"],
    ["✏️ Редактор текста", "📅 Контент-план"],
    ["🔍 Предоставить информацию об НКО"]
], resize_keyboard=True)

back_to_main_keyboard = ReplyKeyboardMarkup([
    ["🔙 Назад в главное меню"]
], resize_keyboard=True)

# только для первого вопроса (название НКО)
back_skip_to_main_keyboard = ReplyKeyboardMarkup([
    ["🔙 Назад в главное меню", "⏭️ Пропустить"]
], resize_keyboard=True)

back_skip_keyboard = ReplyKeyboardMarkup([
    ["🔙 Назад", "⏭️ Пропустить"]
], resize_keyboard=True)

back_only_keyboard = ReplyKeyboardMarkup([
    ["🔙 Назад"]
], resize_keyboard=True)

style_keyboard = ReplyKeyboardMarkup([
    ["💬 Разговорный", "🏢 Официальный"],
    ["🎭 Художественный", "⚪ Без стиля"],
    ["🔙 Назад"]
], resize_keyboard=True)

image_style_keyboard = ReplyKeyboardMarkup([
    ["🎨 Реализм", "🦄 Мультяшный"],
    ["💧 Акварель", "🔳 Минимализм"],
    ["🔙 Назад"]
], resize_keyboard=True)

period_keyboard = ReplyKeyboardMarkup([
    ["📅 Неделя", "📆 Месяц"],
    ["📊 Ввести свой период"],
    ["🔙 Назад в главное меню"]
], resize_keyboard=True)

freq_week_keyboard = ReplyKeyboardMarkup([
    ["🔄 1 раз в день", "🔄 2 раза в неделю", "🔄 3 раза в неделю"],
    ["🔄 1 раз в неделю"],
    ["🔙 Назад"]
], resize_keyboard=True)

freq_month_keyboard = ReplyKeyboardMarkup([
    ["🔄 1 раз в день", "🔄 2 раза в неделю", "🔄 3 раза в неделю"],
    ["🔄 1 раз в неделю", "🔄 2 раза в месяц"],
    ["🔙 Назад"]
], resize_keyboard=True)


def scrub_pii(text: str):
    text = re.sub(r'\+\d[\d\s\-\(\)]{8,}', '[телефон]', text)
    text = re.sub(r'[\w\.-]+@[\d\w\.-]+', '[email]', text)
    text = re.sub(r'\b\d{1,3}\.\d+\s*,\s*-?\d{1,3}\.\d+\b', '[координаты]', text)
    return text, []


class BotHandlers:
    def __init__(self, text_service: TextService, image_service: ImageService):
        self.text_service = text_service
        self.image_service = image_service

    # ───── /start ───────────────────────────────────────────────────────────────
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data.clear()
        context.user_data['nko_info'] = {
            'name': '', 'description': '', 'activities': '',
            'audience': '', 'website': ''
        }
        context.user_data['nko_skipped_all'] = False  # флаг: все поля пропущены
        await update.message.reply_text(
            "👋 Привет! Я помогу создавать посты и картинки для НКО\n\n"
            "📋 Сначала можешь рассказать о своей организации (необязательно)",
            reply_markup=main_keyboard
        )

    # ───── Обработчик всех текстовых сообщений ─────────────────────────────────────
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        scrubbed, _ = scrub_pii(text)
        nko_info = context.user_data.get('nko_info', {})
        state = context.user_data.get('state')
        waiting = context.user_data.get('waiting')

        # ── Назад в главное меню ─────────────────────────────────────────────────
        if text == "🔙 Назад в главное меню":
            context.user_data.clear()
            context.user_data['nko_info'] = {}
            await update.message.reply_text(
                "👇 Возвращаюсь в главное меню", reply_markup=main_keyboard
            )
            return

        # ── НАЗАД ───────────────────────────────────────────────────────────────
        if text == "🔙 Назад":
            if 'nko_skipped_all' in context.user_data:
                del context.user_data['nko_skipped_all']

            if state == 'nko_desc':
                context.user_data['state'] = 'nko_name'
                await update.message.reply_text(
                    "🏷️ Название НКО? (например, «Благотворительный фонд «Добро»)",
                    reply_markup=back_skip_to_main_keyboard
                )
                return
            if state == 'nko_act':
                context.user_data['state'] = 'nko_desc'
                await update.message.reply_text(
                    "📜 Краткое описание миссии? (1–2 предложения, например: «Помогаем детям-сиротам найти любящую семью»)",
                    reply_markup=back_skip_keyboard
                )
                return
            if state == 'nko_audience':
                context.user_data['state'] = 'nko_act'
                await update.message.reply_text(
                    "⚙️ Чем занимаетесь? (например, помощь детям, экология, поддержка пожилых)",
                    reply_markup=back_skip_keyboard
                )
                return
            if state == 'nko_website':
                context.user_data['state'] = 'nko_audience'
                await update.message.reply_text(
                    "👥 Целевая аудитория? (дети, студенты, работники, пенсионеры и т.д.)",
                    reply_markup=back_skip_keyboard
                )
                return

            if waiting == 'plan_freq':
                context.user_data['waiting'] = 'plan_period'
                await update.message.reply_text(
                    "📆 Выбери период для контент-плана (например: Неделя или Месяц):",
                    reply_markup=period_keyboard
                )
                return
            if waiting == 'plan_end_date':
                context.user_data['waiting'] = 'plan_start_date'
                await update.message.reply_text(
                    "📅 Укажи начальную дату (дд.мм.гггг, например 15.11.2025):",
                    reply_markup=back_only_keyboard
                )
                return
            if waiting == 'plan_start_date':
                context.user_data['waiting'] = 'plan_period'
                await update.message.reply_text(
                    "📆 Выбери период для контент-плана (например: Неделя или Месяц):",
                    reply_markup=period_keyboard
                )
                return

            if waiting == 'select_style':
                context.user_data['waiting'] = 'text_prompt'
                await update.message.reply_text(
                    "📝 О чём пост? (идея в 1–2 предложения)",
                    reply_markup=back_to_main_keyboard
                )
                return
            if waiting == 'image_style':
                context.user_data['waiting'] = 'image_prompt'
                await update.message.reply_text(
                    "🎨 Опиши картинку:",
                    reply_markup=back_to_main_keyboard
                )
                return
            return

        # ── Пропустить ───────────────────────────────────────────────────────────
        if text == "⏭️ Пропустить":
            if state == 'nko_name':
                nko_info['name'] = ''
                context.user_data['state'] = 'nko_desc'
                await update.message.reply_text(
                    "📜 Краткое описание миссии? (1–2 предложения, например: «Помогаем детям-сиротам найти любяющую семью»)",
                    reply_markup=back_skip_keyboard
                )
            elif state == 'nko_desc':
                nko_info['description'] = ''
                context.user_data['state'] = 'nko_act'
                await update.message.reply_text(
                    "⚙️ Чем занимаетесь? (например, помощь детям, экология, поддержка пожилых)",
                    reply_markup=back_skip_keyboard
                )
            elif state == 'nko_act':
                nko_info['activities'] = ''
                context.user_data['state'] = 'nko_audience'
                await update.message.reply_text(
                    "👥 Целевая аудитория? (дети, студенты, работники, пенсионеры и т.д.)",
                    reply_markup=back_skip_keyboard
                )
            elif state == 'nko_audience':
                nko_info['audience'] = ''
                context.user_data['state'] = 'nko_website'
                await update.message.reply_text(
                    "🌐 Веб-сайт (при наличии)? (пример: https://example.org)",
                    reply_markup=back_skip_keyboard
                )
            elif state == 'nko_website':
                nko_info['website'] = ''
                context.user_data['state'] = None
                context.user_data['nko_info'] = nko_info

                # Проверяем: все поля пустые?
                if not any(nko_info.values()):
                    context.user_data['nko_skipped_all'] = True
                    await update.message.reply_text(
                        "❌ Информация не была предоставлена!",
                        reply_markup=main_keyboard
                    )
                else:
                    await update.message.reply_text(
                        "✅ Информация сохранена! Теперь посты будут персональными",
                        reply_markup=main_keyboard
                    )
            return

        # ── Предоставить информацию об НКО (первый клик) ───────────────────────
        if text == "🔍 Предоставить информацию об НКО":
            context.user_data['state'] = 'nko_name'
            context.user_data.pop('nko_skipped_all', None)  # сбрасываем флаг
            await update.message.reply_text(
                "🏷️ Название НКО? (например, «Благотворительный фонд «Добро»)",
                reply_markup=back_skip_to_main_keyboard
            )
            return

        # ── Ввод информации НКО ─────────────────────────────────────────────────
        if state == 'nko_name':
            nko_info['name'] = scrubbed
            context.user_data['state'] = 'nko_desc'
            await update.message.reply_text(
                "📜 Краткое описание миссии? (1–2 предложения, например: «Помогаем детям-сиротам найти любящую семью»)",
                reply_markup=back_skip_keyboard
            )
            return

        if state == 'nko_desc':
            nko_info['description'] = scrubbed
            context.user_data['state'] = 'nko_act'
            await update.message.reply_text(
                "⚙️ Чем занимаетесь? (например, помощь детям, экология, поддержка пожилых)",
                reply_markup=back_skip_keyboard
            )
            return

        if state == 'nko_act':
            nko_info['activities'] = scrubbed
            context.user_data['state'] = 'nko_audience'
            await update.message.reply_text(
                "👥 Целевая аудитория? (дети, студенты, работники, пенсионеры и т.д.)",
                reply_markup=back_skip_keyboard
            )
            return

        if state == 'nko_audience':
            nko_info['audience'] = scrubbed
            context.user_data['state'] = 'nko_website'
            await update.message.reply_text(
                "🌐 Веб-сайт (при наличии)? (пример: https://example.org)",
                reply_markup=back_skip_keyboard
            )
            return

        if state == 'nko_website':
            nko_info['website'] = scrubbed
            context.user_data['state'] = None
            context.user_data['nko_info'] = nko_info

            # Если хотя бы одно поле заполнено — персонализация
            if any(nko_info.values()):
                await update.message.reply_text(
                    "✅ Информация сохранена! Теперь посты будут персональными",
                    reply_markup=main_keyboard
                )
            else:
                context.user_data['nko_skipped_all'] = True
                await update.message.reply_text(
                    "❌ Информация не была предоставлена",
                    reply_markup=main_keyboard
                )
            return

        # ── Основные действия ───────────────────────────────────────────────────
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
                "📆 Выбери период для контент-плана (например: Неделя или Месяц):",
                reply_markup=period_keyboard
            )
            return

        # ── Период ───────────────────────────────────────────────────────────────
        if waiting == 'plan_period':
            if text == "📅 Неделя":
                context.user_data['plan_period'] = "неделя"
                context.user_data['waiting'] = 'plan_freq'
                await update.message.reply_text(
                    "🔄 Как часто публикуете? (например: 1 раз в день, 2 раза в неделю)",
                    reply_markup=freq_week_keyboard
                )
                return
            elif text == "📆 Месяц":
                context.user_data['plan_period'] = "месяц"
                context.user_data['waiting'] = 'plan_freq'
                await update.message.reply_text(
                    "🔄 Как часто публикуете? (например: 1 раз в неделю, 2 раза в месяц)",
                    reply_markup=freq_month_keyboard
                )
                return
            elif text == "📊 Ввести свой период":
                context.user_data['waiting'] = 'plan_start_date'
                await update.message.reply_text(
                    "📅 Укажи начальную дату (дд.мм.гггг, например 15.11.2025):",
                    reply_markup=back_only_keyboard
                )
                return

        # ── Пользовательский период – начало ─────────────────────────────────────
        if waiting == 'plan_start_date':
            try:
                start = datetime.strptime(text, "%d.%m.%Y").date()
                context.user_data['plan_start_date'] = start
                context.user_data['waiting'] = 'plan_end_date'
                await update.message.reply_text(
                    "📅 Укажи конечную дату (дд.мм.гггг, например 30.11.2025):",
                    reply_markup=back_only_keyboard
                )
            except ValueError:
                await update.message.reply_text(
                    "❌ Неверный формат. Пример: 15.11.2025",
                    reply_markup=back_only_keyboard
                )
            return

        # ── Пользовательский период – конец ─────────────────────────────────────
        if waiting == 'plan_end_date':
            try:
                end = datetime.strptime(text, "%d.%m.%Y").date()
                start = context.user_data.get('plan_start_date')
                if end < start:
                    await update.message.reply_text(
                        "❌ Конечная дата должна быть позже начальной. Пример: 30.11.2025",
                        reply_markup=back_only_keyboard
                    )
                    return
                context.user_data['plan_end_date'] = end
                context.user_data['plan_period'] = "custom"
                context.user_data['waiting'] = 'plan_freq'

                delta = (end - start).days
                if delta <= 7:
                    await update.message.reply_text(
                        "🔄 Как часто публикуете? (например: 1 раз в день, 2 раза в неделю)",
                        reply_markup=freq_week_keyboard
                    )
                else:
                    await update.message.reply_text(
                        "🔄 Как часто публикуете? (например: 1 раз в неделю, 2 раза в месяц)",
                        reply_markup=freq_month_keyboard
                    )
            except ValueError:
                await update.message.reply_text(
                    "❌ Неверный формат. Пример: 30.11.2025",
                    reply_markup=back_only_keyboard
                )
            return

        # ── Частота и генерация плана ───────────────────────────────────────────
        if waiting == 'plan_freq':
            valid_freq = [
                "🔄 1 раз в день", "🔄 2 раза в неделю", "🔄 3 раза в неделю",
                "🔄 1 раз в неделю", "🔄 2 раза в месяц"
            ]
            if text in valid_freq:
                period = context.user_data.get('plan_period', 'неделя')
                frequency = text.replace("🔄 ", "")  # Убираем эмодзи для логики

                start_date = datetime.now().date()
                end_date = None
                if period == "custom":
                    start_date = context.user_data.get('plan_start_date')
                    end_date = context.user_data.get('plan_end_date')

                await update.message.reply_text("⏳ Генерирую контент-план...")
                plan = self.text_service.generate_content_plan(
                    period=period,
                    frequency=frequency,
                    nko_info=nko_info,
                    start_date=start_date,
                    end_date=end_date
                )
                await update.message.reply_text(
                    f"📋 Контент-план:\n\n{plan}", reply_markup=main_keyboard
                )
                context.user_data['waiting'] = None
                return

        # ── Генерация текста ───────────────────────────────────────────────────
        if waiting == 'text_prompt':
            context.user_data['last_prompt'] = scrubbed
            await update.message.reply_text(
                "🎨 Выбери стиль:", reply_markup=style_keyboard
            )
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
                await update.message.reply_text(
                    f"✅ Готово:\n\n{result}", reply_markup=main_keyboard
                )
                context.user_data['waiting'] = None
            else:
                await update.message.reply_text(
                    "👇 Выбери стиль из кнопок", reply_markup=style_keyboard
                )
            return

        # ── Генерация изображения ───────────────────────────────────────────────
        if waiting == 'image_prompt':
            context.user_data['image_prompt'] = scrubbed
            await update.message.reply_text(
                "🎨 Выбери стиль картинки:", reply_markup=image_style_keyboard
            )
            context.user_data['waiting'] = 'image_style'
            return

        if waiting == 'image_style':
            styles = {
                "🎨 Реализм": "реализм",
                "🦄 Мультяшный": "мультяшный",
                "💧 Акварель": "акварель",
                "🔳 Минимализм": "минимализм"
            }
            if text in styles:
                style = styles[text]
                prompt = context.user_data['image_prompt']
                full_prompt = f"{prompt}, стиль: {style}"
                await update.message.reply_text("⏳ Генерирую...")
                img = await self.image_service.generate_image(full_prompt, nko_info)
                if img:
                    await update.message.reply_photo(
                        photo=img, caption="✅ Готово!", reply_markup=main_keyboard
                    )
                else:
                    await update.message.reply_text(
                        "❌ Не получилось сгенерировать", reply_markup=main_keyboard
                    )
                context.user_data['waiting'] = None
            else:
                await update.message.reply_text(
                    "👇 Выбери стиль из кнопок", reply_markup=image_style_keyboard
                )
            return

        # ── Редактор текста ─────────────────────────────────────────────────────
        if waiting == 'edit_text':
            await update.message.reply_text("⏳ Улучшаю текст...")
            result = self.text_service.edit_text(scrubbed, nko_info)
            await update.message.reply_text(
                f"✨ Улучшено:\n\n{result}", reply_markup=main_keyboard
            )
            context.user_data['waiting'] = None
            return

        # ── Если ничего не подошло ───────────────────────────────────────────────
        await update.message.reply_text(
            "👇 Выбери действие ниже", reply_markup=main_keyboard
        )
