import sys
import asyncio
from config import Config
from ai_service import AIService

"""
Модуль выполняет отдельную проверку доступности Yandex AI API.

Используется для диагностики перед запуском бота или сервера.
Проверяет корректность конфигурации, доступность токенов и возможность
успешного обращения к Yandex AI API.
"""

async def check_ai_api():
    #Проверяет доступность Yandex AI API через сервис AIService.
    try:
        # Загружаем конфигурацию из переменных окружения
        config = Config.from_env()
        ai_service = AIService(config)
        result = await ai_service.check_health()# Проверяем доступность API
        print('✅ Yandex AI API доступен.' if result else '❌ Yandex AI API недоступен.')
        return result
    except Exception as e:
        # Выводим ошибку диагностики
        print(f'Ошибка проверки: {e}')
        return False

if __name__ == '__main__':
    # Запускаем асинхронную проверку и возвращаем код завершения
    result = asyncio.run(check_ai_api())
    sys.exit(0 if result else 1)
