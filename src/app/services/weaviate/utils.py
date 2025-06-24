import uuid


def generate_uuid5(input_str: str) -> str:
    # Создаем детерминированный UUID на основе строки
    return str(uuid.uuid5(uuid.NAMESPACE_URL, input_str))
