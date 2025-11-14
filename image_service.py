from yandex_cloud_ml_sdk import AsyncYCloudML
from typing import Optional
from config import Config


class ImageService:
    def __init__(self, config: Config):
        self.sdk = AsyncYCloudML(
            folder_id=config.YANDEX_FOLDER_ID,
            auth=config.YANDEX_OAUTH_TOKEN,
        )
        self.sdk.setup_default_logging()

        self.model = self.sdk.models.image_generation('yandex-art')
        self.model = self.model.configure(width_ratio=1, height_ratio=2, seed=42)

    async def generate_image(self, prompt: str, nko_info: Optional[dict] = None) -> Optional[bytes]:
        context = ""
        if nko_info and nko_info.get('name'):
            context = f"Для НКО «{nko_info['name']}», тема: {nko_info.get('description', '')}. "
#Изменить
        full_prompt = [
            f"{context}{prompt}",
            "стиль Хаяо Миядзаки, студия Гибли, пастельные тона, эмоционально, тепло, высокое качество, без текста"
        ]

        try:
            operation = await self.model.run_deferred(full_prompt)
            result = await operation
            return result.image_bytes
        except Exception as e:
            print(f"Ошибка генерации изображения: {e}")
            return None