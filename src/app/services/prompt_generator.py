import os
from typing import List
import httpx
from dotenv import load_dotenv
from app.db import Session
from app.repositories.user_domain_repository import UserDomainRepository
from app.repositories.domain_repository import DomainRepository
import logging
import uuid


load_dotenv()

logger = logging.getLogger(__name__)


class PromptService:
    def __init__(self):
        self.ai_api_url = os.getenv("DEEPSEEK_API_URL")
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.default_prompt = """Проанализируй список тем (domains) пользователя и предложи:
1. 3 ключевые области для развития
2. Рекомендации по изучению каждой темы
3. Связи между темами"""
        logger.info(f"DeepSeek API URL: {self.ai_api_url}")
        logger.info(
            f"DeepSeek API Key: {'set' if self.api_key else 'not set'}"
        )

    async def _get_user_domains(self, user_id: str) -> List[str]:
        try:
            user_uuid = uuid.UUID(user_id)
            async with Session() as session:
                domain_repo = DomainRepository(session)
                user_domain_repo = UserDomainRepository(session)

                user_domains = await user_domain_repo.get_by_user(user_uuid)
                domains = []
                for ud in user_domains:
                    domain = await domain_repo.get_by_id(ud.domain_id)
                    if domain:
                        domains.append(domain.name)
                return domains
        except Exception as e:
            logger.error(f"Error getting user domains: {str(e)}")
            return []

    async def generate_analysis_prompt(self, user_id: str) -> str:
        domains = await self._get_user_domains(user_id)
        if not domains:
            return "У вас пока нет добавленных тем для анализа"

        domains_list = "\n- ".join(domains)
        return f"""Пользователь работает со следующими темами:
- {domains_list}

{self.default_prompt}"""

    async def get_ai_analysis(self, user_id: str) -> str:
        try:
            logger.info("Starting AI analysis")
            prompt = await self.generate_analysis_prompt(user_id)

            if not self.ai_api_url or not self.api_key:
                logger.error("AI service configuration error")
                return "Ошибка конфигурации AI-сервиса"

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
            }

            async with httpx.AsyncClient() as client:
                logger.info(f"Sending request to AI API: {payload}")
                response = await client.post(
                    self.ai_api_url,
                    json=payload,
                    headers=headers,
                    timeout=60,
                )
                response.raise_for_status()

                data = response.json()
                logger.info("AI response received successfully")
                return data["choices"][0]["message"]["content"]

        except httpx.HTTPError as e:
            logger.error(f"HTTP error in AI service: {str(e)}")
            return f"Ошибка сети при обращении к AI-сервису: {str(e)}"
        except Exception as e:
            logger.exception("Unexpected error in AI service")
            return f"Неожиданная ошибка при обращении к AI-сервису: {str(e)}"

    async def generate_concept_definition(self, concept_name: str) -> str:
        """Генерирует определение концепта с помощью AI"""
        if not self.ai_api_url or not self.api_key:
            return "Автоматически извлеченный термин"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Сгенерируй краткое, понятное и информативное определение "
                        f"для термина '{concept_name}' на русском языке. "
                        "Определение должно быть длиной 1-2 предложения, "
                        "достаточно подробным для учебных целей."
                    ),
                }
            ],
            "temperature": 0.5,
            "max_tokens": 150,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.ai_api_url, json=payload, headers=headers, timeout=30
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Error generating definition: {str(e)}")
            return "Автоматически извлеченный термин"
