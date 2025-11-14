# main.py
import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from config import Config
from text_service import TextService
from image_service import ImageService
from handlers import BotHandlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    text_service = application.bot_data['text_service']
    logger.info('Проверка подключения к YandexGPT...')
    if text_service.check_health():
        logger.info('YandexGPT готов!')
    else:
        logger.warning('YandexGPT недоступен — проверьте токены и доступ')


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка бота: {context.error}")
    if update and hasattr(update, "effective_message"):
        try:
            await update.effective_message.reply_text("Произошла ошибка. Попробуйте позже.")
        except:
            pass


def main():
    try:
        config = Config.from_env()
    except ValueError as e:
        logger.error(e)
        return

    text_service = TextService(config)
    image_service = ImageService(config)
    handlers = BotHandlers(text_service, image_service)

    app = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.bot_data['text_service'] = text_service

    # Обработчики (удален CallbackQueryHandler, так как стили теперь reply buttons)
    app.add_handler(CommandHandler("start", handlers.start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_text_message))
    app.add_error_handler(error_handler)

    logger.info("Бот запущен с YandexGPT + YandexART!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
