import httpx
import asyncio
import sys


async def check_sd_api():
    url = 'http://localhost:7860/sdapi/v1/sd-models'
    
    print('Проверка доступности Stable Diffusion API...')
    print('URL:', url)
    print()
    
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                models = response.json()
                print('✅ Stable Diffusion API работает!')
                print(f'Найдено моделей: {len(models)}')
                
                if models:
                    print('\nДоступные модели:')
                    for model in models:
                        title = model.get('title', model.get('model_name', 'Unknown'))
                        print(f'  • {title}')
                else:
                    print('\n⚠️ Модели не найдены. Скачайте модель в models/Stable-diffusion/')
                
                return True
            else:
                print(f'❌ Получен код ответа: {response.status_code}')
                return False
                
    except httpx.ConnectError:
        print('❌ Не удалось подключиться к API')
        print('WebUI еще не запущен или запускается...')
        print('Подождите и попробуйте еще раз')
        return False
    except httpx.TimeoutException:
        print('❌ Превышено время ожидания')
        return False
    except Exception as e:
        print(f'❌ Ошибка: {e}')
        return False


if __name__ == '__main__':
    result = asyncio.run(check_sd_api())
    sys.exit(0 if result else 1)

