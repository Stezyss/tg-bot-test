# handlers/handlers_image.py
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

style_kb = ReplyKeyboardMarkup([
    ["Реализм", "Мультяшный"],
    ["Акварель", "Киберпанк"],
    ["Свой стиль"],
    ["Назад"]
], resize_keyboard=True)

BACK_TO_MAIN = ReplyKeyboardMarkup([["Назад в главное меню"]], resize_keyboard=True)


class ImageHandler:
    def __init__(self, image_service):
        self.isvc = image_service

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE, **kw):
        context.user_data['waiting'] = 'image_prompt'
        await update.message.reply_text(
            "Давай создадим картинку для поста!\n\n"
            "Опиши, что хочешь увидеть.\n"
            "Пример: «Счастливый щенок в приюте с волонтёрами».\n"
            "Чем ярче описание — тем круче результат!",
            reply_markup=BACK_TO_MAIN,
            parse_mode='Markdown',
            **kw
        )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, nco_info: dict, **kw):
        w = context.user_data.get('waiting')

        # 1. Описание (первый шаг)
        if w == 'image_prompt':
            if text == "Назад в главное меню":
                context.user_data.clear()
                from .handlers_nco import get_main_keyboard
                await update.message.reply_text(
                    "Хорошо, возвращаемся. Если картинка нужна — просто скажи!",
                    reply_markup=get_main_keyboard(True), **kw
                )
                return True

            context.user_data['image_prompt'] = text
            context.user_data['waiting'] = 'image_style'
            await update.message.reply_text(
                f"Отлично! Описание: *{text[:50]}...*\n\n"
                "Теперь выбери стиль.\n"
                "Например: «Реализм» — как фото, «Мультяшный» — весело и ярко.",
                reply_markup=style_kb,
                parse_mode='Markdown',
                **kw
            )
            return True

        # 2. Стиль
        if w == 'image_style':
            if text == "Назад":
                context.user_data['waiting'] = 'image_prompt'
                await update.message.reply_text(
                    "Хорошо, давай перепишем описание.\n\n"
                    "Опиши картинку заново:",
                    reply_markup=BACK_TO_MAIN,
                    parse_mode='Markdown',
                    **kw
                )
                return True

            styles = {
                "Реализм": "реализм", "Мультяшный": "мультяшный",
                "Акварель": "акварель", "Киберпанк": "киберпанк"
            }

            if text in styles:
                await update.message.reply_text("Генерирую... Это займёт 10–20 секунд!", **kw)
                img = await self.isvc.generate_image(context.user_data['image_prompt'], nco_info, styles[text])
                from .handlers_nco import get_main_keyboard
                if img:
                    await update.message.reply_photo(
                        photo=img,
                        caption="Готово! Если не то — попробуй другой стиль или описание.",
                        reply_markup=get_main_keyboard(True), **kw
                    )
                else:
                    await update.message.reply_text(
                        "Ой, что-то пошло не так. Попробуй ещё раз!",
                        reply_markup=get_main_keyboard(True), **kw
                    )
                context.user_data.clear()
            elif text == "Свой стиль":
                context.user_data['waiting'] = 'custom_image_style'
                await update.message.reply_text(
                    "Круто! Опиши свой стиль.\n"
                    "Пример: «В стиле поп-арт» или «Ретро-футуризм».\n"
                    "Я постараюсь учесть!",
                    reply_markup=ReplyKeyboardMarkup([["Назад"]], resize_keyboard=True),
                    parse_mode='Markdown',
                    **kw
                )
            return True

        # 3. Свой стиль
        if w == 'custom_image_style':
            if text == "Назад":
                context.user_data['waiting'] = 'image_style'
                await update.message.reply_text("Хорошо, выбирай стиль заново.", reply_markup=style_kb, parse_mode='Markdown', **kw)
                return True

            await update.message.reply_text("Генерирую с твоим стилем... Жду!", **kw)
            img = await self.isvc.generate_image(context.user_data['image_prompt'], nco_info, text)
            from .handlers_nco import get_main_keyboard
            if img:
                await update.message.reply_photo(
                    photo=img,
                    caption="Вот! Если нужно доработать — опиши по-новому.",
                    reply_markup=get_main_keyboard(True), **kw
                )
            else:
                await update.message.reply_text(
                    "Не получилось. Попробуй другой стиль или описание!",
                    reply_markup=get_main_keyboard(True), **kw
                )
            context.user_data.clear()
            return True

        return False
