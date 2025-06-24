# app/services/agents/base.py
from abc import ABC, abstractmethod


class AgentBase(ABC):
    def __init__(self, tools: list):
        self.tools = tools

    @abstractmethod
    async def run(self, query: str) -> str:
        """Основной метод агента – принимает запрос и возвращает ответ."""
        pass
