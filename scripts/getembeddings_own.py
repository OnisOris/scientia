# #!/usr/bin/env python3
# import os
# import sys
# from dotenv import load_dotenv
# from weaviate import WeaviateClient
# from weaviate.connect import ConnectionParams, ProtocolParams
# from weaviate.auth import AuthApiKey
#
# # ── 1. Загрузка конфигурации ───────────────────────────────────────────
# load_dotenv()
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# WEAVIATE_URL = os.getenv("WEAVIATE_URL")
# WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
# if not (OPENAI_API_KEY and WEAVIATE_URL and WEAVIATE_API_KEY):
#     print("❌ Укажите OPENAI_API_KEY, WEAVIATE_URL и WEAVIATE_API_KEY в .env")
#     sys.exit(1)
#
# # ── 2. Подключение ─────────────────────────────────────────────────────
# client = WeaviateClient(
#     connection_params=ConnectionParams(
#         http=ProtocolParams(host=WEAVIATE_URL, port=443, secure=True),
#         grpc=ProtocolParams(host=WEAVIATE_URL, port=50051, secure=True),
#     ),
#     auth_client_secret=AuthApiKey(WEAVIATE_API_KEY),
#     additional_headers={"X-OpenAI-Api-Key": OPENAI_API_KEY},
#     skip_init_checks=True,
# )
# client.connect()
# if not client.is_ready():
#     print("❌ Weaviate недоступен")
#     sys.exit(1)
# print("✅ Подключено к Weaviate")
#
# # ── 3. Запрос через GraphQL ────────────────────────────────────────────
# class_name = "Sentence"
# fields = ["text"]  # какие поля хотим получить
# limit = 100  # безопасный верхний предел, у вас всего 3
#
# resp = (
#     client.query.get(class_name, fields)
#     .with_additional({"id": True})  # чтобы получить UUID в разделе _additional
#     .with_limit(limit)
#     .do()
# )
#
# # ── 4. Разбор и вывод ──────────────────────────────────────────────────
# items = resp.get("data", {}).get("Get", {}).get(class_name, [])
# if not items:
#     print(f"⚠️ В коллекции «{class_name}» объектов не найдено.")
# else:
#     print(f"\n📦 Объекты из коллекции «{class_name}» (limit={limit}):\n")
#     for obj in items:
#         uuid = obj["_additional"]["id"]
#         text = obj.get("text", "")
#         print(f"• UUID: {uuid}\n  Text: {text}\n")
#
# client.close()
#!/usr/bin/env python3
import os, sys
from dotenv import load_dotenv
from weaviate import WeaviateClient
from weaviate.connect import ConnectionParams, ProtocolParams
from weaviate.auth import AuthApiKey

# 1) Конфиг из .env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
if not (OPENAI_API_KEY and WEAVIATE_URL and WEAVIATE_API_KEY):
    print("❌ Укажите OPENAI_API_KEY, WEAVIATE_URL и WEAVIATE_API_KEY в .env")
    sys.exit(1)

# 2) Подключаемся
client = WeaviateClient(
    connection_params=ConnectionParams(
        http=ProtocolParams(host=WEAVIATE_URL, port=443, secure=True),
        grpc=ProtocolParams(host=WEAVIATE_URL, port=50051, secure=True),
    ),
    auth_client_secret=AuthApiKey(WEAVIATE_API_KEY),
    additional_headers={"X-OpenAI-Api-Key": OPENAI_API_KEY},
    skip_init_checks=True,
)
client.connect()
if not client.is_ready():
    print("❌ Weaviate недоступен")
    sys.exit(1)
print("✅ Подключено к Weaviate")

# 3) Ставим GraphQL-запрос
GRAPHQL = """
{
  Get {
    Sentence(limit: 100) {
      text
      _additional {
        id
      }
    }
  }
}
"""

# 4) Дёргаем raw-endpoint
res = client.graphql.raw(
    GRAPHQL
)  # raw() даёт полный контроль над запросом :contentReference[oaicite:0]{index=0}

# 5) Парсим и выводим
items = res.get("data", {}).get("Get", {}).get("Sentence", [])

if not items:
    print("⚠️ В коллекции 'Sentence' нет объектов.")
else:
    print(f"\n📦 Найдено объектов: {len(items)}\n")
    for obj in items:
        uuid = obj["_additional"]["id"]
        text = obj.get("text", "")
        print(f"• UUID: {uuid}\n  Text: {text}\n")

client.close()
sys.exit(0)
