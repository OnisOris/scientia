import logging
import os
import uuid
# from datetime import datetime, timedelta
# from uuid import UUID
# from typing import List, Dict

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException  # , Query
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from app.db import Session

# from app.models.domains import Domain
# from app.models.user_domains import UserDomain
# from app.models.user_profile import UserProfile
from app.models.users import User

from app.repositories.profile_repository import ProfileRepository

from app.repositories.user_repository import UserRepository
# from app.services.auth import (
#     create_confirmation_token,
#     verify_confirmation_token,
# )


class RegisterRequest(BaseModel):
    telegram_id: int
    # email: str


# class UpdateConceptRequest(BaseModel):
#     concept_id: int
#     definition: str


admin_header = APIKeyHeader(name="X-Admin-Token")
logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

load_dotenv()

app = FastAPI(title="Scientia API")

#
# class AddRequest(BaseModel):
#     telegram_id: int
#     text: str


# class CardResponse(BaseModel):
#     concept_id: int
#     word: str
#     definition: str


# class KnowledgeItemResponse(BaseModel):
#     concept: str
#     retention: float
#     next_review: datetime


# class UserStatsResponse(BaseModel):
#     total_concepts: int
#     weak_concepts: int
#     strong_concepts: int
#     reviews_last_7_days: int
#     avg_retention: float
#     concepts_added_last_7_days: int
#     avg_reviews_per_concept: float


# class KnowledgeMapResponse(BaseModel):
#     concepts: List[str]
#     connections: Dict[str, List[str]]
#     retention_levels: Dict[str, float]
#     next_reviews: Dict[str, datetime]

#
# class ReviewRequest(BaseModel):
#     user: int
#     concept_id: int
#     quality: float


async def get_repos():
    async with Session() as session:
        yield {
            "users": UserRepository(session),
            "profiles": ProfileRepository(session),
            # "domains": DomainRepository(session),
            # "user_domains": UserDomainRepository(session),
            # "user_knowledge": UserKnowledgeRepository(session),
            # "retention_logs": RetentionLogRepository(session),
            # "concepts": ConceptRepository(session),
        }


@app.post("/sync")
async def sync_all(repos=Depends(get_repos)):
    return {"detail": "Synchronization complete"}


# @app.post("/concept/update")
# async def update_concept(req: UpdateConceptRequest, repos=Depends(get_repos)):
#     concept_repo = repos["concepts"]
#     concept = await concept_repo.get_by_id(req.concept_id)
#
#     if not concept:
#         raise HTTPException(404, "Concept not found")
#
#     concept.description = req.definition
#     await repos["concepts"].session.commit()
#
#     return {"status": "updated"}
#

#
# @app.get("/concept/search")
# async def search_concept(name: str, repos=Depends(get_repos)):
#     """
#     В данный момент не нужно
#     """
#     concept_repo = repos["concepts"]
#     concept = await concept_repo.get_first(name=name)
#
#     if not concept:
#         raise HTTPException(404, "Concept not found")
#
#     return {
#         "id": concept.id,
#         "name": concept.name,
#         "definition": concept.description,
#     }
#

# @app.post("/add")
# async def add_to_buffer(req: AddRequest, repos=Depends(get_repos)):
#     try:
#         user_repo = repos["users"]
#         profile_repo = repos["profiles"]
#         domain_repo = repos["domains"]
#         user_domain_repo = repos["user_domains"]
#
#         user = await user_repo.get_by_telegram_id(req.telegram_id)
#         if not user:
#             user = await user_repo.add(
#                 User(
#                     telegram_id=req.telegram_id,
#                     email=f"user_{req.telegram_id}@example.com",
#                     hashed_password="default",
#                     lambda_coef=0.5,
#                 )
#             )
#
#         if not await profile_repo.get_one(user_id=user.id):
#             await profile_repo.add(
#                 UserProfile(
#                     user_id=user.id,
#                     username=f"user_{user.id}",
#                     email=f"user_{user.id}@example.com",
#                 )
#             )
#
#         domain = await domain_repo.add(
#             Domain(name=req.text, description="added via bot")
#         )
#
#         if not await user_domain_repo.get_first(
#             user_id=user.id, domain_id=domain.id
#         ):
#             await user_domain_repo.add(
#                 UserDomain(user_id=user.id, domain_id=domain.id, level=1)
#             )
#
#         return {"detail": "Added"}
#
#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         logger.error(f"Error: {str(e)}", exc_info=True)
#         raise HTTPException(500, "Internal server error")
#


