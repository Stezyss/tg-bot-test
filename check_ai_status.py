import sys
import asyncio
from config import Config
from ai_service import AIService

async def check_ai_api():
    try:
        config = Config.from_env()
        ai_service = AIService(config)
        result = await ai_service.check_health()
        print('✅ Yandex AI API доступен.' if result else '❌ Yandex AI API недоступен.')
        return result
    except Exception as e:
        print(f'Ошибка проверки: {e}')
        return False

if __name__ == '__main__':
    result = asyncio.run(check_ai_api())
    sys.exit(0 if result else 1)