# handlers/handlers_nco.py
import re
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from db import Database


def clean_url(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'^(https?://)?(www\.)?', '', text, flags=re.IGNORECASE)
    text = text.split('/')[0].split('?')[0].split('#')[0]
    text = re.sub(r'[()\[\]"\']', '', text)
    return text.strip()


def get_main_keyboard(has_data: bool) -> ReplyKeyboardMarkup:
    """
    has_data = True, если хотя бы одно поле НЕ пустое
    """
    return ReplyKeyboardMarkup([
        ["Генерация текста", "Генерация изображения"],
        ["Редактор текста", "Контент-план"],
        ["Изменить информацию об НКО" if has_data else "Предоставить информацию об НКО"],
        ["Просмотреть информацию об НКО"]
    ], resize_keyboard=True)


# Клавиатуры
BACK_TO_MAIN = ReplyKeyboardMarkup([["Назад в главное меню"]], resize_keyboard=True)
BACK_FIRST = ReplyKeyboardMarkup([["Назад в главное меню", "Пропустить", "Очистить"]], resize_keyboard=True)
BACK_SKIP_CLEAR = ReplyKeyboardMarkup([["Назад", "Пропустить", "Очистить"]], resize_keyboard=True)


STEP_TEXTS = {
    'nco_name': (
        "Привет! Давай познакомимся с твоей НКО\n\n"
        "Напиши *название*.\n"
        "Например: «Фонд Добро» или «ЭкоАктивисты».\n\n"
        "Если не хочешь менять — нажми «Пропустить»."
    ),
    'nco_activities': (
        "Отлично! Теперь расскажи, *чем занимается НКО*?\n"
        "Например: «Помогаем бездомным животным и проводим эко-акции».\n\n"
        "Это поможет мне делать посты под твою миссию"
    ),
    'nco_audience': (
        "Кто твоя *целевая аудитория*?\n"
        "Например: «Студенты вузов», «Дети 7–12 лет», «Работники IT», «Пенсионеры».\n\n"
        "Так посты будут ближе к людям"
    ),
    'nco_website': (
        "Есть сайт? Укажи его (можно пропустить).\n"
        "Пример: dobro.org или https://dobro.org\n\n"
        "Я сам уберу лишнее"
    )
}


