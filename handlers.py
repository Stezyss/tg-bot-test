# handlers.py
import re
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from text_service import TextService
from image_service import ImageService
from attachment_service import AttachmentService


# ───── КЛАВИАТУРЫ ─────────────────────────────────────────────────────────────
main_keyboard = ReplyKeyboardMarkup([
    ["Генерация текста", "Генерация изображения"],
    ["Редактор текста", "Контент-план"],
    ["Предоставить информацию об НКО"]
], resize_keyboard=True)

back_to_main_keyboard = ReplyKeyboardMarkup([["Назад в главное меню"]], resize_keyboard=True)
back_skip_to_main_keyboard = ReplyKeyboardMarkup([["Назад в главное меню", "Пропустить"]], resize_keyboard=True)
back_skip_keyboard = ReplyKeyboardMarkup([["Назад", "Пропустить"]], resize_keyboard=True)
back_only_keyboard = ReplyKeyboardMarkup([["Назад"]], resize_keyboard=True)

text_mode_keyboard = ReplyKeyboardMarkup([
    ["Свободный текст", "Структурированная форма"],
    ["Назад в главное меню"]
], resize_keyboard=True)

post_type_keyboard = ReplyKeyboardMarkup([
    ["Анонс", "Новости"],
    ["Призыв к действию", "Отчет"],
    ["Назад"]
], resize_keyboard=True)

style_keyboard = ReplyKeyboardMarkup([
    ["Разговорный", "Официальный"],
    ["Художественный", "Без стиля"],
    ["Назад"]
], resize_keyboard=True)

image_style_keyboard = ReplyKeyboardMarkup([
    ["Реализм", "Мультяшный"],
    ["Акварель", "Киберпанк"],
    ["Свой стиль"],
    ["Назад"]
], resize_keyboard=True)

period_keyboard = ReplyKeyboardMarkup([
    ["Неделя", "Месяц"],
    ["Ввести свой период"],
    ["Назад в главное меню"]
], resize_keyboard=True)

freq_week_keyboard = ReplyKeyboardMarkup([
    ["1 раз в день", "2 раза в неделю", "3 раза в неделю"],
    ["1 раз в неделю"],
    ["Назад"]
], resize_keyboard=True)

freq_month_keyboard = ReplyKeyboardMarkup([
    ["1 раз в день", "2 раза в неделю", "3 раза в неделю"],
    ["1 раз в неделю", "2 раза в месяц"],
    ["Назад"]
], resize_keyboard=True)


def scrub_pii(text: str):
    text = re.sub(r'\+\d[\d\s\-\(\)]{8,}', '[телефон]', text)
    text = re.sub(r'[\w\.-]+@[\d\w\.-]+', '[email]', text)
    text = re.sub(r'\b\d{1,3}\.\d+\s*,\s*-?\d{1,3}\.\d+\b', '[координаты]', text)
    return text, []


