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

# ── БЛОКИРОВКИ ПО ПОЛЬЗОВАТЕЛЮ ───────────────────────────────────────
user_locks: dict[int, asyncio.Lock] = {}


async def post_init(app: Application):
    if app.bot_data['text_service'].check_health():
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
        'text': TextCreateHandler(ts),
        'image': ImageHandler(img),
        'plan': PlanHandler(ts),
        'edit': TextEditHandler(ts),
        'nco': nco
    }

    app = Application.builder().token(cfg.TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    app.bot_data.update({'text_service': ts, 'db': db, 'handlers': handlers, 'nco': nco})

    # ───────────────────────────────────────────────────────────────
    # /start — адаптировано для ЛС и групп
    # ───────────────────────────────────────────────────────────────
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat

        # ── ГРУППА ────────────────────────────────────────────
        if chat.type in ["group", "supergroup"]:
            await update.message.reply_text(
                "Привет! Я помогу создавать посты и картинки для НКО.\n\n"
                "Для дальнейшей работы с ботом используй /nco_postgenerator_bot"
            )
            return

        # ── ЛИЧНЫЕ СООБЩЕНИЯ ─────────────────────────────────-
        user_id = update.effective_user.id
        if user_id not in user_locks:
            user_locks[user_id] = asyncio.Lock()

        context.user_data.clear()
        has_data = nco.has_data(user_id)
        await update.message.reply_text(
            "Привет! Я помогу создавать посты и картинки для НКО.\n\n"
            "Загрузи фото или документ — я извлеку текст и сделаю пост!\n"
            "Или выбери действие ниже.",
            reply_markup=get_main_keyboard(has_data)
        )

    # ───────────────────────────────────────────────────────────────
    # Команда для активации работы в группе
    # /nco_postgenerator_bot
    # ───────────────────────────────────────────────────────────────
    async def group_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat

        if chat.type not in ["group", "supergroup"]:
            await update.message.reply_text("Эта команда используется только в группе.")
            return

        user = update.effective_user
        context.user_data['active_session'] = True
        context.user_data['session_user_id'] = user.id

        await update.message.reply_text(
            f"{user.first_name}, я готов работать! Отправь фото, текст или выбери действие.",
            reply_to_message_id=update.message.message_id
        )

    # ───────────────────────────────────────────────────────────────
    # ГЛАВНЫЙ ОБРАБОТЧИК
    # ───────────────────────────────────────────────────────────────
    async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in user_locks:
            user_locks[user_id] = asyncio.Lock()

        async with user_locks[user_id]:

            # ────────────────────────────────────────────────
            # ГРУППЫ — работа только после команды /nco_postgenerator_bot
            # ────────────────────────────────────────────────
            if update.message and update.message.chat.type in ['group', 'supergroup']:
                if not context.user_data.get('active_session') or \
                   update.effective_user.id != context.user_data.get('session_user_id'):
                    return

            reply_kwargs = {}
            if update.message and update.message.chat.type in ['group', 'supergroup']:
                reply_kwargs['reply_to_message_id'] = update.message.message_id

            # ── CALLBACK ----------------------------------------------------------------
            if update.callback_query:
                await nco.handle_callback(update, context)
                return

            # ── ВЛОЖЕНИЯ (фото / документ) ---------------------------------------------
            if update.message and (update.message.photo or update.message.document):
                waiting = context.user_data.get('waiting', '')

                if waiting.startswith('image_'):
                    await update.message.reply_text(
                        "В генерации изображений не поддерживается загрузка файлов.",
                        **reply_kwargs
                    )
                    return

                if waiting.startswith('plan_'):
                    await update.message.reply_text(
                        "Работа с файлами не поддерживается.",
                        **reply_kwargs
                    )
                    context.user_data['waiting'] = 'plan_theme'
                    from handlers.handlers_plan import PlanHandler
                    plan_handler = PlanHandler(app.bot_data['text_service'])
                    await plan_handler.start(update, context, **reply_kwargs)
                    return

                if waiting == 'edit_text':
                    await update.message.reply_text("Анализирую вложение...", **reply_kwargs)
                    content = await att.process_attachment(update.message)
                    if content and content.strip():
                        context.user_data['original_text'] = content
                        context.user_data['waiting'] = 'edit_style'
                        from telegram import ReplyKeyboardMarkup
                        await update.message.reply_text(
                            "Текст извлечён! Выбери стиль редактирования:",
                            reply_markup=ReplyKeyboardMarkup([
                                ["Сделать короче", "Сделать длиннее"],
                                ["Сделать формальнее", "Сделать проще"],
                                ["Добавить эмодзи", "Убрать эмодзи"],
                                ["Назад в главное меню"]
                            ], resize_keyboard=True),
                            **reply_kwargs
                        )
                    else:
                        await update.message.reply_text("Не удалось извлечь текст.", **reply_kwargs)
                    return

                # Текст из вложения → генератор текста
                if not waiting or waiting.startswith('text_') or waiting == 'select_style':
                    await update.message.reply_text("Анализирую вложение...", **reply_kwargs)
                    content = await att.process_attachment(update.message)
                    if content and content.strip():
                        context.user_data.update({'text_prompt': content, 'waiting': 'select_style'})
                        from handlers.handlers_text_create import style_kb
                        await update.message.reply_text(
                            "Готово!\n\nВыбери стиль для поста:",
                            reply_markup=style_kb,
                            **reply_kwargs
                        )
                    else:
                        await update.message.reply_text(
                            "Не удалось извлечь текст.",
                            reply_markup=get_main_keyboard(True),
                            **reply_kwargs
                        )
                    return

            # ────────────────────────────────────────────────
            # ТЕКСТОВОЕ СООБЩЕНИЕ
            # ────────────────────────────────────────────────
            text = update.message.text.strip() if update.message and update.message.text else None
            nco_info = nco.get_nco_info(update)
            kw = reply_kwargs

            if text == "Назад в главное меню":
                context.user_data.clear()
                has_data = nco.has_data(user_id)
                await update.message.reply_text("Готово.", reply_markup=get_main_keyboard(has_data), **kw)
                return

            if text in ["Назад в главное меню", "Пропустить", "Очистить"] and not context.user_data.get('waiting'):
                return

            if text in ["Предоставить информацию об НКО", "Просмотреть информацию об НКО"]:
                if not nco.has_data(user_id):
                    await nco.start_nco_input(update, context, is_edit=False, **kw)
                else:
                    await nco.show_nco_info(update, context, **kw)
                return

            # Основные разделы
            if text in ["Генерация текста", "Генерация изображения", "Редактор текста", "Контент-план"]:
                h = handlers[['text', 'image', 'edit', 'plan'][["Генерация текста", "Генерация изображения", "Редактор текста", "Контент-план"].index(text)]]
                await h.start(update, context, **kw)
                return

            waiting = context.user_data.get('waiting', '')

            if waiting.startswith('nco_'):
                handled = await nco.handle_nco(update, context, text, **kw)
                if handled:
                    return

            elif waiting.startswith('text_') or waiting in ['select_style', 'text_prompt', 'select_post_type']:
                await handlers['text'].handle(update, context, text, nco_info, **kw)
                return

            elif waiting.startswith('image_'):
                await handlers['image'].handle(update, context, text, nco_info, **kw)
                return

            elif waiting.startswith('edit_'):
                await handlers['edit'].handle(update, context, text, nco_info, **kw)
                return

            elif waiting.startswith('plan_'):
                await handlers['plan'].handle(update, context, text, nco_info, **kw)
                return

            has_data = nco.has_data(user_id)
            await update.message.reply_text("Выбери действие:", reply_markup=get_main_keyboard(has_data), **kw)

    # ───────────────────────────────────────────────────────────────
    # РЕГИСТРАЦИЯ ХЕНДЛЕРОВ
    # ───────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("nco_postgenerator_bot", group_activate))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle))
    app.add_handler(CallbackQueryHandler(handle))
    app.add_error_handler(error_handler)

    logger.info("Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
