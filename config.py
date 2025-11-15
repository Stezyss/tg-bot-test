# config.py
import os
from dataclasses import dataclass


@dataclass
class Config:
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
	"Не используй звёздочки (**) для форматирования текста"
	"Добавляй 3–5 хештегов(#) в конце, после хэштегов не должно быть текста. Используй призывы к действию."
    )

    @classmethod
    def from_env(cls):
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        folder_id = os.getenv('YANDEX_FOLDER_ID')
        oauth_token = os.getenv('YANDEX_OAUTH_TOKEN')
        iam_token = os.getenv('YANDEX_IAM_TOKEN')  # ← НОВОЕ

        if not all([token, folder_id, oauth_token, iam_token]):
            missing = [k for k, v in {
                'TELEGRAM_BOT_TOKEN': token,
                'YANDEX_FOLDER_ID': folder_id,
                'YANDEX_OAUTH_TOKEN': oauth_token,
                'YANDEX_IAM_TOKEN': iam_token
            }.items() if not v]
            raise ValueError(f"Отсутствуют: {', '.join(missing)}")

        return cls(
            TELEGRAM_BOT_TOKEN=token,
            YANDEX_FOLDER_ID=folder_id,
            YANDEX_OAUTH_TOKEN=oauth_token,
            YANDEX_IAM_TOKEN=iam_token
        )