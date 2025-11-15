# main.py
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import Config
from text_service import TextService
from image_service import ImageService
from attachment_service import AttachmentService
from db import Database
from handlers import (
    TextCreateHandler,
    ImageHandler,
    PlanHandler,
    TextEditHandler,
    NCOHandler,
)
from handlers.handlers_nco import get_main_keyboard

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def post_init(app: Application):
    if app.bot_data["text_service"].check_health():
        logger.info("YandexGPT подключён")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}")


def main():
    cfg = Config.from_env()
    db = Database()
    ts = TextService(cfg)
    img = ImageService(cfg)
    att = AttachmentService(cfg)
    nco = NCOHandler(db)

    handlers = {
        "text": TextCreateHandler(ts),
        "image": ImageHandler(img),
        "plan": PlanHandler(ts),
        "edit": TextEditHandler(ts),
        "nco": nco,
    }

    app = (
        Application.builder()
        .token(cfg.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    app.bot_data.update(
        {"text_service": ts, "db": db, "handlers": handlers, "nco": nco}
    )

    # ------------------------------------------------------------------ #
    # /start
    # ------------------------------------------------------------------ #
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data.clear()
        try:
            has_data = nco.has_data(update.effective_user.id)  # <-- публичный метод
        except Exception as e:
            logger.error(f"Ошибка в has_data: {e}")
            has_data = False
        await update.message.reply_text(
            "Привет! Я помогу создавать посты и картинки для НКО.\n\n"
            "Загрузи фото или документ — я извлеку текст и сделаю пост!\n"
            "Или выбери действие ниже.",
            reply_markup=get_main_keyboard(has_data),
        )

    # ------------------------------------------------------------------ #
    # Основной обработчик сообщений
    # ------------------------------------------------------------------ #
    async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Защита от групп (если понадобится)
        if update.message.chat.type in ["group", "supergroup"]:
            if not context.user_data.get("active_session") or \
               update.effective_user.id != context.user_data.get("session_user_id"):
                return

        if not isinstance(context.user_data, dict):
            context.user_data = {}

        message_text = update.message.text
        text = message_text.strip() if message_text else ""
        waiting = context.user_data.get("waiting")
        try:
            nco_info = nco.get_nco_info(update)
            has_data = nco.has_data(update.effective_user.id)  # <-- публичный метод
        except Exception as e:
            logger.error(f"Ошибка в nco_info/has_data: {e}")
            nco_info = {}
            has_data = False
        kw = {}

        # ---------------------- ВЛОЖЕНИЯ ---------------------- #
        if update.message.photo or update.message.document:
            await update.message.reply_text("Обрабатываю вложение...", **kw)
            content = await att.process_attachment(update)
            if content:
                await handlers["text"].start(update, context, **kw)
                await handlers["text"].handle(update, context, content, nco_info, **kw)
            else:
                await update.message.reply_text(
                    "Не удалось извлечь текст из файла.",
                    reply_markup=get_main_keyboard(has_data),
                    **kw,
                )
            return

        # ---------------------- ГЛАВНОЕ МЕНЮ ---------------------- #
        if text == "Генерация текста":
            await handlers["text"].start(update, context, **kw)
            return
        if text == "Генерация изображения":
            await handlers["image"].start(update, context, **kw)
            return
        if text == "Редактор текста":
            await handlers["edit"].start(update, context, **kw)
            return
        if text == "Контент-план":
            await handlers["plan"].start(update, context, **kw)
            return
        if text in ["Предоставить информацию об НКО", "Изменить информацию об НКО"]:
            await handlers["nco"].start_nco_setup(update, context, **kw)
            return
        if text == "Просмотреть информацию об НКО":
            await handlers["nco"].view_nco_info(update, context, **kw)
            return

        # ---------------------- КНОПКА "НАЗАД" ---------------------- #
        if text == "Назад":
            if isinstance(waiting, str):
                if waiting.startswith("plan_"):
                    await handlers["plan"].handle(update, context, text, nco_info, **kw)
                elif waiting.startswith("nco_"):
                    await nco.handle_nco(update, context, text, **kw)
                elif waiting in [
                    "text_mode",
                    "select_post_type",
                    "text_prompt",
                    "select_style",
                ]:
                    await handlers["text"].handle(update, context, text, nco_info, **kw)
                elif waiting in [
                    "image_prompt",
                    "image_style",
                    "custom_image_style",
                ]:
                    await handlers["image"].handle(update, context, text, nco_info, **kw)
                elif waiting in ["edit_text", "edit_action", "edit_style"]:
                    await handlers["edit"].handle(update, context, text, nco_info, **kw)
                else:
                    context.user_data.clear()
                    await update.message.reply_text(
                        "Возвращаемся в главное меню.",
                        reply_markup=get_main_keyboard(has_data),
                        **kw,
                    )
            else:
                context.user_data.clear()
                await update.message.reply_text(
                    "Возвращаемся в главное меню.",
                    reply_markup=get_main_keyboard(has_data),
                    **kw,
                )
            return

        # ---------------------- ОБРАБОТКА АКТИВНЫХ СОСТОЯНИЙ ---------------------- #
        if isinstance(waiting, str):
            if waiting.startswith("nco_"):
                try:
                    handled = await nco.handle_nco(update, context, text, **kw)
                    if handled:
                        return
                except Exception as e:
                    logger.error(f"Ошибка в handle_nco: {e}")
                    await update.message.reply_text("Ошибка в обработке НКО. Возвращаемся в меню.", reply_markup=get_main_keyboard(has_data), **kw)
                    context.user_data.clear()
                    return
            elif waiting in [
                "text_mode",
                "select_post_type",
                "text_prompt",
                "select_style",
            ]:
                await handlers["text"].handle(update, context, text, nco_info, **kw)
            elif waiting in [
                "image_prompt",
                "image_style",
                "custom_image_style",
            ]:
                await handlers["image"].handle(update, context, text, nco_info, **kw)
            elif waiting in ["edit_text", "edit_action", "edit_style"]:
                await handlers["edit"].handle(update, context, text, nco_info, **kw)
            elif waiting.startswith("plan_"):
                await handlers["plan"].handle(update, context, text, nco_info, **kw)
            else:
                await update.message.reply_text(
                    "Выбери действие:",
                    reply_markup=get_main_keyboard(has_data),
                    **kw,
                )
        else:
            await update.message.reply_text(
                "Выбери действие:",
                reply_markup=get_main_keyboard(has_data),
                **kw,
            )

    # ------------------------------------------------------------------ #
    # Регистрация хендлеров
    # ------------------------------------------------------------------ #
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle))
    app.add_error_handler(error_handler)

    logger.info("Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
