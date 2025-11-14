from typing import Optional
from config import Config

class AIService(Config):
    def init(self, config: Config):
        self.api_key = config.AI_API_KEY

    def generate_text(self, prompt: str) -> str:
        """
        Заглушка для генерации с AI.
        В реальном коде: запрос к OpenAI/Anthropic с prompt.
        """
        return ("[Вариант 1]\nКороткий пост на основе: " + prompt[:1200] + "\n\n"
                "[Вариант 2]\nСредний пост...\n\n"
                "[Вариант 3]\nДлинный пост...")
