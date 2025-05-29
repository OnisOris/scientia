import os
import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv
import uuid
from app.services.email import send_confirmation_email
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update
from fastapi import HTTPException
from app.db import Session
from app.repositories.user_repository import UserRepository
from app.services.prompt_generator import PromptService


os.environ["GRPC_DNS_RESOLVER"] = "native"

load_dotenv()
API_URL = os.getenv("API_URL")
TOKEN = os.getenv("TG_BOT_TOKEN")

session = AiohttpSession()
bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode="HTML"),
    session=session,
)
dp = Dispatcher()


class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data):
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
        else:
            return await handler(event, data)

        if not user_id:
            await event.answer("❌ Не удалось определить пользователя")
            return

        async with Session() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_telegram_id(user_id)

            if not user or not user.confirmed:
                if isinstance(event, (Message, CallbackQuery)):
                    await event.answer(
                        "❌ Для использования бота необходимо завершить регистрацию"
                    )
                return

            data["user"] = user
            return await handler(event, data)


dp.update.middleware(AuthMiddleware())


@dp.message(Command("sync"))
async def cmd_sync(message: Message):
    await message.answer("Начинаю синхронизацию…")
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{API_URL}/sync")
    await message.answer(resp.json().get("detail", "Готово"))


@dp.message(Command("quiz"))
async def cmd_quiz(message: Message):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API_URL}/next_card?user={message.from_user.id}"
        )
    if resp.status_code != 200:
        await message.answer("Нет доступных карточек.")
        return
    card = resp.json()
    await message.answer(f"Слово: <b>{card['word']}</b>")


@dp.message(Command("deepseek"))
async def cmd_deepseek(message: Message):
    prompt_service = PromptService()
    analysis = await prompt_service.get_ai_analysis(
        "d7c55690-e047-43a1-ac0c-b09df76d2733"
    )
    print(analysis)
    message.answer(analysis)


@dp.message(Command("add"))
async def cmd_add(message: Message):
    content = message.text.partition(" ")[2]
    if not content:
        await message.answer("Укажите текст после /add.")
        return

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_URL}/add",
            json={
                "telegram_id": message.from_user.id,
                "text": content,
            },
        )

    if resp.headers.get("content-type") == "application/json":
        data = resp.json()
        await message.answer(data.get("detail", "Готово"))
    else:
        await message.answer(f"Ошибка: {resp.status_code}")


ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    await message.answer(
        "Админ-панель:\n/grant_premium <user_id>\n/revoke_premium <user_id>"
    )


@dp.message(Command("grant_premium"))
async def cmd_grant_premium(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        args = message.text.split()
        if len(args) < 2:
            await message.answer("Укажите ID пользователя")
            return

        user_id = uuid.UUID(args[1])
    except (ValueError, IndexError):
        await message.answer("Неверный формат ID пользователя")
        return

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{API_URL}/admin/grant-premium",
                json={"user_id": str(user_id)},
            )
            resp.raise_for_status()
            await message.answer(resp.json().get("detail"))
        except httpx.HTTPStatusError as e:
            await message.answer(f"Ошибка: {e.response.text}")


@dp.message(Command("register"))
async def cmd_register(message: Message):
    await message.answer("Введите ваш email для регистрации:")


@dp.message(F.text.contains("@"))
async def process_email(message: Message):
    email = message.text
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{API_URL}/register",
                json={"telegram_id": message.from_user.id, "email": email},
            )
            resp.raise_for_status()
            await message.answer("Проверьте вашу почту для подтверждения!")
        except httpx.HTTPStatusError as e:
            await message.answer(f"Ошибка регистрации: {e.response.text}")


def start_bot():
    import asyncio

    asyncio.run(dp.start_polling(bot))


if __name__ == "__main__":
    start_bot()
