import os
from dataclasses import dataclass


@dataclass
class Config:
    TELEGRAM_BOT_TOKEN: str
    YANDEX_FOLDER_ID: str
    YANDEX_OAUTH_TOKEN: str
    AI_SYSTEM_PROMPT: str = (
        "Ты — профессиональный SMM-менеджер и копирайтер для НКО. "
        "Пиши эмоциональные, вдохновляющие посты на русском языке. "
        "Добавляй 3–5 хештегов в конце. Используй призывы к действию. "
        "Если есть информация об НКО — используй её естественно."
    )

    @classmethod
    def from_env(cls):
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        folder_id = os.getenv('YANDEX_FOLDER_ID')
        oauth_token = os.getenv('YANDEX_OAUTH_TOKEN')

        if not all([token, folder_id, oauth_token]):
            missing = [k for k, v in {
                'TELEGRAM_BOT_TOKEN': token,
                'YANDEX_FOLDER_ID': folder_id,
                'YANDEX_OAUTH_TOKEN': oauth_token
            }.items() if not v]
            raise ValueError(f"Отсутствуют переменные: {', '.join(missing)}")

        return cls(
            TELEGRAM_BOT_TOKEN=token,
            YANDEX_FOLDER_ID=folder_id,
            YANDEX_OAUTH_TOKEN=oauth_token
        )