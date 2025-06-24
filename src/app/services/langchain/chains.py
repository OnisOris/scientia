# app/services/langchain/chains.py
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI
from langchain.vectorstores import Weaviate as WeaviateStore
from app.services.weaviate.client import WeaviateClient


class QAChainFactory:
    @staticmethod
    async def create_retrieval_chain(
        weaviate_client: WeaviateClient, llm_model: str = "gpt-4"
    ):
        # Убедимся, что клиент подключен
        await weaviate_client.connect()
        # Создаем LangChain VectorStore для Weaviate
        vector_store = WeaviateStore(
            client=weaviate_client.client,
            index_name="Document",
            text_key="text",
        )
        llm = ChatOpenAI(model=llm_model)
        chain = RetrievalQA.from_chain_type(
            llm=llm, retriever=vector_store.as_retriever()
        )
        return chain
