# app/services/embeddings/openai_provider.py
import openai

from app.services.embeddings.providers import EmbeddingsProvider


class OpenAIEmbeddingsProvider(EmbeddingsProvider):
    def __init__(self, model_name: str = "text-embedding-3-large"):
        self.model = model_name

    async def embed_query(self, text: str):
        # Используем OpenAI API для генерации эмбеддинга запроса
        response = openai.Embedding.create(model=self.model, input=text)
        return response["data"][0]["embedding"]

    async def embed_documents(self, texts: list[str]):
        response = openai.Embedding.create(model=self.model, input=texts)
        return [item["embedding"] for item in response["data"]]
