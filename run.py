# run.py
from dotenv import load_dotenv
import sys
import os

def check_environment():
    """
    Проверяет наличие необходимых переменных окружения.

    Функция формирует список обязательных переменных, затем проверяет,
    существуют ли они в текущей среде. Если какие-то переменные
    отсутствуют, программа выводит сообщение об ошибке и завершает работу.
    """
    
    required = ['TELEGRAM_BOT_TOKEN', 'YANDEX_FOLDER_ID', 'YANDEX_OAUTH_TOKEN', 'YANDEX_IAM_TOKEN']

    # Фильтрация переменных, отсутствующих в окружении
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        print(f"Ошибка: отсутствуют переменные окружения: {', '.join(missing)}")
        sys.exit(1) # Принудительное завершение программы

if __name__ == '__main__':
    # Загружаем переменные окружения из .env файла
    load_dotenv()
    # Проверяем корректность конфигурации
    check_environment()
    # Принудительное завершение программы
    from main import main
    main()
