"""
Главный модуль Telegram‑бота. Отвечает за инициализацию приложения,
регистрацию обработчиков, запуск сервисов и маршрутизацию сообщений.

Основные функции модуля:
- загрузка конфигурации и инициализация сервисов (текст, изображения, OCR, БД);
- настройка Telegram‑бота и всех команд;
- единый главный обработчик сообщений `handle()`;
- управление состояниями пользователя и блокировками;
- поддержка работы как в ЛС, так и в группах.
"""

import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes,
    filters, CallbackQueryHandler
)

from config import Config
from text_service import TextService
from image_service import ImageService
from attachment_service import AttachmentService
from db import Database
from handlers import (
    TextCreateHandler, ImageHandler, PlanHandler,
    TextEditHandler, NCOHandler
)
from handlers.handlers_nco import get_main_keyboard


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальный словарь для блокировки конкурирующих запросов одного пользователя
user_locks: dict[int, asyncio.Lock] = {}


async def post_init(app: Application):
    """
    Проверка подключения к YandexGPT после старта приложения.
    """
    if app.bot_data['text_service'].check_health():
        logger.info("YandexGPT подключён")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """
    Глобальный обработчик ошибок.
    Логирует исключения, не влияя на работу бота.
    """
    logger.error(f"Ошибка: {context.error}")


# ============================================================================
#  ОСНОВНАЯ ФУНКЦИЯ ЗАПУСКА БОТА
# ============================================================================

def main():
    """
    Главная точка входа приложения.

    Здесь происходит:
    - загрузка конфигурации;
    - инициализация сервисов;
    - настройка Telegram‑бота;
    - регистрация всех обработчиков;
    - запуск polling‑механизма.
    """

    cfg = Config.from_env()
    db = Database()
    ts = TextService(cfg)
    img = ImageService(cfg)
    att = AttachmentService(cfg)

    # Handlers для разных разделов
    nco = NCOHandler(db)
    handlers = {
        'text': TextCreateHandler(ts),
        'image': ImageHandler(img),
        'plan': PlanHandler(ts),
        'edit': TextEditHandler(ts),
        'nco': nco
    }

    # Создание Telegram‑приложения
    app = Application.builder().token(cfg.TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Передача сервисов внутрь приложения
    app.bot_data.update({'text_service': ts, 'db': db, 'handlers': handlers, 'nco': nco})


#  /start
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработчик команды /start.
        Умеет работать как в личных сообщениях, так и в группах.
        """

        chat = update.effective_chat

        # Для групп — отдельное пояснение
        if chat.type in ["group", "supergroup"]:
            await update.message.reply_text(
                "👋 Привет! Я помогу создавать посты и картинки для НКО.\n\n"
                "Для дальнейшей работы с ботом используй /nco_postgenerator_bot"
            )
            return

        # Для ЛС — инициализация состояния пользователя
        user_id = update.effective_user.id
        if user_id not in user_locks:
            user_locks[user_id] = asyncio.Lock()

        context.user_data.clear()
        has_data = nco.has_data(user_id)

        await update.message.reply_text(
            "👋 Привет! Я твой помощник по созданию контента для НКО.\n\n"
            "📸 Можешь загрузить фото или документ — я извлеку текст и сделаю пост!\n"
            "✨ Или выбери действие из меню ниже.",
            reply_markup=get_main_keyboard(has_data)
        )

#  /nco_postgenerator_bot — активация в группе

    async def group_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Команда‑ключ для активации бота в группах.
        Без неё бот игнорирует сообщения.
        """

        chat = update.effective_chat
        if chat.type not in ["group", "supergroup"]:
            await update.message.reply_text("❌ Эта команда используется только в группе.")
            return

        user = update.effective_user
        context.user_data['active_session'] = True
        context.user_data['session_user_id'] = user.id

        await update.message.reply_text(
            f"👋 {user.first_name}, я готов работать! Отправь фото, текст или выбери действие.",
            reply_to_message_id=update.message.message_id
        )

#  ГЛАВНЫЙ ОБРАБОТЧИК СООБЩЕНИЙ
    async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Универсальный обработчик всех типов входящих данных:
        - текст
        - фото / документы
        - callback‑запросы

        Управляет состояниями, работой отдельных модулей и маршрутизацией.
        """

        user_id = update.effective_user.id
        if user_id not in user_locks:
            user_locks[user_id] = asyncio.Lock()

        async with user_locks[user_id]:

            # === Ограничение работы в группах ===
            if update.message and update.message.chat.type in ['group', 'supergroup']:
                if not context.user_data.get('active_session') or \
                   update.effective_user.id != context.user_data.get('session_user_id'):
                    return

            # Настройки ответа
            reply_kwargs = {}
            if update.message and update.message.chat.type in ['group', 'supergroup']:
                reply_kwargs['reply_to_message_id'] = update.message.message_id

            # === CALLBACK ===
            if update.callback_query:
                await nco.handle_callback(update, context)
                return

            # === ВЛОЖЕНИЯ ===
            if update.message and (update.message.photo or update.message.document):
                waiting = context.user_data.get('waiting', '')

                # Несовместимые режимы
                if waiting.startswith('image_'):
                    await update.message.reply_text(
                        "❌ В генерации изображений не поддерживается загрузка файлов.",
                        **reply_kwargs
                    )
                    return

                if waiting.startswith('plan_'):
                    await update.message.reply_text(
                        "❌ Работа с файлами в контент‑плане не поддерживается.",
                        **reply_kwargs
                    )
                    context.user_data['waiting'] = 'plan_theme'
                    from handlers.handlers_plan import PlanHandler
                    plan_handler = PlanHandler(app.bot_data['text_service'])
                    await plan_handler.start(update, context, **reply_kwargs)
                    return

                # Вложение как источник текста для редактора
                if waiting == 'edit_text':
                    await update.message.reply_text("📄 Анализирую вложение...", **reply_kwargs)
                    content = await att.process_attachment(update.message)

                    if content and content.strip():
                        context.user_data['original_text'] = content
                        context.user_data['waiting'] = 'edit_style'

                        from telegram import ReplyKeyboardMarkup
                        await update.message.reply_text(
                            "✅ Текст извлечён! Выбери стиль редактирования:",
                            reply_markup=ReplyKeyboardMarkup([
                                ["📉 Сделать короче", "📈 Сделать длиннее"],
                                ["📋 Сделать формальнее", "💬 Сделать проще"],
                                ["😊 Добавить эмодзи", "🚫 Убрать эмодзи"],
                                ["🏠 Назад в главное меню"]
                            ], resize_keyboard=True),
                            **reply_kwargs
                        )
                    else:
                        await update.message.reply_text("❌ Не удалось извлечь текст из файла.", **reply_kwargs)
                    return

                # Вложение → генератор текста
                if not waiting or waiting.startswith('text_') or waiting == 'select_style':
                    await update.message.reply_text("📄 Анализирую вложение...", **reply_kwargs)
                    content = await att.process
