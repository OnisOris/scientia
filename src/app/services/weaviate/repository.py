from app.services.weaviate.client import WeaviateClient
from app.services.weaviate.schemas import DocumentSchema


class WeaviateRepository:
    def __init__(self, client: WeaviateClient):
        self.client = client

    async def ensure_schema(self, class_name: str, properties: list):
        # Создание схемы/класса в Weaviate, если не существует
        # (используем Weaviate v4 API для работы со схемой)
        exists = await self.client.client.schema.exists()
        if not exists:
            await self.client.client.schema.create({"classes": properties})

    async def add_document(self, class_name: str, doc: DocumentSchema):
        # Вставка объекта в класс Weaviate
        await self.client.client.collections.create(
            name=class_name
        )  # создаст схему, если необходимо
        await self.client.client.collections.get(class_name).data.insert_one(
            {
                "id": doc.id,
                "text": doc.text,
                "vector": doc.vector,
                "metadata": doc.metadata,
            }
        )

    async def search_similar(self, class_name: str, vector: list, k: int = 5):
        # Поиск наиболее близких объектов по вектору
        collection = self.client.client.collections.get(class_name)
        response = await collection.query.near_vector(vector=vector, limit=k)
        return response
