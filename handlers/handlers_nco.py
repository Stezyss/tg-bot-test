# handlers/handlers_nco.py
import re
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from db import Database


def clean_url(text: str) -> str:
    """Очищает URL от протокола, www, скобок, [ ] — оставляет только домен"""
    if not text:
        return ""
    # Убираем http, https, www
    text = re.sub(r'^(https?://)?(www\.)?', '', text, flags=re.IGNORECASE)
    # Убираем путь, параметры, якоря
    text = text.split('/')[0].split('?')[0].split('#')[0]
    # Убираем скобки, кавычки
    text = re.sub(r'[()\[\]"\']', '', text)
    # Убираем пробелы
    return text.strip()


def get_main_keyboard(has_data: bool) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        ["Генерация текста", "Генерация изображения"],
        ["Редактор текста", "Контент-план"],
        ["Изменить информацию об НКО" if has_data else "Предоставить информацию об НКО"],
        ["Просмотреть информацию об НКО"]
    ], resize_keyboard=True)


back_skip_clear = ReplyKeyboardMarkup([["Назад", "Пропустить", "Очистить"]], resize_keyboard=True)
back_main = ReplyKeyboardMarkup([["Назад в главное меню"]], resize_keyboard=True)


class NCOHandler:
    def __init__(self, database: Database):
        self.db = database

    def _get(self, user_id: int) -> dict:
        info = self.db.get_nco_info(user_id) or {}
        return {k: info.get(k, '') for k in ['name', 'activities', 'audience', 'website']}

    async def save_field(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                         field: str, value: str, next_step: str, next_label: str, **kw):
        user_id = update.effective_user.id
        current = self._get(user_id)

        # ← ОЧИСТКА САЙТА
        if field == 'website':
            value = clean_url(value)

        current[field] = value

        self.db.save_nco_info(
            user_id=user_id,
            nco_name=current['name'],
            activities=current['activities'],
            audience=current['audience'],
            website=current['website']
        )

        if next_step:
            context.user_data['waiting'] = next_step
            await update.message.reply_text(next_label, reply_markup=back_skip_clear, **kw)
        else:
            context.user_data['waiting'] = None
            await update.message.reply_text("Готово.", reply_markup=get_main_keyboard(True), **kw)

    async def start_nco_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE, **kw):
        context.user_data['waiting'] = 'nco_name'
        await update.message.reply_text("Название НКО:", reply_markup=back_skip_clear, **kw)

    async def show_nco_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE, **kw):
        info = self._get(update.effective_user.id)
        lines = []
        for key, label in [
            ('name', 'Название'),
            ('activities', 'Деятельность'),
            ('audience', 'Аудитория'),
            ('website', 'Сайт')
        ]:
            value = info[key].strip()
            if key == 'website' and value:
                value = clean_url(value)  # ← ОЧИЩАЕМ ПРИ ПОКАЗЕ
            lines.append(f"• {label}: {value if value else '—'}")
        text = "Информация об НКО:\n\n" + "\n".join(lines)
        has_data = any(info.values())
        await update.message.reply_text(text, reply_markup=get_main_keyboard(has_data), **kw)

    async def handle_nco(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, **kw):
        waiting = context.user_data.get('waiting')

        if text in ["Предоставить информацию об НКО", "Изменить информацию об НКО"]:
            return await self.start_nco_edit(update, context, **kw)

        if text == "Просмотреть информацию об НКО":
            return await self.show_nco_info(update, context, **kw)

        steps = {
            'nco_name': ('name', 'nco_activities', "Деятельность НКО"),
            'nco_activities': ('activities', 'nco_audience', "Целевая аудитория"),
            'nco_audience': ('audience', 'nco_website', "Сайт НКО"),
            'nco_website': ('website', None, None)
        }

        if waiting in steps:
            field, next_step, next_label = steps[waiting]
            if text == "Пропустить":
                value = self._get(update.effective_user.id)[field]
            elif text == "Очистить":
                value = ""
            else:
                value = text.strip()
            await self.save_field(update, context, field, value, next_step, next_label, **kw)
            return True

        return False

    async def back(self, update: Update, context: ContextTypes.DEFAULT_TYPE, **kw):
        waiting = context.user_data.get('waiting')
        if waiting in ['nco_activities', 'nco_audience', 'nco_website']:
            prev = {
                'nco_activities': 'nco_name',
                'nco_audience': 'nco_activities',
                'nco_website': 'nco_audience'
            }[waiting]
            label = {
                'nco_name': "Название НКО",
                'nco_activities': "Деятельность НКО",
                'nco_audience': "Целевая аудитория"
            }[prev]
            context.user_data['waiting'] = prev
            await update.message.reply_text(f"{label}:", reply_markup=back_skip_clear, **kw)
            return True
        return False

    def get_nco_info(self, update: Update) -> dict:
        raw = self._get(update.effective_user.id)
        cleaned = raw.copy()
        if cleaned.get('website'):
            cleaned['website'] = clean_url(cleaned['website'])
        return cleaned