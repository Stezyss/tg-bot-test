# handlers.py
import re
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from text_service import TextService
from image_service import ImageService
from attachment_service import AttachmentService
from db import Database


# ───── ДИНАМИЧЕСКАЯ ГЛАВНАЯ КЛАВИАТУРА ─────────────────────────────────────
def get_main_keyboard(has_nco_data: bool) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        ["Генерация текста", "Генерация изображения"],
        ["Редактор текста", "Контент-план"],
        ["Изменить информацию об НКО" if has_nco_data else "Предоставить информацию об НКО"]
    ], resize_keyboard=True)


back_to_main_keyboard = ReplyKeyboardMarkup([["Назад в главное меню"]], resize_keyboard=True)
back_skip_clear_keyboard = ReplyKeyboardMarkup([["Назад", "Пропустить", "Очистить"]], resize_keyboard=True)
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

edit_action_keyboard = ReplyKeyboardMarkup([
    ["Увеличить текст", "Сократи текст"],
    ["Исправить ошибки", "Изменить стиль"],
    ["Перефразировать"],
    ["Назад в главное меню"]
], resize_keyboard=True)


def scrub_pii(text: str):
    text = re.sub(r'\+?\d[\d\s\-\(\)]{8,}', '[телефон]', text)
    text = re.sub(r'[\w\.-]+@[\d\w\.-]+', '[email]', text)
    text = re.sub(r'\b\d{1,3}\.\d+\s*,\s*-?\d{1,3}\.\d+\b', '[координаты]', text)
    return text, []


