# handlers/handlers_image.py
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

style_kb = ReplyKeyboardMarkup([
    ["🎨 Реализм", "🖼️ Мультяшный"],
    ["💧 Акварель", "🤖 Киберпанк"],
    ["✨ Свой стиль"],
    ["⬅️ Назад"]
], resize_keyboard=True)

BACK_TO_MAIN = ReplyKeyboardMarkup([["🏠 Назад в главное меню"]], resize_keyboard=True)


class ImageHandler:
    def __init__(self, image_service):
        self.isvc = image_service

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE, **kw):
        context.user_data['waiting'] = 'image_prompt'
        await update.message.reply_text(
            "🎨 Отлично! Давай создадим крутую картинку для твоего поста!\n\n"
            "Опиши, что хочешь увидеть — представь это в деталях.\n"
            "✨ *Пример:* «Счастливый щенок в приюте с волонтёрами, солнечный день, много игрушек вокруг»\n\n"
            "💡 *Совет:* Чем ярче и детальнее описание — тем интереснее получится результат!",
            reply_markup=BACK_TO_MAIN,
            parse_mode='Markdown',
            **kw
        )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, nco_info: dict, **kw):
        w = context.user_data.get('waiting')

        # 1. Описание (первый шаг)
        if w == 'image_prompt':
            if text == "🏠 Назад в главное меню":
                context.user_data.clear()
                from .handlers_nco import get_main_keyboard
                await update.message.reply_text(
                    "👌 Хорошо, возвращаемся в главное меню. Если захочешь создать картинку — просто скажи!",
                    reply_markup=get_main_keyboard(True), **kw
                )
                return True

            context.user_data['image_prompt'] = text
            context.user_data['waiting'] = 'image_style'
            await update.message.reply_text(
                f"✨ Отлично! Запомнил твоё описание: *{text[:50]}...*\n\n"
                "Теперь давай выберем стиль — от этого зависит настроение картинки!\n\n"
                "🎯 *Примеры стилей:*\n"
                "• «🎨 Реализм» — как живая фотография\n"  
                "• «🖼️ Мультяшный» — ярко и весело\n"
                "• «💧 Акварель» — нежно и творчески\n"
                "• «🤖 Киберпанк» — футуристично и смело",
                reply_markup=style_kb,
                parse_mode='Markdown',
                **kw
            )
            return True

        # 2. Стиль
        if w == 'image_style':
            if text == "⬅️ Назад":
                context.user_data['waiting'] = 'image_prompt'
                await update.message.reply_text(
                    "👌 Хорошо, давай изменим описание картинки.\n\n"
                    "Опиши заново, что хочешь увидеть:",
                    reply_markup=BACK_TO_MAIN,
                    parse_mode='Markdown',
                    **kw
                )
                return True

            styles = {
                "🎨 Реализм": "реализм", "🖼️ Мультяшный": "мультяшный",
                "💧 Акварель": "акварель", "🤖 Киберпанк": "киберпанк"
            }

            if text in styles:
                await update.message.reply_text("🎨 Генерирую картинку... Обычно это занимает не больше минуты! ⏳", **kw)
                img = await self.isvc.generate_image(context.user_data['image_prompt'], nco_info, styles[text])
                from .handlers_nco import get_main_keyboard
                if img:
                    await update.message.reply_photo(
                        photo=img,
                        caption="✅ Готово! Нравится результат?\n\n"
                               "Если хочешь что-то изменить — попробуй другой стиль или уточни описание!",
                        reply_markup=get_main_keyboard(True), **kw
                    )
                else:
                    await update.message.reply_text(
                        "😕 Упс, что-то пошло не так... Давай попробуем ещё раз?",
                        reply_markup=get_main_keyboard(True), **kw
                    )
                context.user_data.clear()
            elif text == "✨ Свой стиль":
                context.user_data['waiting'] = 'custom_image_style'
                await update.message.reply_text(
                    "🎨 Круто! Творческий подход — это здорово!\n\n"
                    "Опиши свой стиль словами — я постараюсь его воссоздать.\n\n"
                    "✨ *Примеры:*\n"
                    "• «В стиле поп-арт как у Энди Уорхола»\n"
                    "• «Ретро-футуризм 80-х»\n"
                    "• «Как акварельный скетч с лёгкой небрежностью»\n\n"
                    "Какой стиль ты представляешь?",
                    reply_markup=ReplyKeyboardMarkup([["⬅️ Назад"]], resize_keyboard=True),
                    parse_mode='Markdown',
                    **kw
                )
            return True

        # 3. Свой стиль
        if w == 'custom_image_style':
            if text == "⬅️ Назад":
                context.user_data['waiting'] = 'image_style'
                await update.message.reply_text("👌 Хорошо, выбирай стиль из предложенных вариантов.", reply_markup=style_kb, parse_mode='Markdown', **kw)
                return True

            await update.message.reply_text("🎨 Генерирую с твоим уникальным стилем... Жди волшебства! ✨", **kw)
            img = await self.isvc.generate_image(context.user_data['image_prompt'], nco_info, text)
            from .handlers_nco import get_main_keyboard
            if img:
                await update.message.reply_photo(
                    photo=img,
                    caption="✅ Вот что получилось с твоим стилем! Нравится?\n\n"
                           "Если хочешь что-то изменить — просто начни заново и опиши по-другому!",
                    reply_markup=get_main_keyboard(True), **kw
                )
            else:
                await update.message.reply_text(
                    "😕 Не получилось создать картинку с таким стилем... Может, попробуем другой вариант?",
                    reply_markup=get_main_keyboard(True), **kw
                )
            context.user_data.clear()
            return True

        return False