# @app.get("/next_card", response_model=CardResponse)
# async def next_card(user: int, repos=Depends(get_repos)):
#     user_repo = repos["users"]
#     db_user = await user_repo.get_by_telegram_id(user)
#     if not db_user:
#         raise HTTPException(status_code=404, detail="User not found")
#
#     knowledge_repo = repos["user_knowledge"]
#     items = await knowledge_repo.get_by_user_with_concepts(db_user.id, limit=1)
#
#     if not items:
#         raise HTTPException(status_code=404, detail="No cards")
#
#     item, concept_name = items[0]
#     concept_repo = repos["concepts"]
#     concept = await concept_repo.get_by_id(item.concept_id)
#
#     return {
#         "concept_id": item.concept_id,
#         "word": concept_name,
#         "definition": concept.description or "Без определения",
#     }
#


@app.post("/register")
async def register_user(req: RegisterRequest, repos=Depends(get_repos)):
    user_repo = repos["users"]

    user = await user_repo.get_by_telegram_id(req.telegram_id)
    if user:
        raise HTTPException(400, "User already exists")

    await user_repo.add(
        User(
            telegram_id=req.telegram_id,
            # email=req.email,
            hashed_password="temporary",
            # lambda_coef=0.5,
        )
    )

    # token = create_confirmation_token(str(new_user.id))
    # await send_confirmation_email(req.email, token)

    return {"detail": "You're registered"}


# @app.get("/confirm-email")
# async def confirm_email(token: str, repos=Depends(get_repos)):
#     user_id = verify_confirmation_token(token)
#     user = await repos["users"].get_by_id(user_id)
#
#     if not user:
#         raise HTTPException(400, "Invalid token")
#
#     user.confirmed = True
#     await repos["users"].session.commit()
#
#     return {"detail": "Email confirmed"}


@app.post("/admin/grant-premium")
async def grant_premium(
    user_id: uuid.UUID,
    repos=Depends(get_repos),
    token: str = Depends(admin_header),
):
    if token != os.getenv("ADMIN_SECRET"):
        raise HTTPException(403, "Forbidden")

    user = await repos["users"].get_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")

    user.is_premium = True
    await repos["users"].session.commit()
    return {"detail": "Premium access granted"}


# @app.get("/knowledge/{user_id}", response_model=List[KnowledgeItemResponse])
# async def get_user_knowledge(
#     user_id: UUID,
#     limit: int = Query(20, description="Количество возвращаемых элементов"),
#     repos=Depends(get_repos),
# ):
#     knowledge_repo = repos["user_knowledge"]
#     items = await knowledge_repo.get_by_user_with_concepts(
#         user_id, limit=limit
#     )
#
#     return [
#         {
#             "concept": concept_name,
#             "retention": item.retention,
#             "next_review": item.next_review,
#         }
#         for item, concept_name in items
#     ]
#


