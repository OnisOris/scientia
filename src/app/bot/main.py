import logging
import os
import uuid

import httpx

# import spacy
from aiogram import BaseMiddleware, Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    Message,
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BotCommand,
)

# from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy.orm import Mapped

from app.db import Session
from app.models.users import User
from app.repositories.user_repository import UserRepository

# from app.repositories.domain_repository import DomainRepository
from app.repositories.registration_request_repository import (
    RegistrationRequestRepository,
)

# from app.repositories.concept_repository import ConceptRepository
from app.repositories.profile_repository import ProfileRepository

# from app.services.email import send_confirmation_email
# from app.services.prompt_generator import PromptService
# from app.services.text_processor import TextProcessorService
from app.models.registration_requests import RegistrationRequest
from app.models.user_profile import UserProfile

from app.settings import settings

logger = logging.getLogger(__name__)

os.environ["GRPC_DNS_RESOLVER"] = settings.GRPC_DNS_RESOLVER
ADMIN_IDS = settings.ADMIN_IDS

session = AiohttpSession()
bot = Bot(
    token=settings.TG_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML"),
    session=session,
)
dp = Dispatcher()


class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data):
        if isinstance(event, Message) and event.text:
            if event.text.startswith("/register") or event.text.startswith(
                "/admin"
            ):
                return await handler(event, data)

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


@dp.message(Command("sync"))
async def cmd_sync(message: Message):
    await message.answer("Начинаю синхронизацию…")
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{settings.API_URL}/sync")
    await message.answer(resp.json().get("detail", "Готово"))


@dp.message(Command("quiz"))
async def cmd_quiz(message: Message):
    await message.answer("cmd_quiz() пока не реализована")


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in settings.ADMIN_IDS:
        return

    text = (
        "👮 Админ панель:\n\n"
        "Чтобы выдать премиум доступ:\n"
        "`/grant_premium <user_id>`\n\n"
        "Чтобы отозвать премиум доступ:\n"
        "`/revoke_premium <user_id>`\n\n"
        "Где `user_id`: внутренний ID пользователя в системе, UUID"
    )

    await message.answer(text, parse_mode="MarkdownV2")


@dp.message(Command("grant_premium"))
async def cmd_grant_premium(message: Message):
    if message.from_user.id not in settings.ADMIN_IDS:
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
                f"{settings.API_URL}/admin/grant-premium",
                json={"user_id": str(user_id)},
            )
            resp.raise_for_status()
            await message.answer(resp.json().get("detail"))
        except httpx.HTTPStatusError as e:
            await message.answer(f"Ошибка: {e.response.text}")


@dp.message(Command("register"))
async def cmd_register(message: Message):
    """
    Процедура регистрации
    """
    if message.from_user.id in settings.ADMIN_IDS:
        async with Session() as session:
            user_repo = UserRepository(session)
            existing_user = await user_repo.get_by_telegram_id(
                message.from_user.id
            )
            if existing_user:
                await message.answer(
                    "✅ Вы уже зарегистрированы как администратор!"
                )
                return
            user = await user_repo.add(
                User(
                    telegram_id=message.from_user.id,
                    hashed_password="default",
                    confirmed=True,
                    is_premium=True,
                )
            )
            profile_repo = ProfileRepository(session)
            await profile_repo.add(
                UserProfile(
                    user_id=user.id,
                    username=message.from_user.username
                    or f"admin_{message.from_user.id}",
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name,
                )
            )
            await session.commit()
        await message.answer(
            "🎉 Вы зарегистрированы как администратор! Теперь вы можете пользоваться ботом."
        )
        return
    async with Session() as session:
        request_repo = RegistrationRequestRepository(session)
        existing_request = await request_repo.get_by_telegram_id(
            message.from_user.id
        )
        if existing_request:
            status_msg = {
                "pending": "⏳ Ваша заявка уже отправлена и ожидает подтверждения",
                "approved": "✅ Ваша заявка уже одобрена",
                "rejected": "❌ Ваша заявка была отклонена",
            }
            await message.answer(status_msg[existing_request.status])
            return
        new_request = RegistrationRequest(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        await request_repo.add(new_request)
        sent_to_admins = False
        for admin_id in settings.ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"📨 Новая заявка на регистрацию:\n"
                    f"👤 Пользователь: {message.from_user.full_name}\n"
                    f"🆔 ID: {message.from_user.id}\n"
                    f"👤 Username: @{message.from_user.username}",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="✅ Одобрить",
                                    callback_data=f"approve_{message.from_user.id}",
                                ),
                                InlineKeyboardButton(
                                    text="❌ Отклонить",
                                    callback_data=f"reject_{message.from_user.id}",
                                ),
                            ]
                        ]
                    ),
                )
                sent_to_admins = True
            except Exception as e:
                logger.error(f"Failed to send to admin {admin_id}: {str(e)}")

        if sent_to_admins:
            await message.answer(
                "✅ Ваша заявка на регистрацию отправлена администраторам. "
                "Вы получите уведомление, когда она будет рассмотрена."
            )
        else:
            logger.critical(
                f"Failed to send registration request to any admin!"
            )
            await message.answer(
                "⚠️ Не удалось отправить заявку администраторам. "
                "Пожалуйста, сообщите об этом разработчику."
            )


