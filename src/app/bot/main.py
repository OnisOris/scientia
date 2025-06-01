import logging
import os
import uuid

import httpx
import spacy
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
from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy.orm import Mapped

from app.db import Session
from app.models.users import User
from app.repositories.user_repository import UserRepository
from app.repositories.domain_repository import DomainRepository
from app.repositories.registration_request_repository import (
    RegistrationRequestRepository,
)
from app.repositories.concept_repository import ConceptRepository
from app.repositories.profile_repository import ProfileRepository
from app.services.email import send_confirmation_email
from app.services.prompt_generator import PromptService
from app.services.text_processor import TextProcessorService
from app.models.registration_requests import RegistrationRequest
from app.models.user_profile import UserProfile
from datetime import datetime
from app.services.nlp_loader import load_nlp_model

nlp = load_nlp_model()

logger = logging.getLogger(__name__)


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


dp.message.middleware(AuthMiddleware())


@dp.message(Command("sync"))
async def cmd_sync(message: Message):
    await message.answer("Начинаю синхронизацию…")
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{API_URL}/sync")
    await message.answer(resp.json().get("detail", "Готово"))


@dp.message(Command("quiz"))
async def cmd_quiz(message: Message):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{API_URL}/next_card?user={message.from_user.id}"
            )
            if resp.status_code != 200:
                await message.answer("Нет доступных карточек.")
                from app.models.retention_log import RetentionLog

                return

            card = resp.json()
            builder = InlineKeyboardBuilder()
            builder.button(
                text="Показать ответ",
                callback_data=f"show_{card['concept_id']}",
            )

            await message.answer(
                f"Слово: <b>{card['word']}</b>",
                reply_markup=builder.as_markup(),
            )
        except Exception as e:
            logger.error(f"Error in cmd_quiz: {str(e)}")
            await message.answer("Ошибка при получении карточки.")


