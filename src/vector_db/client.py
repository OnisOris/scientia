from typing import Any, Dict, List, Optional
from uuid import UUID

import weaviate
from weaviate.classes.config import (
    Configure,
    Property,
    VectorDistances,
)
from weaviate.classes.init import Auth
from weaviate.util import generate_uuid5

from app.settings import settings


class WeaviateClient:
    def __init__(self):
        self.client = weaviate.connect_to_weaviate_cloud(
            cluster_url=settings.WEAVIATE_URL,
            auth_credentials=Auth.api_key(settings.WEAVIATE_API_KEY),
            headers={"X-OpenAI-Api-Key": settings.OPENAI_API_KEY},
        )
        print(f"Connected to Weaviate: {self.client.is_ready()}")

    def ensure_collection(self, class_name: str, properties: List[dict] = []):
        """Создает коллекцию, если она не существует"""
        if not self.client.collections.exists(class_name):
            collection = self.client.collections.create(
                name=class_name,
                properties=[Property(**prop) for prop in properties],
                vectorizer_config=Configure.Vectorizer.none(),
                vector_index_config=Configure.VectorIndex.hnsw(
                    distance_metric=VectorDistances.COSINE
                ),
            )
            print(f"Created collection: {class_name}")
            return collection
        return self.client.collections.get(class_name)

    def insert_object(
        self,
        collection_name: str,
        properties: dict,
        vector: Optional[List[float]] = None,
    ) -> UUID:
        """Вставляет объект в коллекцию и возвращает его UUID"""
        collection = self.client.collections.get(collection_name)
        uuid = generate_uuid5(properties)
        response = collection.data.insert(
            properties=properties, vector=vector, uuid=uuid
        )
        return response

    def semantic_search(
        self,
        collection_name: str,
        query_vector: List[float],
        user_id: str,
        limit: int = 5,
        certainty: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Выполняет семантический поиск по вектору"""
        collection = self.client.collections.get(collection_name)
        response = collection.query.near_vector(
            near_vector=query_vector,
            limit=limit,
            filters=weaviate.classes.query.Filter.by_property("user_id").equal(
                user_id
            ),
            return_metadata=["distance", "certainty"],
        )
        return [
            {
                **obj.properties,
                "distance": obj.metadata.distance,
                "certainty": obj.metadata.certainty,
            }
            for obj in response.objects
        ]

    def hybrid_search(
        self,
        collection_name: str,
        query_vector: List[float],
        user_id: str,
        query_text: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Гибридный поиск по вектору и тексту"""
        collection = self.client.collections.get(collection_name)

        # Базовый фильтр по user_id
        filters = weaviate.classes.query.Filter.by_property("user_id").equal(
            user_id
        )

        # Добавляем текстовый фильтр, если указан
        if query_text:
            filters = filters & weaviate.classes.query.Filter.by_property(
                "content"
            ).like(f"*{query_text}*")

        response = collection.query.near_vector(
            near_vector=query_vector,
            limit=limit,
            filters=filters,
            return_metadata=["distance"],
        )
        return [obj.properties for obj in response.objects]

    def get_collection_schema(self, collection_name: str) -> dict:
        """Возвращает схему коллекции"""
        collection = self.client.collections.get(collection_name)
        return collection.config.get(simple=False)

    def close(self):
        """Закрывает соединение с Weaviate"""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Синглтон для использования во всем приложении
# weaviate_client = WeaviateClient()
