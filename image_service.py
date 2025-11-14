from typing import Optional
from config import Config

class ImageService(Config):
    def init(self, config: Config):
        pass  # Заглушка

    async def generate_image(self, prompt: str) -> Optional[bytes]:
        raise RuntimeError('Генерация изображений не реализована в этом коде')  # Заглушка