# @app.get("/users/{user_id}/stats", response_model=UserStatsResponse)
# async def get_user_stats(user_id: UUID, repos=Depends(get_repos)):
#     knowledge_repo = repos["user_knowledge"]
#     logs_repo = repos["retention_logs"]
#
#     total = await knowledge_repo.count_by_user(user_id)
#     weak = await knowledge_repo.count_by_user(user_id, max_retention=0.5)
#     strong = await knowledge_repo.count_by_user(user_id, min_retention=0.7)
#
#     now = datetime.utcnow()
#     week_ago = now - timedelta(days=7)
#
#     reviews = await logs_repo.count_by_user_and_period(user_id, week_ago, now)
#     avg_retention = await knowledge_repo.avg_retention_by_user(user_id)
#     added = await knowledge_repo.count_added_in_period(user_id, week_ago, now)
#
#     avg_reviews = reviews / total if total > 0 else 0
#
#     return UserStatsResponse(
#         total_concepts=total,
#         weak_concepts=weak,
#         strong_concepts=strong,
#         reviews_last_7_days=reviews,
#         avg_retention=avg_retention,
#         concepts_added_last_7_days=added,
#         avg_reviews_per_concept=avg_reviews,
#     )
#
#


# @app.post("/review")
# async def review(req: ReviewRequest, repos=Depends(get_repos)):
#     user_repo = repos["users"]
#     user = await user_repo.get_by_telegram_id(req.user)
#     if not user:
#         raise HTTPException(404, "User not found")
#
#     knowledge_repo = repos["user_knowledge"]
#     knowledge = await knowledge_repo.get_first(
#         user_id=user.id, concept_id=req.concept_id
#     )
#
#     if not knowledge:
#         raise HTTPException(404, "Knowledge record not found")
#
#     srs = SpacedRepetitionService()
#     updated_user, updated_knowledge, log_data = srs.update_knowledge(
#         user, knowledge, req.quality
#     )
#     #
#     # knowledge.retention = updated_knowledge.retention
#     # knowledge.last_reviewed = updated_knowledge.last_reviewed
#     # knowledge.next_review = updated_knowledge.next_review
#     # user.lambda_coef = updated_user.lambda_coef
#
#     log_repo = repos["retention_logs"]
#     await log_repo.add(
#         RetentionLog(
#             user_id=log_data.user_id,
#             concept_id=log_data.concept_id,
#             old_lambda=log_data.old_lambda,
#             new_lambda=log_data.new_lambda,
#             retention_before=log_data.retention_before,
#             retention_after=log_data.retention_after,
#         )
#     )
#
#     await repos["user_knowledge"].session.commit()
#
#     return {
#         "next_review": knowledge.next_review.isoformat(),
#         "retention": knowledge.retention,
#     }
#

#
# @app.get("/concept/{concept_id}")
# async def get_concept(concept_id: int, repos=Depends(get_repos)):
#     concept_repo = repos["concepts"]
#     concept = await concept_repo.get_by_id(concept_id)
#     if not concept:
#         raise HTTPException(404, "Concept not found")
#     return {"description": concept.description}
#

#
# @app.get("/knowledge_map/{user_id}", response_model=KnowledgeMapResponse)
# async def get_knowledge_map(
#     user_id: UUID, limit: int = 20, repos=Depends(get_repos)
# ):
#     knowledge_repo = repos["user_knowledge"]
#
#     knowledge_items = await knowledge_repo.get_by_user_with_concepts(
#         user_id, limit=limit
#     )
#
#     if not knowledge_items:
#         return KnowledgeMapResponse(
#             concepts=[], connections={}, retention_levels={}, next_reviews={}
#         )
#
#     concepts = [concept_name for _, concept_name in knowledge_items]
#
#     retention_levels = {}
#     next_reviews = {}
#
#     for knowledge, concept_name in knowledge_items:
#         retention_levels[concept_name] = knowledge.retention
#         next_reviews[concept_name] = knowledge.next_review
#
#     text_processor = TextProcessorService()
#
#     session = repos["concepts"].session
#     connections = await text_processor.find_concept_relations(
#         concepts, session
#     )
#
#     return KnowledgeMapResponse(
#         concepts=concepts,
#         connections=connections,
#         retention_levels=retention_levels,
#         next_reviews=next_reviews,
#     )
