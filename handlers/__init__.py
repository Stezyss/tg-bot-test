"""
Пакетный модуль, объединяющий обработчики Telegram-бота.

Позволяет удобно импортировать все хендлеры через единый namespace.
Используется в main.py и других частях приложения.
"""
from .handlers_text_create import TextCreateHandler
from .handlers_image import ImageHandler
from .handlers_plan import PlanHandler
from .handlers_text_edit import TextEditHandler
from .handlers_nco import NCOHandler

# Определяем, какие имена будут доступны при импорте
__all__ = [
    "TextCreateHandler",
    "ImageHandler",
    "PlanHandler",
    "TextEditHandler",
    "NCOHandler"
]