@dp.message(Command("deepseek"))
async def cmd_deepseek(
    message: Message, user: User
):
    prompt_service = PromptService()
    analysis = await prompt_service.get_ai_analysis(str(user.id))
    await message.answer(analysis)


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
    if message.from_user.id in ADMIN_IDS:
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
                    email=f"user_{uuid.uuid4()}@example.com",
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
                    email=f"admin_{message.from_user.id}@example.com",
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
        for admin_id in ADMIN_IDS:
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
                email=f"user_{telegram_id}@example.com",
                hashed_password="default",
                confirmed=True,
            )
        )

        profile_repo = ProfileRepository(session)
        await profile_repo.add(
            UserProfile(
                user_id=user.id,
                username=request.username or f"user_{telegram_id}",
                email=f"user_{telegram_id}@example.com",
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


@dp.callback_query(F.data.startswith("show_"))
async def show_answer(callback: CallbackQuery):
    concept_id = int(callback.data.split("_")[1])
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{API_URL}/concept/{concept_id}")
            if resp.status_code != 200:
                await callback.answer("Ошибка загрузки определения")
                return

            concept_data = resp.json()
            definition = concept_data.get(
                "description", "Определение отсутствует"
            )

            if definition == "Автоматически извлеченный термин":
                definition += "\n\nℹ️ Вы можете добавить своё определение, используя формат: Концепт::Определение"

        except Exception as e:
            logger.error(f"Error getting concept: {str(e)}")
            await callback.answer("Ошибка")
            return

    builder = InlineKeyboardBuilder()
    builder.button(
        text="🤔 Плохо (повторить завтра)",
        callback_data=f"rate_{concept_id}_0.3",
    )
    builder.button(
        text="😐 Нормально (через 3 дня)",
        callback_data=f"rate_{concept_id}_0.6",
    )
    builder.button(
        text="😄 Отлично (через неделю)",
        callback_data=f"rate_{concept_id}_0.9",
    )
    builder.adjust(1)

    await callback.message.edit_text(
        f"<b>Термин:</b> {callback.message.text.split(': ')[1]}\n\n"
        f"<b>Определение:</b>\n{definition}\n\n"
        f"<i>Насколько хорошо вы помните это?</i>",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("rate_"))
async def process_rate(callback: CallbackQuery):
    await callback.answer("⏳ Обрабатываем ваш ответ...")

    data = callback.data.split("_")
    concept_id = int(data[1])
    quality = float(data[2])

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{API_URL}/review",
                json={
                    "user": callback.from_user.id,
                    "concept_id": concept_id,
                    "quality": quality,
                },
            )

            if resp.status_code == 200:
                result = resp.json()
                next_review = datetime.fromisoformat(result["next_review"])
                next_review_str = next_review.strftime("%d.%m.%Y")

                async with Session() as session:
                    user_repo = UserRepository(session)
                    user = await user_repo.get_by_telegram_id(
                        callback.from_user.id
                    )

                    if user:
                        prompt_service = PromptService()
                        analysis = await prompt_service.get_ai_analysis(
                            str(user.id)
                        )

                        if len(analysis) > 1000:
                            analysis = analysis[:1000] + "..."

                        response_text = (
                            f"{callback.message.text}\n\n"
                            f"✅ <b>Следующее повторение:</b> {next_review_str}\n\n"
                            f"<b>Анализ ваших знаний:</b>\n{analysis}"
                        )
                    else:
                        response_text = (
                            f"{callback.message.text}\n\n"
                            f"✅ <b>Следующее повторение:</b> {next_review_str}"
                        )

                await callback.message.edit_text(
                    response_text, reply_markup=None
                )
            else:
                await callback.message.answer(
                    "⚠️ Ошибка при обновлении. Попробуйте позже."
                )
    except Exception as e:
        logger.error(f"Error in process_rate: {str(e)}")
        await callback.message.answer(
            "⚠️ Произошла ошибка при обработке вашего ответа."
        )


@dp.message(F.text)
async def handle_text(message: Message, **kwargs):
    user = kwargs.get("user")
    if not user:
        await message.answer("❌ Пользователь не найден.")
        return

    prompt_service = PromptService()
    processor = TextProcessorService(prompt_service)

    async with Session() as session:
        try:
            profile_repo = ProfileRepository(session)
            profile = await profile_repo.get_one(user_id=user.id)

            domain_id = (
                profile.domain_id if profile and profile.domain_id else 1
            )

            added_concepts = await processor.process_text(
                text=message.text,
                user_id=user.id,
                domain_id=domain_id,
                session=session,
            )

            if "::" in message.text:
                await message.answer(
                    "✅ Определение концепта добавлено/обновлено!"
                )
            else:
                if added_concepts:
                    concepts_list = "\n".join(
                        [f"- {c}" for c in added_concepts]
                    )
                    await message.answer(
                        f"✅ Из текста извлечены концепты:\n{concepts_list}\n\n"
                        "Они добавлены в вашу карту знаний и будут использоваться "
                        "в повторениях!"
                    )
                else:
                    await message.answer(
                        "✅ Текст обработан. Новые концепты не найдены, "
                        "но существующие знания обновлены."
                    )

        except Exception as e:
            logger.error(f"Text processing error: {str(e)}", exc_info=True)
            await message.answer(
                "⚠️ Произошла ошибка при обработке текста. Попробуйте позже."
            )


async def update_concept_definition(message: Message, user: User):
    try:
        parts = message.text.split("::", 1)
        concept_name = parts[0].strip()
        definition = parts[1].strip()

        async with Session() as session:
            concept_repo = ConceptRepository(session)
            concept = await concept_repo.get_first(name=concept_name)

            if not concept:
                await message.answer(
                    "❌ Концепт не найден. Сначала добавьте текст с этим концептом."
                )
                return

            concept.description = definition
            await session.commit()

            await message.answer("✅ Определение концепта обновлено!")
    except Exception as e:
        logger.error(f"Error updating concept definition: {str(e)}")
        await message.answer(
            "⚠️ Ошибка при обновлении определения. Попробуйте позже."
        )


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


@dp.message(Command("map"))
async def cmd_knowledge_map(message: Message, user: User):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{API_URL}/knowledge_map/{user.id}")
            if resp.status_code != 200:
                await message.answer("Не удалось загрузить карту знаний.")
                return

            knowledge_map = resp.json()

            map_text = "🗺️ Ваша карта знаний:\n\n"
            for concept in knowledge_map["concepts"]:
                retention = knowledge_map["retention_levels"][concept]
                connections = ", ".join(
                    knowledge_map["connections"].get(concept, [])
                )

                retention_emoji = "🔴"
                if retention > 0.7:
                    retention_emoji = "🟢"
                elif retention > 0.5:
                    retention_emoji = "🟡"

                map_text += f"{retention_emoji} <b>{concept}</b> (Удержание: {retention:.0%})\n"
                if connections:
                    map_text += f"    Связано с: {connections}\n"
                map_text += "\n"

            await message.answer(map_text)

        except Exception as e:
            logger.error(f"Error getting knowledge map: {str(e)}")
            await message.answer("⚠️ Ошибка при формировании карты знаний.")


@dp.message(Command("start"))
async def cmd_start(message: Message):
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(
            text="Добавить текст", callback_data="add_text"
        ),
        types.InlineKeyboardButton(
            text="Повторить карточки", callback_data="quiz"
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

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{API_URL}/concept/search?name={concept_name}"
            )

            if resp.status_code != 200:
                await message.answer("Концепт не найден")
                return

            concept = resp.json()

            resp = await client.post(
                f"{API_URL}/concept/update",
                json={"concept_id": concept["id"], "definition": definition},
            )

            if resp.status_code == 200:
                await message.answer("✅ Определение обновлено!")
            else:
                await message.answer("❌ Ошибка при обновлении")

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


@dp.callback_query(F.data == "analysis")
async def process_analysis(callback: CallbackQuery):
    await cmd_deepseek(callback.message)
    await callback.answer()


@dp.message(F.text == "Добавить текст")
async def handle_add_text(message: Message):
    await message.answer(
        "Введите текст для добавления или используйте команду /add [текст]"
    )


@dp.message(F.text == "Повторить карточки")
async def handle_quiz(message: Message):
    await cmd_quiz(message)


@dp.message(F.text == "Анализ знаний")
async def handle_analysis(message: Message):
    await cmd_deepseek(message)


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

        for admin_id in ADMIN_IDS:
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
