# app/services/agents/search_agent.py
from app.services.agents.base import AgentBase


class SearchAgent(AgentBase):
    async def run(self, query: str) -> str:
        # Тупо демонстрация: здесь мог бы быть запрос к поисковому API
        return f"Результаты поиска для: {query}"