@dp.callback_query(F.data.startswith("approve_"))
async def approve_registration(callback: CallbackQuery):
    """
    Подтверждение регистрации
    """
    telegram_id = int(callback.data.split("_")[1])
    async with Session() as session:
        user_repo = UserRepository(session)
        existing_user = await user_repo.get_by_telegram_id(telegram_id)
        if existing_user:
            await callback.answer("⚠️ Пользователь уже зарегистрирован")
            await callback.message.edit_text(
                f"⚠️ Пользователь с ID {telegram_id} уже зарегистрирован",
                reply_markup=None,
            )
            return
        request_repo = RegistrationRequestRepository(session)
        request = await request_repo.get_by_telegram_id(telegram_id)
        if not request:
            await callback.answer("❌ Заявка не найдена")
            return
        request.status = "approved"
        user = await user_repo.add(
            User(
                telegram_id=telegram_id,
                hashed_password="default",
                confirmed=True,
            )
        )
        profile_repo = ProfileRepository(session)
        await profile_repo.add(
            UserProfile(
                user_id=user.id,
                username=request.username or f"user_{telegram_id}",
                first_name=request.first_name,
                last_name=request.last_name,
            )
        )
        await session.commit()
        try:
            await bot.send_message(
                telegram_id,
                "🎉 Ваша регистрация подтверждена! Теперь вы можете пользоваться ботом.",
            )
        except Exception as e:
            logger.error(
                f"Failed to send message to user {telegram_id}: {str(e)}"
            )
        await callback.answer("✅ Пользователь зарегистрирован")
        await callback.message.edit_text(
            f"✅ Пользователь @{request.username} зарегистрирован",
            reply_markup=None,
        )


@dp.callback_query(F.data.startswith("reject_"))
async def reject_registration(callback: CallbackQuery):
    """
    Отклонение регистрации
    """
    telegram_id = int(callback.data.split("_")[1])
    async with Session() as session:
        request_repo = RegistrationRequestRepository(session)
        request = await request_repo.get_by_telegram_id(telegram_id)
        request.status = "rejected"
        await session.commit()
        try:
            await bot.send_message(
                telegram_id,
                "❌ Ваша заявка на регистрацию отклонена администратором.",
            )
        except Exception:
            pass
        await callback.answer("❌ Заявка отклонена")
        await callback.message.edit_text(
            f"❌ Заявка пользователя @{request.username} отклонена",
            reply_markup=None,
        )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "📚 Помощь по командам:\n\n"
        "• /start - Начало работы с ботом\n"
        "• /register - Регистрация в системе\n"
        "• /add [текст] - Добавить текст для анализа\n"
        "• /quiz - Получить карточку для повторения\n"
        "• /deepseek - Анализ ваших знаний\n"
        "• /admin - Админ-панель (для администраторов)\n\n"
        "Вы также можете просто отправлять мне тексты - я автоматически извлеку из них ключевые концепты!"
    )
    await message.answer(text)


