# handlers/handlers_plan.py
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime, timedelta


period_kb = ReplyKeyboardMarkup([["Неделя", "Месяц"], ["Ввести свой период"], ["Назад в главное меню"]], resize_keyboard=True)
freq_week = ReplyKeyboardMarkup([["1 раз в день", "2 раза в неделю", "3 раза в неделю"], ["1 раз в неделю"], ["Назад"]], resize_keyboard=True)
freq_month = ReplyKeyboardMarkup([["1 раз в день", "2 раза в неделю", "3 раза в неделю"], ["1 раз в неделю", "2 раза в месяц"], ["Назад"]], resize_keyboard=True)


class PlanHandler:
    def __init__(self, text_service):
        self.ts = text_service

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE, **kw):
        context.user_data['waiting'] = 'plan_theme'
        await update.message.reply_text("Тема плана:", reply_markup=ReplyKeyboardMarkup([["Назад в главное меню"]], resize_keyboard=True), **kw)

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, nco_info: dict, **kw):
        w = context.user_data.get('waiting')
        if w == 'plan_theme':
            context.user_data['plan_theme'] = text
            context.user_data['waiting'] = 'plan_period'
            await update.message.reply_text("Период:", reply_markup=period_kb, **kw)
            return True

        if w == 'plan_period':
            if text in ["Неделя", "Месяц"]:
                context.user_data['plan_period'] = "неделя" if text == "Неделя" else "месяц"
                context.user_data['waiting'] = 'plan_freq'
                await update.message.reply_text("Частота:", reply_markup=freq_week if text == "Неделя" else freq_month, **kw)
            elif text == "Ввести свой период":
                context.user_data['waiting'] = 'plan_start'
                await update.message.reply_text("Начало (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup([["Назад"]], resize_keyboard=True), **kw)
            return True

        if w == 'plan_start':
            try:
                start = datetime.strptime(text, "%d.%m.%Y").date()
                context.user_data.update({'plan_start': start, 'waiting': 'plan_end'})
                await update.message.reply_text("Конец (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup([["Назад"]], resize_keyboard=True), **kw)
            except:
                await update.message.reply_text("Формат: 15.11.2025", **kw)
            return True

        if w == 'plan_end':
            try:
                end = datetime.strptime(text, "%d.%m.%Y").date()
                start = context.user_data['plan_start']
                if end < start:
                    await update.message.reply_text("Конец позже начала", **kw); return True
                context.user_data.update({'plan_end': end, 'plan_period': 'custom', 'waiting': 'plan_freq'})
                await update.message.reply_text("Частота:", reply_markup=freq_week if (end-start).days <= 7 else freq_month, **kw)
            except:
                await update.message.reply_text("Формат: 30.11.2025", **kw)
            return True

        if w == 'plan_freq':
            await update.message.reply_text("Генерирую...", **kw)
            period = context.user_data['plan_period']
            start = datetime.now().date() if period != 'custom' else context.user_data['plan_start']
            end = None if period != 'custom' else context.user_data['plan_end']
            plan = self.ts.generate_content_plan(period, text, nco_info, start, end, context.user_data['plan_theme'])
            from .handlers_nco import get_main_keyboard
            await update.message.reply_text(f"План:\n\n{plan}", reply_markup=get_main_keyboard(True), **kw)
            context.user_data.clear()
            return True
        return False