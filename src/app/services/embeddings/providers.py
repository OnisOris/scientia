# app/services/embeddings/providers.py
from abc import ABC, abstractmethod
from typing import List


class EmbeddingsProvider(ABC):
    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """Получить embedding для одного запроса."""
        pass

    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Получить embeddings для списка документов."""
        pass
