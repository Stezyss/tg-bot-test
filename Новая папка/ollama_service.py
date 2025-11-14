import httpx
from typing import Optional, AsyncGenerator
from config import Config


class OllamaService:
    def __init__(self, config: Config):
        self.base_url = config.OLLAMA_BASE_URL
        self.text_model = config.TEXT_MODEL
        self.timeout = config.REQUEST_TIMEOUT

    async def generate_text(self, prompt: str, stream: bool = False) -> str:
        url = f'{self.base_url}/api/generate'
        payload = {
            'model': self.text_model,
            'prompt': prompt,
            'stream': stream
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                if stream:
                    return await self._handle_stream(response)
                else:
                    result = response.json()
                    return result.get('response', '')
        except httpx.HTTPError as e:
            raise RuntimeError(f'Ошибка HTTP при генерации текста: {str(e)}')
        except Exception as e:
            raise RuntimeError(f'Неожиданная ошибка при генерации текста: {str(e)}')

    async def generate_text_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        url = f'{self.base_url}/api/generate'
        payload = {
            'model': self.text_model,
            'prompt': prompt,
            'stream': True
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream('POST', url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                import json
                                data = json.loads(line)
                                if 'response' in data:
                                    yield data['response']
                            except json.JSONDecodeError:
                                continue
        except httpx.HTTPError as e:
            raise RuntimeError(f'Ошибка HTTP при потоковой генерации: {str(e)}')
        except Exception as e:
            raise RuntimeError(f'Неожиданная ошибка при потоковой генерации: {str(e)}')

    async def get_models(self) -> list:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f'{self.base_url}/api/tags')
                response.raise_for_status()
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
        except Exception:
            return []

    async def check_health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f'{self.base_url}/api/tags')
                return response.status_code == 200
        except Exception:
            return False

