from dotenv import load_dotenv
import sys
import os

def check_environment():
    required_vars = ['TELEGRAM_BOT_TOKEN']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f'Ошибка: отсутствуют обязательные переменные окружения: {", ".join(missing_vars)}')
        print('Создайте файл .env на основе .env.example и заполните необходимые значения.')
        sys.exit(1)

if __name__ == '__main__':
    load_dotenv()
    check_environment()
    
    from main import main
    main()