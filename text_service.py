# text_service.py
from yandex_cloud_ml_sdk import YCloudML
from typing import Optional
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

    def generate_text(self, user_prompt: str, nco_info: Optional[dict] = None, style: Optional[str] = None) -> str:
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

    def edit_text_with_action(self, text: str, action: str, nco_info: Optional[dict] = None, style: Optional[str] = None) -> str:
        if action == "Увеличить текст":
            prompt = f"Расширь этот текст для соцсетей НКО, добавь детали, эмоции, сделай ярче и с призывом к действию:\n\n{text}"
        elif action == "Сократи текст":
            prompt = f"Сократи этот текст для соцсетей НКО, сохрани суть, сделай ярче и с призывом:\n\n{text}"
        elif action == "Исправить ошибки":
            prompt = f"Исправь орфографические, грамматические, логические и речевые ошибки в этом тексте. Сделай готовый пост для НКО — яркий, человечный, с призывом:\n\n{text}"
        elif action == "Перефразировать":
            prompt = f"Перефразируй этот текст для соцсетей НКО, сохрани смысл, сделай ярче, человечнее, с призывом:\n\n{text}"
        elif action == "Изменить стиль":
            style_name = "без стиля" if style is None else style
            prompt = f"Перепиши этот текст в {style_name} стиле для НКО, сделай ярко, с призывом:\n\n{text}"
        else:
            prompt = f"Отредактируй этот текст для соцсетей НКО. Сделай ярче, человечнее, с призывом:\n\n{text}"

        return self.generate_text(prompt, nco_info)

    def edit_text(self, text: str, nco_info: Optional[dict] = None) -> str:
        return self.edit_text_with_action(text, "default", nco_info)

    def generate_content_plan(
        self,
        period: str,
        frequency: str,
        nco_info: Optional[dict] = None,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None,
        theme: Optional[str] = None
    ) -> str:
        if start_date is None:
            start_date = datetime.now().date()

        if period == "неделя":
            end_date = start_date + timedelta(days=6)
            days = 7
        elif period == "месяц":
            end_date = start_date + timedelta(days=29)
            days = 30
        elif period == "custom":
            if end_date is None:
                raise ValueError("Для custom периода требуется end_date")
            days = (end_date - start_date).days + 1
        else:
            raise ValueError("Неверный период")

        interval_map = {
            "1 раз в день": 1,
            "2 раза в неделю": 3.5,
            "3 раза в неделю": 2.33,
            "1 раз в неделю": 7,
            "2 раза в месяц": 15
        }
        interval = interval_map.get(frequency, 7)

        num_posts = max(1, int(days / interval))
        if num_posts > 30:
            num_posts = 30
        step = days / num_posts if num_posts > 0 else 1
        post_dates = [start_date + timedelta(days=int(i * step)) for i in range(num_posts)]

        context = ""
        if nco_info and any(nco_info.values()):
            context = (
                f"Информация об НКО:\n"
                f"* Название: {nco_info.get('name', '')}\n"
                f"* Деятельность: {nco_info.get('activities', '')}\n"
                f"* Аудитория: {nco_info.get('audience', '')}\n"
                f"* Сайт: {nco_info.get('website', '')}\n\n"
            )

        theme_hint = f"Тема: {theme}\n" if theme else ""
        period_desc = period if period != "custom" else f"с {start_date.strftime('%d.%m.%Y')} по {end_date.strftime('%d.%m.%Y')}"
        prompt = (
            f"{self.system_prompt}\n\n"
            f"{context}"
            f"{theme_hint}"
            f"Составь контент-план на {period_desc} с частотой «{frequency}», начиная с {start_date.strftime('%d.%m.%Y')}.\n"
            f"Даты публикаций: {', '.join(d.strftime('%d.%m') for d in post_dates)}\n"
            f"Для каждой даты: 1 идея поста (тип + краткое описание). Всего {num_posts} идей.\n"
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
