# main.py
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters
)

from config import Config
from text_service import TextService
from image_service import ImageService
from attachment_service import AttachmentService
from handlers import BotHandlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def post_init(app: Application):
    if app.bot_data['text_service'].check_health():
        logger.info("YandexGPT готов!")
    else:
        logger.warning("YandexGPT недоступен")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}")
    if update and hasattr(update, "effective_message"):
        await update.effective_message.reply_text("Ошибка. Попробуйте позже.")

def main():
    config = Config.from_env()
    text_service = TextService(config)
    image_service = ImageService(config)
    attachment_service = AttachmentService(config)
    handlers = BotHandlers(text_service, image_service, attachment_service)

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    app.bot_data['text_service'] = text_service

    # Команды
    app.add_handler(CommandHandler("start", handlers.start_command))
    app.add_handler(CommandHandler("nco_postgenerator_bot", handlers.group_start_command))

    # Текст (кроме команд)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_text_message))

    # Фото + Документы (включая PDF, DOCX, TXT)
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handlers.handle_text_message))

    app.add_error_handler(error_handler)

    logger.info("Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()