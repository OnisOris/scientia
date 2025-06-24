import asyncio
import multiprocessing

import uvicorn

from app.bot.main import start_bot
from app.db.init_db import create_tables
from app.services.embeddings.openai_provider import OpenAIEmbeddingsProvider
from app.services.weaviate.client import WeaviateClient


async def init_models():
    await create_tables()


def run_api():
    uvicorn.run("app.api.main:app", host="0.0.0.0", port=8000, reload=False)


def run_bot():
    start_bot()


async def get_services():
    weaviate_client = WeaviateClient()
    await weaviate_client.connect()
    embeddings = OpenAIEmbeddingsProvider()
    yield {"weaviate": weaviate_client, "embeddings": embeddings}


def main():
    asyncio.run(init_models())
    multiprocessing.set_start_method("spawn")

    api_process = multiprocessing.Process(target=run_api)
    bot_process = multiprocessing.Process(target=run_bot)

    api_process.start()
    bot_process.start()

    api_process.join()
    bot_process.join()


if __name__ == "__main__":
    main()
