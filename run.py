# run.py
from dotenv import load_dotenv
import sys
import os

def check_environment():
    required = ['TELEGRAM_BOT_TOKEN', 'YANDEX_FOLDER_ID', 'YANDEX_OAUTH_TOKEN', 'YANDEX_IAM_TOKEN']
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        print(f"Ошибка: отсутствуют переменные окружения: {', '.join(missing)}")
        sys.exit(1)

if __name__ == '__main__':
    load_dotenv()
    check_environment()
    from main import main
    main()