@dp.message(Command("start"))
async def cmd_start(message: Message):
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(
            text="Добавить текст", callback_data="add_text"
        ),
        types.InlineKeyboardButton(
            text="Анализ знаний", callback_data="analysis"
        ),
    )
    builder.adjust(1)

    await message.answer(
        "👋 Добро пожаловать в Scientia! Выберите действие:",
        reply_markup=builder.as_markup(),
    )


@dp.message(F.text.contains("::"))
async def process_concept_definition(message: Message):
    try:
        parts = message.text.split("::", 1)
        concept_name = parts[0].strip()
        definition = parts[1].strip()

        await message.answer(
            f"concept_name - {concept_name} \ndefinition - {definition}"
        )
    except Exception as e:
        logger.error(f"Error updating concept: {str(e)}")
        await message.answer("⚠️ Произошла ошибка")


@dp.callback_query(F.data == "add_text")
async def process_add_text(callback: CallbackQuery):
    await callback.message.answer(
        "Введите текст для добавления или используйте команду /add [текст]"
    )
    await callback.answer()


@dp.callback_query(F.data == "quiz")
async def process_quiz(callback: CallbackQuery):
    await cmd_quiz(callback.message)
    await callback.answer()


@dp.message(F.text == "Добавить текст")
async def handle_add_text(message: Message):
    await message.answer(
        "Введите текст для добавления или используйте команду /add [текст]"
    )


@dp.message(F.text == "Повторить карточки")
async def handle_quiz(message: Message):
    await message.answer("Пока не реализовано")


def start_bot():
    import asyncio

    async def set_bot_commands():
        commands = [
            types.BotCommand(command="/start", description="Начать работу"),
            types.BotCommand(
                command="/help", description="Помощь по командам"
            ),
            types.BotCommand(command="/add", description="Добавить текст"),
            types.BotCommand(
                command="/quiz", description="Повторить карточки"
            ),
            types.BotCommand(command="/map", description="Карта знаний"),
            types.BotCommand(
                command="/stats", description="Статистика знаний"
            ),
            types.BotCommand(command="/deepseek", description="Анализ знаний"),
            types.BotCommand(command="/register", description="Регистрация"),
        ]

        admin_commands = [
            types.BotCommand(command="/admin", description="Админ-панель"),
            types.BotCommand(
                command="/sync", description="Синхронизация данных"
            ),
        ]
        await bot.set_my_commands(commands)
        for admin_id in settings.ADMIN_IDS:
            try:
                await bot.set_my_commands(
                    commands + admin_commands,
                    scope=types.BotCommandScopeChat(chat_id=admin_id),
                )
            except Exception as e:
                logger.error(
                    f"Failed to set commands for admin {admin_id}: {str(e)}"
                )

    @dp.message(Command("help"))
    async def cmd_help(message: Message):
        text = (
            "📚 <b>Помощь по командам</b>:\n\n"
            "• /start - Начало работы с ботом\n"
            "• /help - Показать это сообщение\n"
            "• /add [текст] - Добавить текст для анализа\n"
            "• /quiz - Получить карточку для повторения\n"
            "• /map - Показать вашу карту знаний\n"
            "• /stats - Статистика ваших знаний\n"
            "• /deepseek - Анализ ваших знаний AI\n"
            "• /register - Регистрация в системе\n\n"
            "<b>Для администраторов</b>:\n"
            "• /admin - Админ-панель\n"
            "• /sync - Синхронизация данных\n\n"
            "💡 Вы также можете просто отправлять мне тексты - "
            "я автоматически извлеку из них ключевые концепты!\n"
            "💡 Чтобы добавить определение, используйте формат: <code>Концепт :: Определение</code>"
        )
        await message.answer(text, parse_mode="HTML")

    async def main():
        await set_bot_commands()
        await dp.start_polling(bot)

    asyncio.run(main())
