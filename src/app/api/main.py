from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from app.db import Session
from app.models.domains import Domain
from app.models.user_domains import UserDomain
from app.models.users import User
from app.models.user_profile import UserProfile
from app.repositories.domain_repository import DomainRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.user_domain_repository import UserDomainRepository
from app.repositories.user_repository import UserRepository
import logging
from app.services.email import send_confirmation_email
from app.services.auth import create_confirmation_token
from app.services.auth import verify_confirmation_token
from fastapi.security import APIKeyHeader
import uuid
import os


class RegisterRequest(BaseModel):
    telegram_id: int
    email: str


admin_header = APIKeyHeader(name="X-Admin-Token")
logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

load_dotenv()

app = FastAPI(title="Scientia API")


# Pydantic‑схемы
class AddRequest(BaseModel):
    telegram_id: int  # Вместо user: str
    text: str


class CardResponse(BaseModel):
    word: str


# Dependency (async)
async def get_repos():
    async with Session() as session:
        yield {
            "users": UserRepository(session),
            "profiles": ProfileRepository(session),
            "domains": DomainRepository(session),
            "user_domains": UserDomainRepository(session),
        }


@app.post("/sync")
async def sync_all(repos=Depends(get_repos)):
    # здесь будет асинхронная логика
    return {"detail": "Synchronization complete"}


@app.post("/add")
async def add_to_buffer(req: AddRequest, repos=Depends(get_repos)):
    try:
        user_repo = repos["users"]
        profile_repo = repos["profiles"]
        domain_repo = repos["domains"]
        user_domain_repo = repos["user_domains"]

        # Получаем или создаем пользователя
        user = await user_repo.get_by_telegram_id(req.telegram_id)
        if not user:
            user = await user_repo.add(
                User(
                    telegram_id=req.telegram_id,
                    email=f"user_{req.telegram_id}@example.com",
                    hashed_password="default",
                )
            )

        # Создаем профиль если нужно
        if not await profile_repo.get_one(user_id=user.id):
            await profile_repo.add(
                UserProfile(
                    user_id=user.id,
                    username=f"user_{user.id}",
                    email=f"user_{user.id}@example.com",
                )
            )

        # Получаем или создаем домен
        domain = await domain_repo.add(
            Domain(name=req.text, description="added via bot")
        )

        # Создаем связь если не существует
        if not await user_domain_repo.get_first(
            user_id=user.id, domain_id=domain.id
        ):
            await user_domain_repo.add(
                UserDomain(user_id=user.id, domain_id=domain.id, level=1)
            )

        return {"detail": "Added"}

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        raise HTTPException(500, "Internal server error")


@app.get("/next_card", response_model=CardResponse)
async def next_card(user: int, repos=Depends(get_repos)):
    user_domain_repo = repos["user_domains"]
    domain_repo = repos["domains"]

    ud = await user_domain_repo.get_by_user(user)
    if not ud:
        raise HTTPException(status_code=404, detail="No cards")

    domain = await domain_repo.get_by_id(ud[0].domain_id)
    return {"word": domain.name}


@app.post("/register")
async def register_user(req: RegisterRequest, repos=Depends(get_repos)):
    user_repo = repos["users"]

    # Проверяем существование пользователя
    user = await user_repo.get_by_telegram_id(req.telegram_id)
    if user:
        raise HTTPException(400, "User already exists")

    # Создаем нового пользователя
    new_user = await user_repo.add(
        User(
            telegram_id=req.telegram_id,
            email=req.email,
            hashed_password="temporary",
        )
    )

    # Отправляем письмо подтверждения
    token = create_confirmation_token(str(new_user.id))
    await send_confirmation_email(req.email, token)

    return {"detail": "Confirmation email sent"}


@app.get("/confirm-email")
async def confirm_email(token: str, repos=Depends(get_repos)):
    user_id = verify_confirmation_token(token)
    user = await repos["users"].get_by_id(user_id)

    if not user:
        raise HTTPException(400, "Invalid token")

    user.confirmed = True
    await repos["users"].session.commit()

    return {"detail": "Email confirmed"}


@app.post("/admin/grant-premium")
async def grant_premium(
    user_id: uuid.UUID,
    repos=Depends(get_repos),
    token: str = Depends(admin_header),
):
    # Проверка админского токена
    if token != os.getenv("ADMIN_SECRET"):
        raise HTTPException(403, "Forbidden")

    user = await repos["users"].get_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")

    user.is_premium = True
    await repos["users"].session.commit()
    return {"detail": "Premium access granted"}
