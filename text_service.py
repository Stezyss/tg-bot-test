from yandex_cloud_ml_sdk import YCloudML
from typing import Optional, Dict
from config import Config


class TextService:
    def __init__(self, config: Config):
        self.sdk = YCloudML(
            folder_id=config.YANDEX_FOLDER_ID,
            auth=config.YANDEX_OAUTH_TOKEN,
        )
        self.sdk.setup_default_logging()

        # Синхронная модель (без async_models — используем run())
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
                f"• Деятельность: {nko_info.get('activities', '')}\n\n"
            )

        style_hint = f"Стиль: {style}. " if style else ""
        full_prompt = f"{self.system_prompt}\n\n{context}{style_hint}Запрос: {user_prompt}"

        # Синхронный вызов — возвращает результат сразу
        result = self.model.run(full_prompt)
        return result.alternatives[0].text.strip()

    def edit_text(self, text: str, nko_info: Optional[dict] = None) -> str:
        prompt = f"Отредактируй этот текст для соцсетей НКО. Сделай ярче, человечнее, с призывом:\n\n{text}"
        return self.generate_text(prompt, nko_info)

    def generate_content_plan(self, period: str, frequency: str, nko_info: Optional[dict] = None) -> str:
        prompt = f"Составь контент-план для НКО на {period} с частотой {frequency}. 10–30 идей с датами и типами постов."
        return self.generate_text(prompt, nko_info)

    def check_health(self) -> bool:
        try:
            result = self.model.run("Ответь одним словом: ок")
            return "ок" in result.alternatives[0].text.lower()
        except Exception as e:
            print(f"Health check error: {e}")
            return False