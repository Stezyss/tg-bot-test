# image_service.py
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

    async def generate_image(self, prompt: str, nco_info: Optional[dict] = None, style: Optional[str] = None) -> Optional[bytes]:
        # --- Контекст НКО ---
        context = ""
        if nco_info and nco_info.get('name'):
            context = f"Для НКО «{nco_info['name']}», тема: {nco_info.get('description', '')}. "

        # --- Стиль: ЯВНО УКАЗЫВАЕМ ---
        style_part = ""
        if style:
            style_map = {
                "реализм": "Реалистичный фотореализм: максимальная правдоподобность, детализированные материалы и текстуры, естественный свет и тени. ",
                "мультяшный": "Выраженный мультяшный стиль в духе Pixar: насыщенные цвета, мягкие формы, чистые контуры. Гладкие поверхности без реализма, лёгкие блики, подчёркнутый объём. Преувеличенные эмоции, тёплая яркая палитра, упрощённые детали, сказочная дружелюбная стилизация.",
                "акварель": "Классическая акварель: мягкие переходы, размывы, прозрачные слои, естественные светотени. Нежная палитра, отсутствие жёстких контуров, фактура бумаги. Воздушность и живописность ручной работы, без цифровых резких линий и мультяшности.",
                "киберпанк": "Киберпанк: яркий неон, контрастные подсветки, тёмная футуристическая атмосфера. Техно-архитектура, металлические и стеклянные поверхности, голограммы, отражения на мокром асфальте. Плотный мегаполис, дроны, провода, цифровой шум, индустриальный и виртуальный антураж будущего."
            }
            style_part = style_map.get(style.lower(), style) + ". "

        # --- Запрещаем --- без текста на изображении,Глубокая резкость, мягкие переходы, физкорректное освещение, натуральные цвета. Атмосфера настоящей фотографии: высокого качества, без стилизации и мультяшности.
        ban = ""

        # --- Финальный промт ---
        full_prompt = [
            f"{context}{prompt} {style_part}. {ban}",
            "эмоционально, тепло, высокое качество, текста на изображении, профессиональная композиция"
        ]

        print(f"[ART] Промт: {full_prompt[0][:500]}...")

        try:
            operation = await self.model.run_deferred(full_prompt)
            result = await operation
            return result.image_bytes
        except Exception as e:
            print(f"[ART] Ошибка: {e}")
            return None
