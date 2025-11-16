"""
Сервис для генерации текста, редактирования и создания контент-планов
через YandexGPT (Yandex Cloud ML SDK).

Функциональность:
- генерация нового текста для постов
- редактирование текста по действию (увеличить, сократить, исправить ошибки, перефразировать, изменить стиль)
- создание контент-плана по периоду и частоте
- проверка доступности модели (health check)

Все функции используют общий системный промпт, а также могут учитывать
информацию об НКО: название, деятельность, аудиторию и сайт.
"""

from yandex_cloud_ml_sdk import YCloudML
from typing import Optional
from datetime import datetime, timedelta
from config import Config
import re


class TextService:
    """
    Сервис для работы с текстом через YandexGPT.

    Возможности:
        - генерация текстов
        - редактирование с разными действиями
        - создание контент-планов
        - проверка состояния модели
    """

    def __init__(self, config: Config):
        # Инициализация SDK
        self.sdk = YCloudML(
            folder_id=config.YANDEX_FOLDER_ID,
            auth=config.YANDEX_OAUTH_TOKEN,
        )
        self.sdk.setup_default_logging()

        # Настройка языковой модели
        self.model = self.sdk.models.completions('yandexgpt')
        self.model = self.model.configure(temperature=0.7, max_tokens=1500)

        # Системный промпт из конфига
        self.system_prompt = config.AI_SYSTEM_PROMPT

    #  ГЕНЕРАЦИЯ ТЕКСТА

    def generate_text(self, user_prompt: str, nco_info: Optional[dict] = None,
                      style: Optional[str] = None) -> str:
        """
        Генерация текста с учётом системного промпта, данных НКО и стиля.

        Параметры:
            user_prompt (str): основной запрос пользователя.
            nco_info (dict | None): информация об НКО.
            style (str | None): выбранный стиль.

        Возвращает:
            str — сгенерированный текст.
        """

        context = ""
        if nco_info and any(nco_info.values()):
            context = (
                f"Информация об НКО:\n"
                f"* Название: {nco_info.get('name', '')}\n"
                f"* Деятельность: {nco_info.get('activities', '')}\n"
                f"* Аудитория: {nco_info.get('audience', '')}\n"
                f"* Сайт: {nco_info.get('website', '')}\n\n"
            )

        style_hint = f"Стиль: {style}. " if style else ""
        full_prompt = f"{self.system_prompt}\n\n{context}{style_hint}Запрос: {user_prompt}"

        result = self.model.run(full_prompt)
        return result.alternatives[0].text.strip()

    #  РЕДАКТИРОВАНИЕ ТЕКСТА

    def edit_text_with_action(self, text: str, action: str,
                              nco_info: Optional[dict] = None,
                              style: Optional[str] = None) -> str:
        """
        Выполняет редактирование текста в зависимости от выбранного действия.

        Параметры:
            text (str): исходный текст.
            action (str): действие (увеличить, сократить, исправить ошибки и т.д.).
            nco_info (dict | None): данные об НКО.
            style (str | None): выбранный стиль (для действия "Изменить стиль").

        Возвращает:
            str — отредактированный текст.
        """

        if action == "Увеличить текст":
            prompt = (
                f"Расширь этот текст для соцсетей НКО, добавь детали, эмоции, сделай ярче и с призывом к действию:\n\n{text}\n\n"
                "Результатом должен стать отредактированный текст пользователя ..."
            )
        elif action == "Сократи текст":
            prompt = (
                f"Сократи этот текст для соцсетей НКО ...\n\n{text}\n\n"
                "Результатом должен стать отредактированный текст пользователя ..."
            )
        elif action == "Исправить ошибки":
            prompt = (
                f"Исправь орфографические, грамматические ...\n\n{text}\n\n"
                "Результатом должен стать отредактированный текст пользователя ..."
            )
        elif action == "Перефразировать":
            prompt = (
                f"Перефразируй этот текст ...\n\n{text}\n\n"
                "Результатом должен стать отредактированный текст пользователя ..."
            )
        elif action == "Изменить стиль":
            style_name = "без стиля" if style is None else style
            prompt = (
                f"Перепиши этот текст в {style_name} стиле ...\n\n{text}\n\n"
                "Результатом должен стать отредактированный текст пользователя ..."
            )
        else:
            prompt = (
                f"Отредактируй этот текст ...\n\n{text}\n\n"
                "Результатом должен стать отредактированный текст пользователя ..."
            )

        return self.generate_text(prompt, nco_info)

    def edit_text(self, text: str, nco_info: Optional[dict] = None) -> str:
        """
        Упрощённая функция редактирования по умолчанию.
        """
        return self.edit_text_with_action(text, "default", nco_info)

    #  ГЕНЕРАЦИЯ КОНТЕНТ-ПЛАНА

    def generate_content_plan(
        self,
        period: str,
        frequency: str,
        nco_info: Optional[dict] = None,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None,
        theme: Optional[str] = None
    ) -> str:
        """
        Генерация контент-плана по выбранному периоду и частоте.

        Параметры:
            period (str): "неделя", "месяц", "custom".
            frequency (str): частота публикаций.
            nco_info (dict | None): данные об НКО.
            start_date (date | None): дата начала.
            end_date (date | None): дата окончания (для custom).
            theme (str | None): тема контент-плана.

        Возвращает:
            str — готовый контент-план.
        """

        if start_date is None:
            start_date = datetime.now().date()

        # Обработка периода
        if period == "неделя":
            end_date = start_date + timedelta(days=6)
            total_days = 7
        elif period == "месяц":
            end_date = start_date + timedelta(days=29)
            total_days = 30
        elif period == "custom":
            if end_date is None:
                raise ValueError("Для custom периода требуется end_date")
            total_days = (end_date - start_date).days + 1
        else:
            raise ValueError("Неверный период")

        # Нормализация частоты
        freq_lower = frequency.lower().strip()
        freq_clean = re.sub(r"[^\w\s]", "", freq_lower)

        if "1 раз в день" in freq_clean:
            normalized = "1 раз в день"
        elif "1 раз в неделю" in freq_clean:
            normalized = "1 раз в неделю"
        elif "2 раза в неделю" in freq_clean:
            normalized = "2 раза в неделю"
        elif "3 раза в неделю" in freq_clean:
            normalized = "3 раза в неделю"
        elif "2 раза в месяц" in freq_clean:
            normalized = "2 раза в месяц"
        else:
            normalized = "1 раз в неделю"

        # Расчёт количества постов
        if normalized == "1 раз в день":
            num_posts = total_days
        elif normalized == "1 раз в неделю":
            num_posts = max(1, (total_days + 6) // 7)
        elif normalized == "2 раза в неделю":
            num_posts = max(1, (total_days * 2 + 6) // 7)
        elif normalized == "3 раза в неделю":
            num_posts = max(1, (total_days * 3 + 6) // 7)
        elif normalized == "2 раза в месяц":
            num_posts = 2
        else:
            num_posts = 4

        num_posts = min(num
