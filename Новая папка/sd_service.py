import httpx
import base64
from typing import Optional
from config import Config


class StableDiffusionService:
    def __init__(self, config: Config):
        self.api_url = config.SD_API_URL
        self.enabled = config.SD_ENABLED
        self.timeout = config.IMAGE_TIMEOUT

    async def generate_image(
        self, 
        prompt: str, 
        negative_prompt: str = "low quality, blurry, ugly, distorted",
        width: int = 512,
        height: int = 512,
        steps: int = 20
    ) -> Optional[bytes]:
        if not self.enabled:
            raise RuntimeError('Генерация изображений отключена в конфигурации')

        url = f'{self.api_url}/sdapi/v1/txt2img'
        
        payload = {
            'prompt': prompt,
            'negative_prompt': negative_prompt,
            'width': width,
            'height': height,
            'steps': steps,
            'sampler_name': 'DPM++ 2M Karras',
            'cfg_scale': 7,
            'batch_size': 1,
            'n_iter': 1
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                images = result.get('images', [])
                
                if not images:
                    return None
                
                image_data = images[0]
                return base64.b64decode(image_data)
                
        except httpx.ConnectError:
            raise RuntimeError(
                'Не удалось подключиться к Stable Diffusion API. '
                'Убедитесь, что Automatic1111 WebUI запущен с флагом --api'
            )
        except httpx.TimeoutException:
            raise RuntimeError('Превышено время ожидания генерации изображения')
        except httpx.HTTPError as e:
            raise RuntimeError(f'Ошибка HTTP при генерации изображения: {str(e)}')
        except Exception as e:
            raise RuntimeError(f'Неожиданная ошибка при генерации изображения: {str(e)}')

    async def check_health(self) -> bool:
        if not self.enabled:
            return False
            
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f'{self.api_url}/sdapi/v1/sd-models')
                return response.status_code == 200
        except Exception:
            return False

    async def get_models(self) -> list:
        if not self.enabled:
            return []
            
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f'{self.api_url}/sdapi/v1/sd-models')
                response.raise_for_status()
                models = response.json()
                return [model.get('title', model.get('model_name', 'Unknown')) for model in models]
        except Exception:
            return []

