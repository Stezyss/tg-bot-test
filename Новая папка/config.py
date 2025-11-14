import os
from dataclasses import dataclass

@dataclass
class Config:
    TELEGRAM_BOT_TOKEN: str
    AI_API_KEY: str = None  # Опционально, так как в коде это заглушка

    @classmethod
    def from_env(cls):
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            raise ValueError('TELEGRAM_BOT_TOKEN не установлен')
        
        ai_key = os.getenv('AI_API_KEY')
        
        return cls(
            TELEGRAM_BOT_TOKEN=token,
            AI_API_KEY=ai_key
        )