import os

from vector_db.client import WeaviateClient

os.environ["GRPC_DNS_RESOLVER"] = "native"
client = WeaviateClient()
client.ensure_collection(class_name="Test3")

client.insert_object("Test", "csvdbevsefvw")

client.close()

# class TestWeaviateClient:
#     def test_init(self):
#         assert True
#
#     def test_ensure_collection(self):
#         client.test_ensure_collection(class="Test")