class BotHandlers:
    def __init__(self, text_service: TextService, image_service: ImageService,
                 attachment_service: AttachmentService, database: Database):
        self.text_service = text_service
        self.image_service = image_service
        self.attachment_service = attachment_service
        self.database = database

    def _get_nco_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> dict:
        user_id = update.effective_user.id
        db_info = self.database.get_nco_info(user_id) or {}
        return {
            'name': db_info.get('name', ''),
            'activities': db_info.get('activities', ''),
            'audience': db_info.get('audience', ''),
            'website': db_info.get('website', '')
        }

    async def _save_single_field_and_next(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                          field: str, value: str, next_waiting: str, next_label: str, **reply_kwargs):
        """Сохраняет поле и переходит к следующему шагу БЕЗ лишних сообщений"""
        user_id = update.effective_user.id
        current = self._get_nco_info(update, context)
        current[field] = value
        self.database.save_nco_info(
            user_id=user_id,
            nco_name=current.get('name'),
            activities=current.get('activities'),
            audience=current.get('audience'),
            website=current.get('website')
        )
        context.user_data['waiting'] = next_waiting
        await update.message.reply_text(next_label, reply_markup=back_skip_clear_keyboard, **reply_kwargs)

    async def _finish_nco_form(self, update: Update, context: ContextTypes.DEFAULT_TYPE, **reply_kwargs):
        """Завершает форму и возвращает в главное меню БЕЗ сообщений"""
        context.user_data['waiting'] = None
        nco = self._get_nco_info(update, context)
        has_data = any(nco.values())
        await update.message.reply_text("Готово.", reply_markup=get_main_keyboard(has_data), **reply_kwargs)

    async def _show_nco_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, **reply_kwargs):
        nco = self._get_nco_info(update, context)
        has_data = any(nco.values())
        await update.message.reply_text(
            "Информация об НКО:",
            reply_markup=get_main_keyboard(has_data),
            **reply_kwargs
        )

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data.clear()
        nco = self._get_nco_info(update, context)
        has_data = any(nco.values())
        await update.message.reply_text(
            "Привет! Я помогу создавать посты и картинки для НКО\n\n"
            "Загрузи фото или документ — я извлеку текст и сделаю пост!\n"
            "Или выбери действие ниже.",
            reply_markup=get_main_keyboard(has_data)
        )

    async def group_start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['active_session'] = True
        context.user_data['session_user_id'] = update.effective_user.id
        nco = self._get_nco_info(update, context)
        has_data = any(nco.values())
        await update.message.reply_text(
            "Готов работать в группе! Загружай файлы или выбирай действие.",
            reply_markup=get_main_keyboard(has_data),
            reply_to_message_id=update.message.message_id
        )

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.chat.type in ['group', 'supergroup']:
            if not context.user_data.get('active_session') or \
               update.effective_user.id != context.user_data.get('session_user_id'):
                return

        reply_kwargs = {}
        if update.message.chat.type in ['group', 'supergroup']:
            reply_kwargs['reply_to_message_id'] = update.message.message_id

        # ── ВЛОЖЕНИЯ ─────────────────────────────────────────────────────
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
                    reply_markup=get_main_keyboard(True),
                    **reply_kwargs
                )
            return

        text = update.message.text.strip()
        scrubbed, _ = scrub_pii(text)
        waiting = context.user_data.get('waiting')

        # ── НАЗАД В ГЛАВНОЕ МЕНЮ ───────────────────────────────────────
        if text == "Назад в главное меню":
            context.user_data.clear()
            await self._show_nco_menu(update, context, **reply_kwargs)
            return

        # ── НАЗАД ───────────────────────────────────────────────────────
        if text == "Назад":
            if waiting in ['nco_activities', 'nco_audience', 'nco_website']:
                prev = {
                    'nco_activities': 'nco_name',
                    'nco_audience': 'nco_activities',
                    'nco_website': 'nco_audience'
                }[waiting]
                context.user_data['waiting'] = prev
                label = {
                    'nco_name': "Название НКО",
                    'nco_activities': "Деятельность НКО",
                    'nco_audience': "Целевая аудитория"
                }[prev]
                await update.message.reply_text(f"{label}:", reply_markup=back_skip_clear_keyboard, **reply_kwargs)
            elif waiting in ['edit_action', 'edit_style', 'plan_period', 'plan_freq']:
                context.user_data['waiting'] = None
                await self._show_nco_menu(update, context, **reply_kwargs)
            return

        # ── ПРОПУСТИТЬ / ОЧИСТИТЬ ───────────────────────────────────────
        if text == "Пропустить" and waiting in ['nco_name', 'nco_activities', 'nco_audience', 'nco_website']:
            field_map = {
                'nco_name': 'name',
                'nco_activities': 'activities',
                'nco_audience': 'audience',
                'nco_website': 'website'
            }
            next_map = {
                'nco_name': ('nco_activities', "Деятельность НКО"),
                'nco_activities': ('nco_audience', "Целевая аудитория"),
                'nco_audience': ('nco_website', "Сайт НКО"),
                'nco_website': (None, None)
            }
            field = field_map[waiting]
            next_waiting, next_label = next_map[waiting]
            current = self._get_nco_info(update, context)
            await self._save_single_field_and_next(update, context, field, current[field], next_waiting, next_label, **reply_kwargs)
            if next_waiting is None:
                await self._finish_nco_form(update, context, **reply_kwargs)
            return

        if text == "Очистить" and waiting in ['nco_name', 'nco_activities', 'nco_audience', 'nco_website']:
            field_map = {
                'nco_name': 'name',
                'nco_activities': 'activities',
                'nco_audience': 'audience',
                'nco_website': 'website'
            }
            next_map = {
                'nco_name': ('nco_activities', "Деятельность НКО"),
                'nco_activities': ('nco_audience', "Целевая аудитория"),
                'nco_audience': ('nco_website', "Сайт НКО"),
                'nco_website': (None, None)
            }
            field = field_map[waiting]
            next_waiting, next_label = next_map[waiting]
            await self._save_single_field_and_next(update, context, field, "", next_waiting, next_label, **reply_kwargs)
            if next_waiting is None:
                await self._finish_nco_form(update, context, **reply_kwargs)
            return

        # ── ИЗМЕНЕНИЕ ИНФОРМАЦИИ ОБ НКО ─────────────────────────────────
        if text in ["Предоставить информацию об НКО", "Изменить информацию об НКО"]:
            context.user_data['waiting'] = 'nco_name'
            await update.message.reply_text("Название НКО:", reply_markup=back_skip_clear_keyboard, **reply_kwargs)
            return

        if waiting == 'nco_name':
            await self._save_single_field_and_next(update, context, 'name', scrubbed, 'nco_activities', "Деятельность НКО", **reply_kwargs)
            return

        if waiting == 'nco_activities':
            await self._save_single_field_and_next(update, context, 'activities', scrubbed, 'nco_audience', "Целевая аудитория", **reply_kwargs)
            return

        if waiting == 'nco_audience':
            await self._save_single_field_and_next(update, context, 'audience', scrubbed, 'nco_website', "Сайт НКО", **reply_kwargs)
            return

        if waiting == 'nco_website':
            await self._save_single_field_and_next(update, context, 'website', scrubbed, None, None, **reply_kwargs)
            await self._finish_nco_form(update, context, **reply_kwargs)
            return

        # ── ГЕНЕРАЦИЯ ТЕКСТА ───────────────────────────────────────────
        if text == "Генерация текста":
            context.user_data['waiting'] = 'text_mode'
            await update.message.reply_text("Выбери режим:", reply_markup=text_mode_keyboard, **reply_kwargs)
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
            post_types = {"Анонс": "анонс события", "Новости": "новости", "Призыв к действию": "призыв к действию", "Отчет": "отчет"}
            if text in post_types:
                context.user_data['post_type'] = post_types[text]
                context.user_data['waiting'] = 'text_prompt'
                await update.message.reply_text("Опиши детали:", reply_markup=back_to_main_keyboard, **reply_kwargs)
            return

        if waiting == 'text_prompt':
            prompt = scrubbed
            if context