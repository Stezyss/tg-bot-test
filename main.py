# main.py
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from config import Config
from text_service import TextService
from image_service import ImageService
from attachment_service import AttachmentService
from db import Database
from handlers import (
    TextCreateHandler, ImageHandler, PlanHandler,
    TextEditHandler, NCOHandler
)
from handlers.handlers_nco import get_main_keyboard  # ← КРИТИЧНО!


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data.clear()
        nco_info = nco.get_nco_info(update)
        has_data = any(nco_info.values())
        await update.message.reply_text(
            "Привет! Я помогу создавать посты и картинки для НКО.\n\n"
            "Загрузи фото или документ — я извлеку текст и сделаю пост!\n"
            "Или выбери действие ниже.",
            reply_markup=get_main_keyboard(has_data)
        )

    async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.chat.type in ['group', 'supergroup']:
            if not context.user_data.get('active_session') or update.effective_user.id != context.user_data.get('session_user_id'):
                return

        reply_kwargs = {}
        if update.message.chat.type in ['group', 'supergroup']:
            reply_kwargs['reply_to_message_id'] = update.message.message_id

        # ── ВЛОЖЕНИЯ ─────────────────────────────────────────────────────
        if update.message.photo or update.message.document:
            await update.message.reply_text("Анализирую вложение...", **reply_kwargs)
            content = await att.process_attachment(update.message)
            if content and content.strip():
                context.user_data['text_prompt'] = content
                context.user_data['waiting'] = 'select_style'
                from handlers.handlers_text_create import style_kb
                await update.message.reply_text("Выбери стиль для поста:", reply_markup=style_kb, **reply_kwargs)
            else:
                await update.message.reply_text("Не удалось извлечь текст.", reply_markup=get_main_keyboard(True), **reply_kwargs)
            return

        text = update.message.text.strip()
        nco_info = nco.get_nco_info(update)
        kw = reply_kwargs

        # ── НАЗАД В ГЛАВНОЕ МЕНЮ ───────────────────────────────────────
        if text == "Назад в главное меню":
            context.user_data.clear()
            await update.message.reply_text("Готово.", reply_markup=get_main_keyboard(any(nco_info.values())), **kw)
            return

        # ── КНОПКИ НКО: ПРОСМОТР / ИЗМЕНЕНИЕ ───────────────────────────
        if text in ["Предоставить информацию об НКО", "Изменить информацию об НКО"]:
            await nco.start_nco_edit(update, context, **kw)
            return  # ← ВАЖНО: ПРЕРЫВАЕМ ВЫПОЛНЕНИЕ

        if text == "Просмотреть информацию об НКО":
            await nco.show_nco_info(update, context, **kw)
            return  # ← ПРЕРЫВАЕМ

        # ── ОСНОВНЫЕ ДЕЙСТВИЯ ─────────────────────────────────────────
        if text in ["Генерация текста", "Генерация изображения", "Редактор текста", "Контент-план"]:
            h = handlers[['text', 'image', 'edit', 'plan'][["Генерация текста", "Генерация изображения", "Редактор текста", "Контент-план"].index(text)]]
            await h.start(update, context, **kw)
            return  # ← ПРЕРЫВАЕМ

        # ── ОБРАБОТКА СОСТОЯНИЙ ───────────────────────────────────────
        waiting = context.user_data.get('waiting', '')

        if waiting.startswith('nco_'):
            handled = await nco.handle_nco(update, context, text, **kw)
            if handled:
                return  # ← ПРЕРЫВАЕМ, если обработано
            if text == "Назад":
                await nco.back(update, context, **kw)
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

        # ── ПО УМОЛЧАНИЮ ───────────────────────────────────────────────
        await update.message.reply_text("Выбери действие:", reply_markup=get_main_keyboard(any(nco_info.values())), **kw)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle))
    app.add_error_handler(error_handler)

    logger.info("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
