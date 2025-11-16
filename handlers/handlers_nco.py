"""
Обработчик, отвечающий за работу с информацией об НКО.

Функциональность модуля:
- ввод и редактирование данных об НКО (название, деятельность, аудитория, сайт);
- просмотр сохранённых данных;
- пошаговое заполнение с поддержкой «назад», «пропустить», «очистить»;
- работа как через текстовые сообщения, так и через inline-кнопки;
- очистка и стандартизация введённых URL.
"""

import re
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from db import Database

#  УТИЛИТЫ

def clean_url(text: str) -> str:
    """
    Очищает URL от протокола, www, параметров, слешей и лишних символов.

    Используется для хранения только домена.
    """
    if not text:
        return ""
    text = re.sub(r'^(https?://)?(www\.)?', '', text, flags=re.IGNORECASE)
    text = text.split('/')[0].split('?')[0].split('#')[0]
    text = re.sub(r'[()\[\]"\']', '', text)
    return text.strip()

#  КЛАВИАТУРЫ

def get_main_keyboard(has_data: bool) -> ReplyKeyboardMarkup:
    """
    Главное меню для пользователя.
    """
    return ReplyKeyboardMarkup([
        ["📝 Генерация текста", "🎨 Генерация изображения"],
        ["✏️ Редактор текста", "📅 Контент-план"],
        ["👁️ Просмотреть информацию об НКО" if has_data else "➕ Предоставить информацию об НКО"]
    ], resize_keyboard=True)


def get_view_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура под просмотром информации об НКО.
    """
    return InlineKeyboardMarkup([[InlineKeyboardButton("✏️ Изменить информацию об НКО", callback_data="edit_nco")]])

# Универсальные клавиатуры возврата/пропуска
back_skip_clear = ReplyKeyboardMarkup([["⏭️ Пропустить", "🧹 Очистить"], ["🏠 Назад в главное меню"]], resize_keyboard=True)
back_skip_only = ReplyKeyboardMarkup([["⏭️ Пропустить"], ["🏠 Назад в главное меню"]], resize_keyboard=True)

#  ОСНОВНОЙ КЛАСС-ОБРАБОТЧИК

class NCOHandler:
    """
    Обрабатывает ввод, редактирование и вывод информации об НКО.

    Взаимодействует с базой данных, хранит состояния диалога, 
    управляет пошаговым заполнением четырёх полей:
        - name
        - activities
        - audience
        - website
    """

    def __init__(self, database: Database):
        self.db = database

    # --- Вспомогательные методы ---
    def _get(self, user_id: int) -> dict:
        """Возвращает словарь с данными об НКО (или пустые строки по умолчанию)."""
        info = self.db.get_nco_info(user_id) or {}
        return {k: info.get(k, '') for k in ['name', 'activities', 'audience', 'website']}

    def _has_data(self, user_id: int) -> bool:
        """Проверяет, заполнено ли хотя бы одно поле."""
        info = self._get(user_id)
        return any(v.strip() for v in info.values())

    #  СОХРАНЕНИЕ ОТДЕЛЬНОГО ПОЛЯ

    async def save_field(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                         field: str, value: str, next_step: str, next_label: str, **kw):
        """
        Сохраняет отдельное поле и переводит на следующий шаг.

        field     — ключ поля в базе (name, activities, audience, website)
        value     — введённое пользователем значение
        next_step — имя следующего состояния
        next_label — текст для следующего вопроса
        """

        user_id = update.effective_user.id
        current = self._get(user_id)

        if field == 'website':
            value = clean_url(value)

        current[field] = value

        # Обновление записи в базе
        self.db.save_nco_info(
            user_id,
            current['name'],
            current['activities'],
            current['audience'],
            current['website']
        )

        # Если есть следующий шаг → продолжаем
        if next_step:
            context.user_data['waiting'] = next_step
            markup = back_skip_clear if context.user_data.get('is_edit_mode') else back_skip_only
            await update.message.reply_text(next_label, reply_markup=markup, **kw)
            return

        # Завершение
        context.user_data['waiting'] = None
        context.user_data.pop('is_edit_mode', None)
        has_data = self._has_data(user_id)
        await update.message.reply_text("✅ Отлично! Всё сохранено.", reply_markup=get_main_keyboard(has_data), **kw)

    #  ЗАПУСК ВВОДА ДАННЫХ ОБ НКО
    
    async def start_nco_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, is_edit: bool = False, **kw):
        """
        Начало заполнения данных об НКО.
        is_edit=True — режим редактирования.
        """

        context.user_data['waiting'] = 'nco_name'
        context.user_data['is_edit_mode'] = is_edit

        text = (
            "📝 Введите новые данные об НКО\n\n*Название НКО:*"
            if is_edit else
            "👋 Давай заполним информацию о твоей НКО!\n\nЭто поможет мне создавать более подходящие посты и картинки.\n\n*Начнём с названия НКО:*"
        )

        markup = back_skip_clear if is_edit else back_skip_only

        await update.message.reply_text(text, reply_markup=markup, parse_mode='Markdown', **kw)

    #  ПОКАЗ СОХРАНЁННЫХ ДАННЫХ

    async def show_nco_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE, **kw):
        """
        Отображает информацию об НКО в структурированном виде.
        """

        user_id = update.effective_user.id
        info = self._get(user_id)

        lines = []
        for key, label in [
            ('name', 'Название'),
            ('activities', 'Деятельность'),
            ('audience', 'Аудитория'),
            ('website', 'Сайт')
        ]:
            value = info[key].strip()
            if key == 'website' and value:
                value = clean_url(value)
            lines.append(f"• *{label}:* {value ifs value else '—'}")

        text = "📋 *Информация о вашей НКО:*\n\n" + "\n".join(lines)

        context.user_data.pop('waiting', None)
        context.user_data.pop('is_edit_mode', None)

        await update.message.reply_text(
            text,
            reply_markup=get_view_keyboard(),
            parse_mode='Markdown',
            **kw
        )

    #  ОБРАБОТКА ЛОГИКИ ВВОД

    async def handle_nco(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, **kw) -> bool:
        """
        Обрабатывает шаги заполнения/редактирования данных об НКО.
        """

        waiting = context.user_data.get('waiting')
        user_id = update.effective_user.id

        # Кнопки главного меню
        if text == "➕ Предоставить информацию об НКО":
            return await self.start
