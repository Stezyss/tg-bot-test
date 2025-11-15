# handlers/handlers_text_edit.py
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

action_kb = ReplyKeyboardMarkup([
    ["Увеличить текст", "Сократи текст"],
    ["Исправить ошибки", "Изменить стиль"],
    ["Перефразировать"],
    ["Назад"]
], resize_keyboard=True)

style_kb = ReplyKeyboardMarkup([
    ["Разговорный", "Официальный"],
    ["Художественный", "Без стиля"],
    ["Назад"]
], resize_keyboard=True)

BACK_TO_MAIN = ReplyKeyboardMarkup([["Назад в главное меню"]], resize_keyboard=True)


class TextEditHandler:
    def __init__(self, text_service):
        self.ts = text_service

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE, **kw):
        context.user_data['waiting'] = 'edit_text'
        await update.message.reply_text(
            "Давай отредактируем текст!\n\n"
            "Введи текст, который хочешь улучшить.\n"
            "Пример: «Сегодня мы помогли 10 животным. Спасибо всем!»",
            reply_markup=BACK_TO_MAIN,
            parse_mode='Markdown',
            **kw
        )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, nco_info: dict, **kw):
        w = context.user_data.get('waiting')

        if w == 'edit_text':
            if text == "Назад в главное меню":
                context.user_data.clear()
                from .handlers_nco import get_main_keyboard
                await update.message.reply_text("Хорошо, возвращаемся. Если текст нужно доработать — просто пришли!", reply_markup=get_main_keyboard(True), **kw)
                return True

            context.user_data['edit_text'] = text
            context.user_data['waiting'] = 'edit_action'
            await update.message.reply_text(
                f"Текст сохранён: *{text[:50]}...*\n\n"
                "Что сделать?",
                reply_markup=action_kb,
                parse_mode='Markdown',
                **kw
            )
            return True

        if w == 'edit_action':
            if text == "Назад":
                context.user_data['waiting'] = 'edit_text'
                await update.message.reply_text("Хорошо, пришли новый текст или подтверди старый.", reply_markup=BACK_TO_MAIN, parse_mode='Markdown', **kw)
                return True

            if text == "Изменить стиль":
                context.user_data['waiting'] = 'edit_style'
                await update.message.reply_text("Выбери новый стиль:", reply_markup=style_kb, parse_mode='Markdown', **kw)
            else:
                await update.message.reply_text("Редактирую... Секунду!", **kw)
                result = self.ts.edit_text_with_action(context.user_data['edit_text'], text, nco_info)
                from .handlers_nco import get_main_keyboard
                await update.message.reply_text(f"Готово!\n\n{result}", reply_markup=get_main_keyboard(True), **kw)
                context.user_data.clear()
            return True

        if w == 'edit_style':
            if text == "Назад":
                context.user_data['waiting'] = 'edit_action'
                await update.message.reply_text("Хорошо, вернёмся к действию.", reply_markup=action_kb, parse_mode='Markdown', **kw)
                return True

            styles = {"Разговорный": "разговорный", "Официальный": "официальный", "Художественный": "художественный", "Без стиля": None}
            if text in styles:
                await update.message.reply_text("Меняю стиль... Готово!", **kw)
                result = self.ts.edit_text_with_action(context.user_data['edit_text'], "Изменить стиль", nco_info, styles[text])
                from .handlers_nco import get_main_keyboard
                await update.message.reply_text(f"Готово!\n\n{result}", reply_markup=get_main_keyboard(True), **kw)
                context.user_data.clear()
            return True
        return False
