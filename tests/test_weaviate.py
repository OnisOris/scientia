import os

from vector_db.client import WeaviateClient

os.environ["GRPC_DNS_RESOLVER"] = "native"
client = WeaviateClient()
client.ensure_collection(class_name="Test3")

props = {
    "content": "Пример текста 2",
    "user_id": "user_123",
    "source": "telegram",
    "created_at": "2025-06-17T12:34:56Z",
}

print(client.insert_object("Testk", props, [3, 45, 533, 2443, 32546, 134]))


client.close()

# class TestWeaviateClient:
#     def test_init(self):
#         assert True
#
#     def test_ensure_collection(self):
#         client.test_ensure_collection(class="Test")
