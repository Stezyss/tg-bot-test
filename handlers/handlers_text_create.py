# handlers/handlers_text_create.py
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

text_mode_kb = ReplyKeyboardMarkup([
    ["Свободный текст", "Структурированная форма"],
    ["Назад в главное меню"]
], resize_keyboard=True)

post_type_kb = ReplyKeyboardMarkup([
    ["Анонс", "Новости"],
    ["Призыв к действию", "Отчет"],
    ["Назад"]
], resize_keyboard=True)

style_kb = ReplyKeyboardMarkup([
    ["Разговорный", "Официально-деловой"],
    ["Художественный", "Без стиля"],
    ["Назад"]
], resize_keyboard=True)

BACK_TO_MAIN = ReplyKeyboardMarkup([["Назад в главное меню"]], resize_keyboard=True)
BACK_SIMPLE = ReplyKeyboardMarkup([["Назад"]], resize_keyboard=True)


class TextCreateHandler:
    def __init__(self, text_service):
        self.ts = text_service

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE, **kw):
        context.user_data['waiting'] = 'text_mode'
        await update.message.reply_text(
            "Привет! Давай создадим текст для поста.\n\n"
            "• *Свободный текст* — просто опиши идею.\n"
            "• *Структурированная форма* — выберем тип и детали.\n\n"
            "Что выбираешь?",
            reply_markup=text_mode_kb,
            parse_mode='Markdown',
            **kw
        )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, nco_info: dict, **kw):
        w = context.user_data.get('waiting')

        # 1. Режим
        if w == 'text_mode':
            if text == "Назад в главное меню":
                context.user_data.clear()
                from .handlers_nco import get_main_keyboard
                await update.message.reply_text("Хорошо, возвращаемся. Если текст нужен — просто скажи!", reply_markup=get_main_keyboard(True), **kw)
                return True

            if text == "Свободный текст":
                context.user_data.update({'text_mode': 'free', 'waiting': 'text_prompt'})
                await update.message.reply_text(
                    "Отлично! Просто опиши идею поста.\n"
                    "Пример: «Расскажи про наш приют и как помочь».\n"
                    "Чем больше деталей — тем лучше!",
                    reply_markup=BACK_SIMPLE,
                    parse_mode='Markdown',
                    **kw
                )
            elif text == "Структурированная форма":
                context.user_data.update({'text_mode': 'structured', 'waiting': 'select_post_type'})
                await update.message.reply_text(
                    "Выбери тип поста:",
                    reply_markup=post_type_kb,
                    **kw
                )
            return True

        # 2. Тип поста
        if w == 'select_post_type':
            if text == "Назад":
                context.user_data['waiting'] = 'text_mode'
                await update.message.reply_text("Хорошо, вернёмся к выбору режима.", reply_markup=text_mode_kb, **kw)
                return True

            context.user_data['post_type'] = text
            context.user_data['waiting'] = 'text_prompt'
            await update.message.reply_text(
                f"Тип: *{text}*.\n"
                "Теперь расскажи подробнее о посте!\n\n"
                "Напиши, например:\n"
                "— как называется событие,\n"
                "— когда и где оно пройдёт,\n"
                "— кого вы приглашаете,\n"
                "— и всё остальное, что хочешь добавить.\n\n"
                "Чем подробнее — тем лучше!",
                reply_markup=BACK_SIMPLE,
                parse_mode='Markdown',
                **kw
            )
            return True

        # 3. Детали
        if w == 'text_prompt':
            if text == "Назад":
                if context.user_data.get('text_mode') == 'structured':
                    context.user_data['waiting'] = 'select_post_type'
                    await update.message.reply_text("Хорошо, вернёмся к выбору типа поста.", reply_markup=post_type_kb, **kw)
                else:
                    context.user_data['waiting'] = 'text_mode'
                    await update.message.reply_text("Хорошо, вернёмся к выбору режима.", reply_markup=text_mode_kb, **kw)
                return True

            prompt = text
            if context.user_data.get('text_mode') == 'structured':
                prompt = f"Пост: {context.user_data['post_type']}. {prompt}"
            context.user_data['text_prompt'] = prompt
            context.user_data['waiting'] = 'select_style'
            await update.message.reply_text(
                "Детали сохранены!\n\n"
                "Теперь выбери *стиль текста*:",
                reply_markup=style_kb,
                parse_mode='Markdown',
                **kw
            )
            return True

        # 4. Стиль
        if w == 'select_style':
            if text == "Назад":
                context.user_data['waiting'] = 'text_prompt'
                await update.message.reply_text(
                    "Хорошо, давай перепишем детали.\n\n"
                    "Опиши пост заново:",
                    reply_markup=BACK_SIMPLE,
                    parse_mode='Markdown',
                    **kw
                )
                return True

            styles = {"Разговорный": "разговорный", "Официально-деловой": "официально-деловой",
                      "Художественный": "художественный", "Без стиля": None}
            if text in styles:
                await update.message.reply_text("Пишу текст... Секунду!", **kw)
                result = self.ts.generate_text(context.user_data['text_prompt'], nco_info, styles[text])
                from .handlers_nco import get_main_keyboard
                await update.message.reply_text(
                    f"Готово! Вот твой пост:\n\n{result}\n\n"
                    "Если нужно доработать — используй редактор.",
                    reply_markup=get_main_keyboard(True),
                    **kw
                )
                context.user_data.clear()
            return True

        return False
