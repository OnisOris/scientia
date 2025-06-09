import os
import numpy as np
import requests
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
import weaviate
from weaviate.auth import AuthApiKey
from weaviate.classes.config import Configure, DataType, Property

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


# Получение эмбеддингов через OpenAI API
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


# Подключение к Weaviate Cloud
client = weaviate.connect_to_weaviate_cloud(
    cluster_url=WEAVIATE_URL, auth_credentials=AuthApiKey(WEAVIATE_API_KEY)
)

# Проверка доступности
if not client.is_ready():
    raise ConnectionError("Weaviate недоступен")

# Имя коллекции
class_name = "Sentence"

# Создание коллекции, если не существует
if not client.collections.exists(class_name):
    client.collections.create(
        name=class_name,
        vectorizer_config=Configure.Vectorizer.none(),  # эмбеддинги вручную
        properties=[
            Property(name="text", data_type=DataType.TEXT),
        ],
    )

collection = client.collections.get(class_name)

# Получаем эмбеддинги
embeddings = get_openai_embeddings(sentences)

# Сохраняем в Weaviate
for sentence, vector in zip(sentences, embeddings):
    collection.data.insert(
        properties={"text": sentence},
        vector=vector.tolist(),
    )

print("✅ Успешно загружено в Weaviate!")

# Косинусная схожесть между первым и вторым предложением
similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
print(f"Схожесть между первым и вторым: {similarity:.4f}")

# Закрываем соединение
client.close()
