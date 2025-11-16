"""
Модуль конфигурации бота.
Отвечает за загрузку переменных окружения, проверку обязательных данных
и предоставление единого объекта конфигурации для других частей системы.
Использует dataclass для удобного хранения параметров.
"""
import os
from dataclasses import dataclass


@dataclass
class Config:
    """
    Конфигурация бота.
    
    Содержит:
    - TELEGRAM_BOT_TOKEN: токен Telegram-бота.
    - YANDEX_FOLDER_ID: ID каталога в Yandex Cloud.
    - YANDEX_OAUTH_TOKEN: OAuth-токен (может использоваться для обновления IAM).
    - YANDEX_IAM_TOKEN: актуальный IAM-токен Yandex Cloud.
    - AI_SYSTEM_PROMPT: системный промпт для генерации текстов.
    """
    
    TELEGRAM_BOT_TOKEN: str
    YANDEX_FOLDER_ID: str
    YANDEX_OAUTH_TOKEN: str
    YANDEX_IAM_TOKEN: str
    AI_SYSTEM_PROMPT: str = (
        "Ты — профессиональный SMM-менеджер и копирайтер для НКО. "
        "Пиши эмоциональные, вдохновляющие посты на русском языке. "
        "Если есть информация об НКО — используй её естественно."
	"Если не уверен, относится ли тема хэштэга (#) к теме поста, то лучше не добавляй."
	"При перечислении используй цифры."
	"Не используй звездочки (**) и специальные символы для форматирования текста"
	"Добавляй 3–5 хештегов(#) в конце, после хэштегов не должно быть текста. Используй призывы к действию."
        "Кроме того, предложи пользователю идеи визуалов для соцсетей и пиши эту информацию ниже от поста, отделив её с помощью эмодзи и при перечислении используй цифры."
    )

    @classmethod
    def from_env(cls):
        """
        Создаёт объект конфигурации, загружая параметры из переменных окружения.
        Если обязательные переменные отсутствуют — выбрасывает ValueError.
        """
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        folder_id = os.getenv('YANDEX_FOLDER_ID')
        oauth_token = os.getenv('YANDEX_OAUTH_TOKEN')
        iam_token = os.getenv('YANDEX_IAM_TOKEN')

        if not all([token, folder_id, oauth_token, iam_token]):
            missing = [k for k, v in {
                'TELEGRAM_BOT_TOKEN': token,
                'YANDEX_FOLDER_ID': folder_id,
                'YANDEX_OAUTH_TOKEN': oauth_token,
                'YANDEX_IAM_TOKEN': iam_token
            }.items() if not v]
            raise ValueError(f"Отсутствуют: {', '.join(missing)}")
        # Возвращаем инициализированный объект
        return cls(
            TELEGRAM_BOT_TOKEN=token,
            YANDEX_FOLDER_ID=folder_id,
            YANDEX_OAUTH_TOKEN=oauth_token,
            YANDEX_IAM_TOKEN=iam_token
        )
