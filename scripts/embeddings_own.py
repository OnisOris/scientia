import os
import ssl
import sys

import certifi
import numpy as np
import requests
import weaviate
from dotenv import load_dotenv
from weaviate import WeaviateClient
from weaviate.auth import AuthApiKey
from weaviate.classes.config import Configure, DataType, Property
from weaviate.classes.query import Filter
from weaviate.connect import ConnectionParams, ProtocolParams
from weaviate.exceptions import WeaviateConnectionError, WeaviateQueryError

# ── Конфиг из .env ───────────────────────────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
if not all([OPENAI_API_KEY, WEAVIATE_URL, WEAVIATE_API_KEY]):
    raise EnvironmentError("Отсутствуют необходимые ключи в .env")

# ── Данные и эмбеддинги ───────────────────────────────────────────────────────────
sentences = [
    "Привет, как твои дела?",
    "Погода сегодня замечательная!",
    "OpenAI предоставляет мощные языковые модели.",
]


def get_embeddings(texts):
    """Получение эмбеддингов через OpenAI API"""
    try:
        response = requests.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "text-embedding-3-small",
                "input": texts,
            },
            timeout=30,
        )
        response.raise_for_status()
        return [
            np.array(item["embedding"]) for item in response.json()["data"]
        ]
    except Exception as e:
        print(f"Ошибка получения эмбеддингов: {e}")
        raise


def fetch_all_objects(collection, batch_size=100):
    """Получение всех объектов с пагинацией"""
    print("\nИзвлекаем все объекты из коллекции...")
    all_objects = []
    cursor = None

    try:
        while True:
            response = collection.query.fetch_objects(
                limit=batch_size,
                after=cursor,
                include_vector=True,
                return_properties=["text"],
            )

            if not response.objects:
                break

            all_objects.extend(response.objects)
            print(f"Получено объектов: {len(all_objects)}")

            if len(response.objects) < batch_size:
                break

            cursor = response.objects[-1].uuid

    except WeaviateQueryError as e:
        print(f"Ошибка запроса: {e.message}")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")

    return all_objects


def semantic_search(collection, query, limit=3):
    """Семантический поиск по вектору"""
    print(f"\n[Семантический поиск] Запрос: '{query}'")

    try:
        # Получаем эмбеддинг для запроса
        query_vector = get_embeddings([query])[0].tolist()

        response = collection.query.near_vector(
            near_vector=query_vector,
            limit=limit,
            return_properties=["text"],
            return_metadata=["distance", "certainty"],
        )

        print("Результаты поиска:")
        for i, obj in enumerate(response.objects, 1):
            print(f"{i}. {obj.properties['text']}")
            print(f"   Расстояние: {obj.metadata.distance:.4f}")
            print(f"   Уверенность: {obj.metadata.certainty:.4f}")

        return response.objects

    except Exception as e:
        print(f"Ошибка семантического поиска: {e}")
        return []


def keyword_search(collection, keyword, limit=3):
    """Поиск по ключевым словам"""
    print(f"\n[Поиск по ключевому слову] '{keyword}'")

    try:
        response = collection.query.fetch_objects(
            filters=Filter.by_property("text").like(f"*{keyword}*"),
            return_properties=["text"],
            limit=limit,
        )

        print("Результаты поиска:")
        for i, obj in enumerate(response.objects, 1):
            print(f"{i}. {obj.properties['text']}")

        return response.objects

    except Exception as e:
        print(f"Ошибка поиска по ключевым словам: {e}")
        return []


# ── Основной код ────────────────────────────────────────────────────────────────
def main():
    client = None
    try:
        # Создаем SSL контекст с доверенными сертификатами
        ssl_context = ssl.create_default_context(cafile=certifi.where())

        # Конфигурация подключения (HTTP и gRPC)
        client = WeaviateClient(
            connection_params=ConnectionParams(
                http=ProtocolParams(
                    host=WEAVIATE_URL,
                    port=443,
                    secure=True,
                    ssl_context=ssl_context,
                ),
                grpc=ProtocolParams(
                    host=WEAVIATE_URL,
                    port=50051,
                    secure=True,
                    ssl_context=ssl_context,
                ),
                # Предпочитаем gRPC соединение
                preferred_connection="grpc",
            ),
            auth_client_secret=AuthApiKey(WEAVIATE_API_KEY),
            additional_headers={"X-OpenAI-Api-Key": OPENAI_API_KEY},
            skip_init_checks=False,  # Для лучшей диагностики
        )

        # Подключаемся с таймаутом
        client.connect(timeout=10)

        if not client.is_ready():
            raise WeaviateConnectionError("Weaviate не отвечает")

        print("✅ Успешное подключение к Weaviate!")

        # Работа с коллекцией
        collection_name = "Sentence"

        # Создаем коллекцию если не существует
        if not client.collections.exists(collection_name):
            print(f"Создаем коллекцию '{collection_name}'...")
            client.collections.create(
                name=collection_name,
                vectorizer_config=Configure.Vectorizer.none(),
                properties=[Property(name="text", data_type=DataType.TEXT)],
            )

        collection = client.collections.get(collection_name)

        # Проверяем количество объектов
        count = collection.aggregate.over_all(total_count=True).total_count
        print(f"Объектов в коллекции: {count}")

        # Добавляем данные если коллекция пустая
        if count == 0:
            print("Добавляем тестовые данные...")
            embeddings = get_embeddings(sentences)

            for i, (sentence, vector) in enumerate(
                zip(sentences, embeddings), 1
            ):
                collection.data.insert(
                    properties={"text": sentence},
                    vector=vector.tolist(),
                    uuid=weaviate.util.generate_uuid5(sentence),
                )
                print(f"Добавлено: {i}/{len(sentences)}")

            print("✅ Данные успешно добавлены!")

        # Примеры запросов
        all_objects = fetch_all_objects(collection)
        semantic_search(collection, "Обсуждение искусственного интеллекта")
        keyword_search(collection, "погода")

    except WeaviateConnectionError as e:
        print(f"Ошибка подключения: {e}")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()
    finally:
        if client:
            client.close()
            print("\n✅ Соединение с Weaviate закрыто")


if __name__ == "__main__":
    main()
