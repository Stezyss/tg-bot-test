import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import Config
from ai_service import AIService
from image_service import ImageService
from handlers import BotHandlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        config = Config.from_env()
    except ValueError as e:
        logger.error(f'Ошибка конфигурации: {e}')
        return

    ai_service = AIService(config)
    image_service = ImageService(config)  # Заглушка

    bot_handlers = BotHandlers(ai_service, image_service)

    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', bot_handlers.start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_handlers.handle_text))

    logger.info("Запуск бота... 🚀")
    application.run_polling()

if __name__ == '__main__':
    main()