import weaviate
from weaviate.classes.init import AdditionalConfig, Auth, Timeout
from weaviate.connect import ConnectionParams

from app.settings import settings


class WeaviateClient:
    def __init__(self):
        # Создаем асинхронный клиент Weaviate v4
        self.client = weaviate.WeaviateAsyncClient(
            connection_params=ConnectionParams.from_params(
                http_host=settings.WEAVIATE_URL,  # URL (без порта) Weaviate
                http_port=8080,
                http_secure=False,
                grpc_host=settings.WEAVIATE_URL,
                grpc_port=50051,
                grpc_secure=False,
            ),
            auth_client_secret=Auth.api_key(settings.WEAVIATE_API_KEY),
            additional_headers={"X-OpenAI-Api-Key": settings.OPENAI_API_KEY},
            additional_config=AdditionalConfig(
                timeout=Timeout(init=30, query=60, insert=120)
            ),
        )

    async def connect(self):
        # Подключаемся к Weaviate
        await self.client.connect()

    async def is_ready(self) -> bool:
        return await self.client.is_ready()
