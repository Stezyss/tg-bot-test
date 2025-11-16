"""
Модуль для генерации изображений через Yandex Cloud ML SDK.

Содержит класс ImageService, предоставляющий удобный интерфейс для
создания изображений на основе текстового промпта, стиля и контекста НКО.
Использует модель `yandex-art` с предварительной конфигурацией.
"""
from yandex_cloud_ml_sdk import AsyncYCloudML
from typing import Optional
from config import Config


class ImageService:
    """
    Сервис генерации изображений на базе Yandex Cloud ML.

    Возможности:
    - подключение к Yandex Cloud ML SDK,
    - настройка модели генерации изображений,
    - генерация изображений с учётом стиля и данных об НКО.
    """
    
    def __init__(self, config: Config):
        # Инициализация клиента SDK
        self.sdk = AsyncYCloudML(
            folder_id=config.YANDEX_FOLDER_ID,
            auth=config.YANDEX_OAUTH_TOKEN,
        )
        # Включение логирования SDK
        self.sdk.setup_default_logging()
        
        # Настройка модели yandex-art
        self.model = self.sdk.models.image_generation('yandex-art')
        self.model = self.model.configure(width_ratio=1, height_ratio=2, seed=42)

    async def generate_image(self, prompt: str, nco_info: Optional[dict] = None, style: Optional[str] = None) -> Optional[bytes]:
        """
        Генерирует изображение на основе текста промпта, стиля и данных об НКО.
        Возвращает: байты изображения или None при ошибке.
        """
        context = ""
        # Формируем контекст, если есть данные об НКО
        if nco_info and nco_info.get('name'):
            context = f"Для НКО «{nco_info['name']}». "
            
        # Добавляем стиль, если указан
        style_part = ""
        if style:
            style_map = {
                "реализм": "Реалистичный фотореализм: максимальная правдоподобность, детализированные материалы и текстуры, естественный свет и тени. ",
                "мультяшный": "Выраженный мультяшный стиль в духе Pixar: насыщенные цвета, мягкие формы, чистые контуры. Преувеличенные эмоции",
                "акварель": "Классическая акварель: мягкие переходы, размывы, прозрачные слои, естественные светотени. Нежная палитра, отсутствие жёстких контуров, фактура бумаги. Ручная работа, без цифровых резких линий и мультяшности.",
                "киберпанк": "Киберпанк: яркий неон, футуристическая атмосфера. Техно-архитектура, голограммы. Цифровой шум, индустриальный и виртуальный антураж будущего."
            }
            style_part = style_map.get(style.lower(), style) + ". "
            
        # Итоговый промпт для генерации изображения
        full_prompt = [
            f"{context}{prompt} {style_part}",
            "эмоционально, тепло, высокое качество, без текста на изображении, профессиональная композиция"
        ]

        print(f"[ART] Промт: {full_prompt[0][:500]}...")
        
        # Запуск генерации
        try:
            operation = await self.model.run_deferred(full_prompt)
            result = await operation
            return result.image_bytes
        except Exception as e:
            print(f"[ART] Ошибка: {e}")
            return None
