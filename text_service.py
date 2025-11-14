from yandex_cloud_ml_sdk import YCloudML
from typing import Optional, Dict
from datetime import datetime, timedelta
from config import Config


class TextService:
    def __init__(self, config: Config):
        self.sdk = YCloudML(
            folder_id=config.YANDEX_FOLDER_ID,
            auth=config.YANDEX_OAUTH_TOKEN,
        )
        self.sdk.setup_default_logging()

        self.model = self.sdk.models.completions('yandexgpt')
        self.model = self.model.configure(temperature=0.7, max_tokens=1500)

        self.system_prompt = config.AI_SYSTEM_PROMPT

    def generate_text(self, user_prompt: str, nko_info: Optional[dict] = None, style: Optional[str] = None) -> str:
        context = ""
        if nko_info and any(nko_info.values()):
            context = (
                f"Информация об НКО:\n"
                f"• Название: {nko_info.get('name', '')}\n"
                f"• Миссия: {nko_info.get('description', '')}\n"
                f"• Деятельность: {nko_info.get('activities', '')}\n"
                f"• Аудитория: {nko_info.get('audience', '')}\n"
                f"• Сайт: {nko_info.get('website', '')}\n"
                f"• Соцсети: {nko_info.get('socials', '')}\n"
                f"• Контакты: {nko_info.get('contacts', '')}\n"
                f"• Цвета: {nko_info.get('colors', '')}\n\n"
            )

        style_hint = f"Стиль: {style}. " if style else ""
        full_prompt = f"{self.system_prompt}\n\n{context}{style_hint}Запрос: {user_prompt}"

        result = self.model.run(full_prompt)
        return result.alternatives[0].text.strip()

    def edit_text(self, text: str, nko_info: Optional[dict] = None) -> str:
        prompt = f"Отредактируй этот текст для соцсетей НКО. Сделай ярче, человечнее, с призывом:\n\n{text}"
        return self.generate_text(prompt, nko_info)

    def generate_content_plan(
        self,
        period: str,
        frequency: str,
        nko_info: Optional[dict] = None,
        start_date: Optional[datetime.date] = None
    ) -> str:
        if start_date is None:
            start_date = datetime.now().date()

        if period == "неделя":
            end_date = start_date + timedelta(days=6)
            days = 7
        else:  # месяц
            end_date = start_date + timedelta(days=29)
            days = 30

        interval_map = {
            "1 раз в день": 1,
            "2 раза в неделю": 3.5,
            "3 раза в неделю": 2.33,
            "1 раз в неделю": 7,
            "2 раза в месяц": 15
        }
        interval = interval_map.get(frequency, 7)
        post_dates = []
        i = 0
        current = start_date
        while current <= end_date:
            post_dates.append(current)
            i += 1
            current = start_date + timedelta(days=int(i * interval))

        context = ""
        if nko_info and any(nko_info.values()):
            context = (
                f"Информация об НКО:\n"
                f"• Название: {nko_info.get('name', '')}\n"
                f"• Миссия: {nko_info.get('description', '')}\n"
                f"• Деятельность: {nko_info.get('activities', '')}\n"
                f"• Аудитория: {nko_info.get('audience', '')}\n"
                f"• Сайт: {nko_info.get('website', '')}\n"
                f"• Соцсети: {nko_info.get('socials', '')}\n"
                f"• Контакты: {nko_info.get('contacts', '')}\n"
                f"• Цвета: {nko_info.get('colors', '')}\n\n"
            )

        prompt = (
            f"{self.system_prompt}\n\n"
            f"{context}"
            f"Составь контент-план на {period} с частотой «{frequency}», начиная с {start_date.strftime('%d.%m.%Y')}.\n"
            f"Даты публикаций: {', '.join(d.strftime('%d.%m') for d in post_dates)}\n"
            f"Для каждой даты: 1 идея поста (тип + краткое описание). Всего 10–30 идей.\n"
            f"Формат: [дд.мм] — Тип: Краткое описание"
        )

        result = self.model.run(prompt)
        return result.alternatives[0].text.strip()

    def check_health(self) -> bool:
        try:
            result = self.model.run("Ответь одним словом: ок")
            return "ок" in result.alternatives[0].text.lower()
        except Exception as e:
            print(f"Health check error: {e}")
            return False
