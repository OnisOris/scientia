import re


def normalize_text(text: str) -> str:
    """Нормализует текст для обработки: удаляет лишние пробелы, приводит к нижнему регистру"""
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()
