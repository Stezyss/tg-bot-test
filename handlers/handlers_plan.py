# handlers/handlers_plan.py
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime, timedelta

# === Клавиатуры ===
period_kb = ReplyKeyboardMarkup([
    ["Неделя", "Месяц"],
    ["Ввести свой период"],
    ["Назад"]
], resize_keyboard=True)

# Частота для недели — сетка 2×2
freq_week = ReplyKeyboardMarkup([
    ["1 раз в день", "1 раз в неделю"],
    ["2 раза в неделю", "3 раза в неделю"],
    ["Назад"]
], resize_keyboard=True)

# Частота для месяца
freq_month = ReplyKeyboardMarkup([
    ["1 раз в день", "1 раз в неделю"],
    ["2 раза в неделю", "3 раза в неделю"],
    ["2 раза в месяц"],
    ["Назад"]
], resize_keyboard=True)

BACK_TO_MAIN = ReplyKeyboardMarkup([["Назад в главное меню"]], resize_keyboard=True)


class PlanHandler:
    def __init__(self, text_service):
        self.ts = text_service

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE, **kw):
        context.user_data['waiting'] = 'plan_theme'
        await update.message.reply_text(
            "Давай составим *контент-план*!\n\n"
            "Сначала напиши *тему*.\n"
            "Например: «Помощь бездомным животным» или «Эко-акции в парке».\n\n"
            "Я подберу идеи под твою НКО\n\n"
            "*Работа с файлами и изображениями не поддерживается.*",
            reply_markup=BACK_TO_MAIN,
            parse_mode='Markdown',
            **kw
        )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, nco_info: dict, **kw):
        w = context.user_data.get('waiting')

        # === Тема ===
        if w == 'plan_theme':
            if text == "Назад в главное меню":
                context.user_data.clear()
                from .handlers_nco import get_main_keyboard
                await update.message.reply_text("Хорошо, возвращаемся. Если план нужен — просто скажи!", reply_markup=get_main_keyboard(True), **kw)
                return True
            context.user_data['plan_theme'] = text
            context.user_data['waiting'] = 'plan_period'
            await update.message.reply_text(
                f"Тема: *{text}*.\n\n"
                "Теперь выбери *период*:",
                reply_markup=period_kb,
                parse_mode='Markdown',
                **kw
            )
            return True

        # === Период ===
        if w == 'plan_period':
            if text == "Назад":
                context.user_data['waiting'] = 'plan_theme'
                await update.message.reply_text("Хорошо, вернёмся к теме.", reply_markup=BACK_TO_MAIN, parse_mode='Markdown', **kw)
                return True

            periods = {"Неделя": "неделя", "Месяц": "месяц"}
            if text in periods:
                context.user_data.update({'plan_period': periods[text], 'waiting': 'plan_freq'})
                kb = freq_week if text == "Неделя" else freq_month
                await update.message.reply_text(
                    f"Период: *{text}*.\n\n"
                    "Теперь выбери *частоту публикаций*:",
                    reply_markup=kb,
                    parse_mode='Markdown',
                    **kw
                )
            elif text == "Ввести свой период":
                context.user_data['waiting'] = 'plan_start'
                await update.message.reply_text(
                    "Отлично! Введи *начало* периода.\n"
                    "Пример: 01.12.2025\n\n"
                    "Или сегодня — нажми «Пропустить».",
                    reply_markup=ReplyKeyboardMarkup([["Пропустить", "Назад"]], resize_keyboard=True),
                    parse_mode='Markdown',
                    **kw
                )
            return True

        # === Начало (custom) ===
        if w == 'plan_start':
            if text == "Назад":
                context.user_data['waiting'] = 'plan_period'
                await update.message.reply_text("Хорошо, вернёмся к периоду.", reply_markup=period_kb, parse_mode='Markdown', **kw)
                return True

            start = datetime.now().date() if text == "Пропустить" else datetime.strptime(text, "%d.%m.%Y").date()
            context.user_data.update({'plan_start': start, 'waiting': 'plan_end'})
            await update.message.reply_text(
                f"Начало: *{start.strftime('%d.%m.%Y')}*.\n\n"
                "Теперь введи *конец* периода.\n"
                "Пример: 30.12.2025",
                reply_markup=ReplyKeyboardMarkup([["Назад"]], resize_keyboard=True),
                parse_mode='Markdown',
                **kw
            )
            return True

        # === Конец (custom) ===
        if w == 'plan_end':
            if text == "Назад":
                context.user_data['waiting'] = 'plan_start'
                await update.message.reply_text("Хорошо, вернёмся к началу.", reply_markup=ReplyKeyboardMarkup([["Пропустить", "Назад"]], resize_keyboard=True), parse_mode='Markdown', **kw)
                return True

            try:
                end = datetime.strptime(text, "%d.%m.%Y").date()
                if end <= context.user_data['plan_start']:
                    raise ValueError("Конец должен быть после начала.")
                days = (end - context.user_data['plan_start']).days
                context.user_data.update({'plan_end': end, 'plan_period': 'custom', 'waiting': 'plan_freq'})
                kb = freq_week if days <= 7 else freq_month
                await update.message.reply_text(
                    f"Конец: *{end.strftime('%d.%m.%Y')}*.\n\n"
                    "Теперь выбери *частоту публикаций*:",
                    reply_markup=kb,
                    parse_mode='Markdown',
                    **kw
                )
            except ValueError as e:
                await update.message.reply_text(f"Ошибка: {str(e)}. Пример: 30.11.2025", **kw)
            return True

        # === Частота ===
        if w == 'plan_freq':
            if text == "Назад":
                period = context.user_data.get('plan_period')
                if period == 'custom':
                    context.user_data['waiting'] = 'plan_end'
                    await update.message.reply_text("Хорошо, вернёмся к дате конца.", reply_markup=ReplyKeyboardMarkup([["Назад"]], resize_keyboard=True), parse_mode='Markdown', **kw)
                else:
                    context.user_data['waiting'] = 'plan_period'
                    await update.message.reply_text("Хорошо, вернёмся к периоду.", reply_markup=period_kb, parse_mode='Markdown', **kw)
                return True

            # Генерация плана
            await update.message.reply_text("Составляю план...", **kw)
            period = context.user_data['plan_period']
            start = datetime.now().date() if period != 'custom' else context.user_data['plan_start']
            end = None if period != 'custom' else context.user_data['plan_end']
            plan = self.ts.generate_content_plan(
                period, text, nco_info, start, end, context.user_data['plan_theme']
            )
            from .handlers_nco import get_main_keyboard
            await update.message.reply_text(
                f"Готово! Вот твой план:\n\n{plan}\n\n"
                "Если нужно изменить — начни заново или используй редактор.",
                reply_markup=get_main_keyboard(True),
                **kw
            )
            context.user_data.clear()
            return True

        return False