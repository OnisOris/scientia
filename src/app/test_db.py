import asyncio

from app.db.init_db import create_tables

asyncio.run(create_tables())
print("Tables created successfully.")
