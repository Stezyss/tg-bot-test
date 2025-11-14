from dotenv import load_dotenv
import sys
import os

def check_environment():
    required_vars = ['TELEGRAM_BOT_TOKEN', 'YANDEX_FOLDER_ID', 'YANDEX_OAUTH_TOKEN']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f'Ошибка: отсутствуют переменные: {", ".join(missing_vars)}')
        print('Создайте .env: TELEGRAM_BOT_TOKEN=..., YANDEX_FOLDER_ID=..., YANDEX_OAUTH_TOKEN=...')
        sys.exit(1)

if __name__ == '__main__':
    load_dotenv()
    check_environment()
    
    from main import main
    main()
