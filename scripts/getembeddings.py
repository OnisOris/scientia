import os
import numpy as np
import requests
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
import weaviate
from weaviate.auth import AuthApiKey
from weaviate.classes.config import Configure, DataType, Property, DistanceType
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA

# Загрузка переменных окружения
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")

# Проверка переменных
if not OPENAI_API_KEY or not WEAVIATE_URL or not WEAVIATE_API_KEY:
    raise EnvironmentError("Отсутствуют ключи в .env")

# Пример предложений
sentences = [
    "Привет, как твои дела?",
    "Погода сегодня замечательная!",
    "OpenAI предоставляет мощные языковые модели.",
]


# Функция для получения эмбеддингов
def get_openai_embeddings(texts):
    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "text-embedding-3-small",
        "input": texts,
        "encoding_format": "float",
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        data = response.json()["data"]
        return [np.array(d["embedding"]) for d in data]
    else:
        raise RuntimeError(
            f"Ошибка от OpenAI: {response.status_code} — {response.text}"
        )


# Подключение к Weaviate
client = weaviate.connect_to_weaviate_cloud(
    cluster_url=WEAVIATE_URL, auth_credentials=AuthApiKey(WEAVIATE_API_KEY)
)

# Управление коллекцией
class_name = "Sentence"

# Удаление существующей коллекции (если есть)
if client.collections.exists(class_name):
    client.collections.delete(class_name)

# Создание новой коллекции
collection = client.collections.create(
    name=class_name,
    vectorizer_config=Configure.Vectorizer.none(),
    properties=[
        Property(name="text", data_type=DataType.TEXT),
    ],
    vector_index_config=Configure.VectorIndex.hnsw(
        distance_metric=DistanceType.COSINE
    ),
)

# Получаем эмбеддинги для предложений
embeddings = get_openai_embeddings(sentences)

# Вставляем данные
for sentence, vector in zip(sentences, embeddings):
    collection.data.insert(
        properties={"text": sentence},
        vector=vector.tolist(),
    )

print("✅ Данные успешно загружены в Weaviate")

# Теперь получаем коллекцию для работы
collection = client.collections.get(class_name)


# Пример 1: Поиск похожих предложений
def semantic_search(query, top_k=3):
    print(f"\n🔍 Поиск похожих на: '{query}'")

    # Получаем эмбеддинг запроса
    query_embedding = get_openai_embeddings([query])[0].tolist()

    # Ищем в Weaviate
    results = collection.query.near_vector(
        near_vector=query_embedding, limit=top_k, return_metadata=["distance"]
    )

    # Выводим результаты
    for i, obj in enumerate(results.objects):
        # Преобразуем расстояние в схожесть
        similarity = 1 - obj.metadata.distance
        print(f"\n#{i + 1}: {obj.properties['text']}")
        print(f"   Расстояние: {obj.metadata.distance:.4f}")
        print(f"   Схожесть: {similarity:.4f}")


# Пример 2: Визуализация эмбеддингов
def visualize_embeddings():
    print("\n📊 Визуализация эмбеддингов")

    # Получаем все объекты
    all_objects = list(collection.iterator(include_vector=True))

    texts = []
    vectors = []

    for obj in all_objects:
        texts.append(obj.properties["text"])
        vectors.append(obj.vector["default"])

    vectors = np.array(vectors)

    # Снижаем размерность для визуализации
    pca = PCA(n_components=2)
    reduced_vectors = pca.fit_transform(vectors)

    # Визуализируем
    plt.figure(figsize=(10, 8))
    for i, (x, y) in enumerate(reduced_vectors):
        plt.scatter(x, y, marker="o")
        plt.text(x + 0.01, y + 0.01, f"{i + 1}", fontsize=9)

    plt.title("Визуализация эмбеддингов предложений")
    plt.xlabel("PCA Component 1")
    plt.ylabel("PCA Component 2")

    # Добавляем легенду
    for i, text in enumerate(texts):
        print(f"{i + 1}: {text}")

    plt.grid()
    plt.show()


# Пример 3: Ручной расчет схожести
def manual_similarity_calculation():
    print("\n🧮 Ручной расчет схожести")

    # Получаем все объекты
    all_objects = list(collection.iterator(include_vector=True))

    if len(all_objects) < 2:
        print("Нужно как минимум 2 объекта для сравнения")
        return

    # Берем первый и последний объекты
    obj1 = all_objects[0]
    obj2 = all_objects[-1]

    vec1 = np.array(obj1.vector["default"])
    vec2 = np.array(obj2.vector["default"])

    # Рассчитываем косинусную схожесть
    similarity = cosine_similarity([vec1], [vec2])[0][0]

    print(f"Объект 1: '{obj1.properties['text']}'")
    print(f"Объект 2: '{obj2.properties['text']}'")
    print(f"Косинусная схожесть: {similarity:.4f}")

    # Рассчитываем евклидово расстояние
    euclidean = np.linalg.norm(vec1 - vec2)
    print(f"Евклидово расстояние: {euclidean:.4f}")


# Пример 4: Гибридный поиск
def hybrid_search(query, keyword=None):
    print(f"\n🔍 Гибридный поиск: '{query}'")

    # Получаем эмбеддинг запроса
    query_embedding = get_openai_embeddings([query])[0].tolist()

    # Строим фильтр
    filter = None
    if keyword:
        filter = weaviate.classes.query.Filter.by_property("text").like(
            f"*{keyword}*"
        )

    # Выполняем запрос
    results = collection.query.near_vector(
        near_vector=query_embedding,
        limit=3,
        filters=filter,
        return_metadata=["distance"],
    )

    # Выводим результаты
    for i, obj in enumerate(results.objects):
        similarity = 1 - obj.metadata.distance
        print(f"\n#{i + 1}: {obj.properties['text']}")
        print(f"   Расстояние: {obj.metadata.distance:.4f}")
        print(f"   Схожесть: {similarity:.4f}")


# Выполняем примеры
if __name__ == "__main__":
    try:
        # Примеры поиска
        semantic_search("Как настроение?")
        semantic_search("Искусственный интеллект")
        semantic_search("OpenAI предоставляет мощные языковые модели.")

        # Ручной расчет
        manual_similarity_calculation()

        # Гибридный поиск
        hybrid_search("Программное обеспечение", keyword="OpenAI")

        # Визуализация
        visualize_embeddings()
    finally:
        # Всегда закрываем соединение
        client.close()
