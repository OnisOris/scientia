# app/services/agents/tools.py
from langchain_core.tools import tool


@tool
def search_tool(query: str) -> str:
    """Выполнить веб-поиск по запросу."""
    # Здесь может быть реальный вызов API (Google, Bing и т.д.)
    return f"Найдены результаты для: {query}"


@tool
def code_run_tool(code: str) -> str:
    """
    Выполнить Python-код.

    :note: Сделать выполнение в контейнере
    """
    try:
        local_vars = {}
        exec(code, {}, local_vars)
        return str(local_vars.get("result", ""))
    except Exception as e:
        return f"Ошибка выполнения кода: {e}"