class BotHandlers:
    def __init__(self, text_service: TextService, image_service: ImageService, attachment_service: AttachmentService):
        self.text_service = text_service
        self.image_service = image_service
        self.attachment_service = attachment_service

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data.clear()
        context.user_data['nco_info'] = {
            'name': '', 'description': '', 'activities': '',
            'audience': '', 'website': ''
        }
        await update.message.reply_text(
            "Привет! Я помогу создавать посты и картинки для НКО\n\n"
            "Загрузи фото или документ — я извлеку текст и сделаю пост!\n"
            "Или выбери действие ниже.",
            reply_markup=main_keyboard
        )

    async def group_start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['active_session'] = True
        context.user_data['session_user_id'] = update.effective_user.id
        await update.message.reply_text(
            "Готов работать в группе! Загружай файлы или выбирай действие.",
            reply_markup=main_keyboard,
            reply_to_message_id=update.message.message_id
        )

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.chat.type in ['group', 'supergroup']:
            if not context.user_data.get('active_session') or update.effective_user.id != context.user_data.get('session_user_id'):
                return

        reply_kwargs = {}
        if update.message.chat.type in ['group', 'supergroup']:
            reply_kwargs['reply_to_message_id'] = update.message.message_id

        # ── ВЛОЖЕНИЯ (фото/документ) ───────────────────────────────────────
        if update.message.photo or update.message.document:
            await update.message.reply_text("Анализирую вложение...", **reply_kwargs)
            content = await self.attachment_service.process_attachment(update.message)
            if content and content.strip():
                context.user_data['last_prompt'] = content
                context.user_data['waiting'] = 'select_style'
                await update.message.reply_text(
                    "Готово!\n\nВыбери стиль для поста:",
                    reply_markup=style_keyboard,
                    **reply_kwargs
                )
            else:
                await update.message.reply_text(
                    "Не удалось извлечь текст.",
                    reply_markup=main_keyboard,
                    **reply_kwargs
                )
            return

        text = update.message.text.strip()
        scrubbed, _ = scrub_pii(text)
        nco_info = context.user_data.get('nco_info', {})
        state = context.user_data.get('state')
        waiting = context.user_data.get('waiting')

        # ── НАЗАД В ГЛАВНОЕ МЕНЮ ───────────────────────────────────────
        if text == "Назад в главное меню":
            context.user_data.clear()
            context.user_data['nco_info'] = {}
            await update.message.reply_text("Возвращаюсь в главное меню", reply_markup=main_keyboard, **reply_kwargs)
            return

        # ── НАЗАД ───────────────────────────────────────────────────────
        if text == "Назад":
            if waiting == 'select_style':
                context.user_data['waiting'] = 'text_mode'
                await update.message.reply_text("Режим:", reply_markup=text_mode_keyboard, **reply_kwargs)
            elif waiting == 'text_prompt':
                context.user_data['waiting'] = 'select_post_type' if context.user_data.get('text_mode') == 'structured' else 'text_mode'
                await update.message.reply_text(
                    "Выбери:",
                    reply_markup=post_type_keyboard if context.user_data.get('text_mode') == 'structured' else text_mode_keyboard,
                    **reply_kwargs
                )
            elif waiting == 'select_post_type':
                context.user_data['waiting'] = 'text_mode'
                await update.message.reply_text("Режим:", reply_markup=text_mode_keyboard, **reply_kwargs)
            elif waiting == 'image_style':
                context.user_data['waiting'] = 'image_prompt'
                await update.message.reply_text("Опиши картинку:", reply_markup=back_to_main_keyboard, **reply_kwargs)
            elif waiting == 'custom_image_style':
                context.user_data['waiting'] = 'image_style'
                await update.message.reply_text("Стиль:", reply_markup=image_style_keyboard, **reply_kwargs)
            elif waiting == 'plan_freq':
                context.user_data['waiting'] = 'plan_period'
                await update.message.reply_text("Период:", reply_markup=period_keyboard, **reply_kwargs)
            elif waiting == 'plan_end_date':
                context.user_data['waiting'] = 'plan_start_date'
                await update.message.reply_text("Начало:", reply_markup=back_only_keyboard, **reply_kwargs)
            elif waiting == 'plan_start_date':
                context.user_data['waiting'] = 'plan_period'
                await update.message.reply_text("Период:", reply_markup=period_keyboard, **reply_kwargs)
            elif waiting == 'plan_period':
                context.user_data['waiting'] = 'plan_theme'
                await update.message.reply_text("Тема:", reply_markup=back_to_main_keyboard, **reply_kwargs)
            return

        # ── НКО ─────────────────────────────────────────────────────────
        if text == "Предоставить информацию об НКО":
            context.user_data['state'] = 'nco_name'
            await update.message.reply_text("Название НКО?", reply_markup=back_skip_to_main_keyboard, **reply_kwargs)
            return

        if state == 'nco_name':
            nco_info['name'] = scrubbed
            context.user_data['state'] = 'nco_desc'
            await update.message.reply_text("Миссия?", reply_markup=back_skip_keyboard, **reply_kwargs)
            return
        if state == 'nco_desc':
            nco_info['description'] = scrubbed
            context.user_data['state'] = 'nco_act'
            await update.message.reply_text("Деятельность?", reply_markup=back_skip_keyboard, **reply_kwargs)
            return
        if state == 'nco_act':
            nco_info['activities'] = scrubbed
            context.user_data['state'] = 'nco_audience'
            await update.message.reply_text("Аудитория?", reply_markup=back_skip_keyboard, **reply_kwargs)
            return
        if state == 'nco_audience':
            nco_info['audience'] = scrubbed
            context.user_data['state'] = 'nco_website'
            await update.message.reply_text("Сайт?", reply_markup=back_skip_keyboard, **reply_kwargs)
            return
        if state == 'nco_website':
            nco_info['website'] = scrubbed
            context.user_data['state'] = None
            await update.message.reply_text("Инфо сохранена!", reply_markup=main_keyboard, **reply_kwargs)
            return

        if text == "Пропустить" and state:
            if state == 'nco_name': nco_info['name'] = ''; context.user_data['state'] = 'nco_desc'
            elif state == 'nco_desc': nco_info['description'] = ''; context.user_data['state'] = 'nco_act'
            elif state == 'nco_act': nco_info['activities'] = ''; context.user_data['state'] = 'nco_audience'
            elif state == 'nco_audience': nco_info['audience'] = ''; context.user_data['state'] = 'nco_website'
            elif state == 'nco_website':
                nco_info['website'] = ''
                context.user_data['state'] = None
                await update.message.reply_text("Готово!", reply_markup=main_keyboard, **reply_kwargs)
                return
            await update.message.reply_text("Пропущено", reply_markup=back_skip_keyboard, **reply_kwargs)
            return

        # ── ГЕНЕРАЦИЯ ТЕКСТА ───────────────────────────────────────────
        if text == "Генерация текста":
            context.user_data['waiting'] = 'text_mode'
            await update.message.reply_text("Режим:", reply_markup=text_mode_keyboard, **reply_kwargs)
            return

        if waiting == 'text_mode':
            if text == "Свободный текст":
                context.user_data['text_mode'] = 'free'
                context.user_data['waiting'] = 'text_prompt'
                await update.message.reply_text("Введи запрос:", reply_markup=back_to_main_keyboard, **reply_kwargs)
            elif text == "Структурированная форма":
                context.user_data['text_mode'] = 'structured'
                context.user_data['waiting'] = 'select_post_type'
                await update.message.reply_text("Тип поста:", reply_markup=post_type_keyboard, **reply_kwargs)
            return

        if waiting == 'select_post_type':
            types = {"Анонс": "Анонс", "Новости": "Новость", "Призыв к действию": "Призыв", "Отчет": "Отчёт"}
            if text in types:
                context.user_data['post_type'] = types[text]
                context.user_data['waiting'] = 'text_prompt'
                await update.message.reply_text("О чём пост?", reply_markup=back_to_main_keyboard, **reply_kwargs)
            return

        if waiting == 'text_prompt':
            context.user_data['last_prompt'] = scrubbed
            context.user_data['waiting'] = 'select_style'
            await update.message.reply_text("Стиль:", reply_markup=style_keyboard, **reply_kwargs)
            return

        if waiting == 'select_style':
            styles = {"Разговорный": "разговорный", "Официальный": "официальный", "Художественный": "поэтичный", "Без стиля": None}
            if text in styles:
                style = styles[text]
                prompt = context.user_data.get('last_prompt', '')
                post_type = context.user_data.get('post_type', '')
                full_prompt = f"{post_type}. {prompt}" if post_type else prompt
                await update.message.reply_text("Готово!", **reply_kwargs)
                await update.message.reply_text("Генерирую...", **reply_kwargs)
                result = self.text_service.generate_text(full_prompt, nco_info, style)
                await update.message.reply_text(result, reply_markup=main_keyboard, **reply_kwargs)
                context.user_data.clear()
                context.user_data['nco_info'] = nco_info
            return

        # ── ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЯ ───────────────────────────────────────
        if text == "Генерация изображения":
            context.user_data['waiting'] = 'image_prompt'
            await update.message.reply_text("Опиши:", reply_markup=back_to_main_keyboard, **reply_kwargs)
            return

        if waiting == 'image_prompt':
            context.user_data['image_prompt'] = scrubbed
            context.user_data['waiting'] = 'image_style'
            await update.message.reply_text("Стиль:", reply_markup=image_style_keyboard, **reply_kwargs)
            return

        if waiting == 'image_style':
            styles = {"Реализм": "реализм", "Мультяшный": "мультяшный", "Акварель": "акварель", "Киберпанк": "киберпанк"}
            if text in styles:
                style = styles[text]
                await update.message.reply_text("Готово!", **reply_kwargs)
                await update.message.reply_text("Генерирую...", **reply_kwargs)
                img = await self.image_service.generate_image(context.user_data['image_prompt'], nco_info, style)
                if img:
                    await update.message.reply_photo(photo=img, reply_markup=main_keyboard, **reply_kwargs)
                else:
                    await update.message.reply_text("Ошибка генерации", reply_markup=main_keyboard, **reply_kwargs)
                context.user_data.clear()
                context.user_data['nco_info'] = nco_info
            elif text == "Свой стиль":
                context.user_data['waiting'] = 'custom_image_style'
                await update.message.reply_text("Введи стиль:", reply_markup=back_only_keyboard, **reply_kwargs)
            return

        if waiting == 'custom_image_style':
            style = scrubbed
            await update.message.reply_text("Готово!", **reply_kwargs)
            await update.message.reply_text("Генерирую...", **reply_kwargs)
            img = await self.image_service.generate_image(context.user_data['image_prompt'], nco_info, style)
            if img:
                await update.message.reply_photo(photo=img, reply_markup=main_keyboard, **reply_kwargs)
            else:
                await update.message.reply_text("Ошибка генерации", reply_markup=main_keyboard, **reply_kwargs)
            context.user_data.clear()
            context.user_data['nco_info'] = nco_info
            return

        # ── РЕДАКТОР ТЕКСТА ─────────────────────────────────────────────
        if text == "Редактор текста":
            context.user_data['waiting'] = 'edit_text'
            await update.message.reply_text("Введи текст:", reply_markup=back_to_main_keyboard, **reply_kwargs)
            return

        if waiting == 'edit_text':
            await update.message.reply_text("Готово!", **reply_kwargs)
            await update.message.reply_text("Улучшаю...", **reply_kwargs)
            result = self.text_service.edit_text(scrubbed, nco_info)
            await update.message.reply_text(result, reply_markup=main_keyboard, **reply_kwargs)
            context.user_data['waiting'] = None
            return

        # ── КОНТЕНТ-ПЛАН ───────────────────────────────────────────────
        if text == "Контент-план":
            context.user_data['waiting'] = 'plan_theme'
            await update.message.reply_text("Тема:", reply_markup=back_to_main_keyboard, **reply_kwargs)
            return

        if waiting == 'plan_theme':
            context.user_data['plan_theme'] = scrubbed
            context.user_data['waiting'] = 'plan_period'
            await update.message.reply_text("Период:", reply_markup=period_keyboard, **reply_kwargs)
            return

        if waiting == 'plan_period':
            if text == "Неделя":
                context.user_data['plan_period'] = "неделя"
            elif text == "Месяц":
                context.user_data['plan_period'] = "месяц"
            elif text == "Ввести свой период":
                context.user_data['waiting'] = 'plan_start_date'
                await update.message.reply_text("Начало (дд.мм.гггг):", reply_markup=back_only_keyboard, **reply_kwargs)
                return
            else:
                return
            context.user_data['waiting'] = 'plan_freq'
            await update.message.reply_text(
                "Частота:",
                reply_markup=freq_week_keyboard if context.user_data['plan_period'] == "неделя" else freq_month_keyboard,
                **reply_kwargs
            )
            return

        if waiting == 'plan_start_date':
            try:
                start = datetime.strptime(text, "%d.%m.%Y").date()
                context.user_data['plan_start_date'] = start
                context.user_data['waiting'] = 'plan_end_date'
                await update.message.reply_text("Конец:", reply_markup=back_only_keyboard, **reply_kwargs)
            except:
                await update.message.reply_text("Формат: 15.11.2025", reply_markup=back_only_keyboard, **reply_kwargs)
            return

        if waiting == 'plan_end_date':
            try:
                end = datetime.strptime(text, "%d.%m.%Y").date()
                start = context.user_data['plan_start_date']
                if end < start:
                    await update.message.reply_text("Конец позже начала", reply_markup=back_only_keyboard, **reply_kwargs)
                    return
                context.user_data['plan_end_date'] = end
                context.user_data['plan_period'] = "custom"
                context.user_data['waiting'] = 'plan_freq'
                await update.message.reply_text(
                    "Частота:",
                    reply_markup=freq_week_keyboard if (end - start).days <= 7 else freq_month_keyboard,
                    **reply_kwargs
                )
            except:
                await update.message.reply_text("Формат: 30.11.2025", reply_markup=back_only_keyboard, **reply_kwargs)
            return

        if waiting == 'plan_freq':
            freq = text
            period = context.user_data['plan_period']
            theme = context.user_data['plan_theme']
            start = datetime.now().date() if period != "custom" else context.user_data['plan_start_date']
            end = None if period != "custom" else context.user_data['plan_end_date']

            await update.message.reply_text("Готово!", **reply_kwargs)
            await update.message.reply_text("Генерирую план...", **reply_kwargs)
            plan = self.text_service.generate_content_plan(period, freq, nco_info, start, end, theme)
            await update.message.reply_text(f"Контент-план:\n\n{plan}", reply_markup=main_keyboard, **reply_kwargs)
            context.user_data.clear()
            context.user_data['nco_info'] = nco_info
            return

        # ── ПО УМОЛЧАНИЮ ───────────────────────────────────────────────
        await update.message.reply_text("Выбери действие:", reply_markup=main_keyboard, **reply_kwargs)