class NCOHandler:
    def __init__(self, database: Database):
        self.db = database

    def _get(self, user_id: int) -> dict:
        raw = self.db.get_nco_info(user_id) or {}
        return {k: raw.get(k, '') for k in ('name', 'activities', 'audience', 'website')}

    def has_data(self, user_id: int) -> bool:
        """Проверяет, есть ли хотя бы одно НЕпустое поле"""
        info = self._get(user_id)
        return any(v.strip() for v in info.values())

    async def save_field(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                         field: str, value: str, next_step: str | None, **kw):
        user_id = update.effective_user.id
        try:
            data = self._get(user_id)
            data[field] = value.strip() if value else ""
            print(f"[DEBUG] Сохраняю {field}={data[field]} для user {user_id}")  # Для дебага в логах
            self.db.save_nco_info(user_id, **data)

            if next_step is None:
                from .handlers_nco import get_main_keyboard
                has_data = self.has_data(user_id)
                await update.message.reply_text(
                    "Всё сохранено! Теперь я знаю твою НКО\n"
                    "Могу использовать это в постах и планах",
                    reply_markup=get_main_keyboard(has_data),
                    **kw
                )
                context.user_data.clear()
            else:
                context.user_data['waiting'] = next_step
                markup = BACK_FIRST if next_step == 'nco_name' else BACK_SKIP_CLEAR
                await update.message.reply_text(
                    STEP_TEXTS[next_step],
                    reply_markup=markup,
                    parse_mode='Markdown',
                    **kw
                )
        except Exception as e:
            print(f"[ERROR] save_field: {e}")
            await update.message.reply_text("Что-то пошло не так при сохранении. Попробуй заново.", **kw)
            context.user_data.clear()

    async def start_nco_setup(self, update: Update, context: ContextTypes.DEFAULT_TYPE, **kw):
        context.user_data['waiting'] = 'nco_name'
        await update.message.reply_text(
            STEP_TEXTS['nco_name'],
            reply_markup=BACK_FIRST,
            parse_mode='Markdown',
            **kw
        )

    async def view_nco_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE, **kw):
        user_id = update.effective_user.id
        info = self._get(user_id)
        has_data = self.has_data(user_id)
        lines = ["Вот что я знаю о твоей НКО:\n"]
        if info.get('name', '').strip():
            lines.append(f"• *Название*: {info['name']}")
        else:
            lines.append("• *Название*: не указано")

        if info.get('activities', '').strip():
            lines.append(f"• *Деятельность*: {info['activities']}")
        else:
            lines.append("• *Деятельность*: не указано")

        if info.get('audience', '').strip():
            lines.append(f"• *Аудитория*: {info['audience']}")
        else:
            lines.append("• *Аудитория*: не указано")

        if info.get('website', '').strip():
            lines.append(f"• *Сайт*: {clean_url(info['website'])}")
        else:
            lines.append("• *Сайт*: не указан")

        if has_data:
            lines.append("\nХочешь изменить — нажми «Изменить информацию об НКО» в главном меню")
        else:
            lines.append("\nХочешь предоставить информацию об НКО — нажми «Предоставить информацию об НКО» в главном меню")

        await update.message.reply_text(
            "\n".join(lines),
            reply_markup=BACK_TO_MAIN,
            parse_mode='Markdown',
            **kw
        )

    async def handle_nco(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, **kw) -> bool:
        waiting = context.user_data.get('waiting')
        if not waiting or not waiting.startswith('nco_'):
            return False

        user_id = update.effective_user.id

        try:
            # === "НАЗАД В ГЛАВНОЕ МЕНЮ" ТОЛЬКО НА ПЕРВОМ ШАГЕ ===
            if waiting == 'nco_name' and text == "Назад в главное меню":
                context.user_data.clear()
                from .handlers_nco import get_main_keyboard
                has_data = self.has_data(user_id)
                await update.message.reply_text(
                    "Хорошо, возвращаемся. Если нужно — просто скажи!",
                    reply_markup=get_main_keyboard(has_data),
                    **kw
                )
                return True

            # === КНОПКА "НАЗАД" (на всех шагах, кроме первого) ===
            if text == "Назад" and waiting != 'nco_name':
                prev = {
                    'nco_activities': 'nco_name',
                    'nco_audience': 'nco_activities',
                    'nco_website': 'nco_audience'
                }[waiting]
                context.user_data['waiting'] = prev
                markup = BACK_FIRST if prev == 'nco_name' else BACK_SKIP_CLEAR
                await update.message.reply_text(STEP_TEXTS[prev], reply_markup=markup, parse_mode='Markdown', **kw)
                return True

            # === ПРОПУСТИТЬ / ОЧИСТИТЬ ===
            if text in ["Пропустить", "Очистить"] and waiting in STEP_TEXTS:
                field = {'nco_name': 'name', 'nco_activities': 'activities',
                         'nco_audience': 'audience', 'nco_website': 'website'}[waiting]
                value = self._get(user_id)[field] if text == "Пропустить" else ""
                next_step = {'nco_name': 'nco_activities', 'nco_activities': 'nco_audience',
                             'nco_audience': 'nco_website', 'nco_website': None}[waiting]
                await self.save_field(update, context, field, value, next_step, **kw)
                return True

            # === ВВОД ЗНАЧЕНИЯ ===
            if waiting in STEP_TEXTS:
                field = {'nco_name': 'name', 'nco_activities': 'activities',
                         'nco_audience': 'audience', 'nco_website': 'website'}[waiting]
                next_step = {'nco_name': 'nco_activities', 'nco_activities': 'nco_audience',
                             'nco_audience': 'nco_website', 'nco_website': None}[waiting]

                # Защита от пустого ввода
                if not text.strip():
                    await update.message.reply_text("Пожалуйста, введи текст или нажми «Пропустить».", **kw)
                    return True

                print(f"[DEBUG] Обрабатываю ввод для {waiting}: {text}")  # Для дебага
                await self.save_field(update, context, field, text, next_step, **kw)
                return True

        except Exception as e:
            print(f"[ERROR] handle_nco: {e}")
            await update.message.reply_text(f"Ошибка в обработке: {str(e)}. Попробуй заново.", **kw)
            context.user_data.clear()
            return True

        return False

    def get_nco_info(self, update: Update) -> dict:
        raw = self._get(update.effective_user.id)
        cleaned = raw.copy()
        if cleaned.get('website'):
            cleaned['website'] = clean_url(cleaned['website'])
        return cleaned
