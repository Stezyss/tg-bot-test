# handlers/handlers_nco.py
import re
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from db import Database


def clean_url(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'^(https?://)?(www\.)?', '', text, flags=re.IGNORECASE)
    text = text.split('/')[0].split('?')[0].split('#')[0]
    text = re.sub(r'[()\[\]"\']', '', text)
    return text.strip()


# ── КЛАВИАТУРЫ ───────────────────────────────────────────────────────
def get_main_keyboard(has_data: bool) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        ["📝 Генерация текста", "🎨 Генерация изображения"],
        ["✏️ Редактор текста", "📅 Контент-план"],
        ["👁️ Просмотреть информацию об НКО" if has_data else "➕ Предоставить информацию об НКО"]
    ], resize_keyboard=True)


def get_view_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✏️ Изменить информацию об НКО", callback_data="edit_nco")
    ]])


back_skip_clear = ReplyKeyboardMarkup([["⏭️ Пропустить", "🧹 Очистить"], ["🏠 Назад в главное меню"]], resize_keyboard=True)
back_skip_only = ReplyKeyboardMarkup([["⏭️ Пропустить"], ["🏠 Назад в главное меню"]], resize_keyboard=True)


class NCOHandler:
    def __init__(self, database: Database):
        self.db = database

    def _get(self, user_id: int) -> dict:
        info = self.db.get_nco_info(user_id) or {}
        return {k: info.get(k, '') for k in ['name', 'activities', 'audience', 'website']}

    def _has_data(self, user_id: int) -> bool:
        info = self._get(user_id)
        return any(v.strip() for v in info.values())

    async def save_field(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                         field: str, value: str, next_step: str, next_label: str, **kw):
        user_id = update.effective_user.id
        current = self._get(user_id)
        if field == 'website':
            value = clean_url(value)
        current[field] = value

        self.db.save_nco_info(
            user_id,
            current['name'],
            current['activities'],
            current['audience'],
            current['website']
        )

        if next_step:
            context.user_data['waiting'] = next_step
            markup = back_skip_clear if context.user_data.get('is_edit_mode') else back_skip_only
            await update.message.reply_text(next_label, reply_markup=markup, **kw)
        else:
            context.user_data['waiting'] = None
            context.user_data.pop('is_edit_mode', None)
            has_data = self._has_data(user_id)
            await update.message.reply_text("✅ Отлично! Всё сохранено.", reply_markup=get_main_keyboard(has_data), **kw)

    async def start_nco_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, is_edit: bool = False, **kw):
        context.user_data['waiting'] = 'nco_name'
        context.user_data['is_edit_mode'] = is_edit
        text = "📝 Введите новые данные об НКО\n\n*Название НКО:*" if is_edit else "👋 Давай заполним информацию о твоей НКО!\n\nЭто поможет мне создавать более подходящие посты и картинки.\n\n*Начнём с названия НКО:*"
        markup = back_skip_clear if is_edit else back_skip_only
        await update.message.reply_text(text, reply_markup=markup, parse_mode='Markdown', **kw)

    async def show_nco_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE, **kw):
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
            lines.append(f"• *{label}:* {value if value else '—'}")
        text = "📋 *Информация о вашей НКО:*\n\n" + "\n".join(lines)

        context.user_data.pop('waiting', None)
        context.user_data.pop('is_edit_mode', None)

        await update.message.reply_text(
            text,
            reply_markup=get_view_keyboard(),
            parse_mode='Markdown',
            **kw
        )

    async def handle_nco(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, **kw):
        waiting = context.user_data.get('waiting')
        user_id = update.effective_user.id

        # ── КНОПКИ: ПРЕДОСТАВИТЬ / ПРОСМОТРЕТЬ ───────────────────────
        if text == "➕ Предоставить информацию об НКО":
            return await self.start_nco_input(update, context, is_edit=False, **kw)

        if text == "👁️ Просмотреть информацию об НКО":
            return await self.show_nco_info(update, context, **kw)

        # ── РЕДАКТИРОВАНИЕ ПОЛЕЙ ─────────────────────────────────────
        steps = {
            'nco_name': ('name', 'nco_activities', "📝 *Деятельность НКО:*\n\nЧем занимается ваша организация? Опишите основные направления работы."),
            'nco_activities': ('activities', 'nco_audience', "🎯 *Целевая аудитория:*\n\nДля кого вы работаете? Кто ваши благополучатели, волонтёры, партнёры?"),
            'nco_audience': ('audience', 'nco_website', "🌐 *Сайт НКО:*\n\nУкажите адрес сайта (если есть). Можно пропустить."),
            'nco_website': ('website', None, None)
        }

        if waiting in steps:
            field, next_step, next_label = steps[waiting]

            # ← СПЕЦИАЛЬНО: "Назад" при вводе названия → в главное меню
            if text == "⬅️ Назад" and waiting == 'nco_name':
                context.user_data['waiting'] = None
                context.user_data.pop('is_edit_mode', None)
                has_data = self._has_data(user_id)
                await update.message.reply_text("👌 Возврат в главное меню.", reply_markup=get_main_keyboard(has_data), **kw)
                return True

            if text == "⏭️ Пропустить":
                value = self._get(user_id)[field]
            elif text == "🧹 Очистить" and context.user_data.get('is_edit_mode'):
                value = ""
            else:
                value = text.strip()

            await self.save_field(update, context, field, value, next_step, next_label, **kw)
            return True

        return False

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if query.data == "edit_nco":
            await query.edit_message_reply_markup(reply_markup=None)
            context.user_data['waiting'] = 'nco_name'
            context.user_data['is_edit_mode'] = True
            await query.message.reply_text(
                "📝 Введите новые данные об НКО\n\n*Название НКО:*",
                reply_markup=back_skip_clear,
                parse_mode='Markdown'
            )

    async def back(self, update: Update, context: ContextTypes.DEFAULT_TYPE, **kw):
        waiting = context.user_data.get('waiting')
        if waiting in ['nco_activities', 'nco_audience', 'nco_website']:
            prev = {
                'nco_activities': 'nco_name',
                'nco_audience': 'nco_activities',
                'nco_website': 'nco_audience'
            }[waiting]
            label = {
                'nco_name': "👤 *Название НКО:*",
                'nco_activities': "📝 *Деятельность НКО:*",
                'nco_audience': "🎯 *Целевая аудитория:*"
            }[prev]
            context.user_data['waiting'] = prev
            markup = back_skip_clear if context.user_data.get('is_edit_mode') else back_skip_only
            await update.message.reply_text(f"{label}", reply_markup=markup, parse_mode='Markdown', **kw)
            return True
        return False

    def get_nco_info(self, update: Update) -> dict:
        raw = self._get(update.effective_user.id)
        cleaned = raw.copy()
        if cleaned.get('website'):
            cleaned['website'] = clean_url(cleaned['website'])
        return cleaned

    def has_data(self, user_id: int) -> bool:
        return self._has_data(user_id)
