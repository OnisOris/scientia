import os
from typing import List
import httpx
from dotenv import load_dotenv
from app.db import Session
from app.repositories.user_domain_repository import UserDomainRepository
from app.repositories.domain_repository import DomainRepository

load_dotenv()


class PromptService:
    def __init__(self):
        self.ai_api_url = os.getenv("DEEPSEEK_API_URL")
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.default_prompt = """Проанализируй список тем (domains) пользователя и предложи:
1. 3 ключевые области для развития
2. Рекомендации по изучению каждой темы
3. Связи между темами"""

    async def _get_user_domains(self, user_id: str) -> List[str]:
        async with Session() as session:
            domain_repo = DomainRepository(session)
            user_domain_repo = UserDomainRepository(session)

            user_domains = await user_domain_repo.get_by_user(user_id)
            domains = []
            for ud in user_domains:
                domain = await domain_repo.get_by_id(ud.domain_id)
                if domain:
                    domains.append(domain.name)
            return domains

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
            print("something")
            prompt = await self.generate_analysis_prompt(user_id)
            if not self.ai_api_url or not self.api_key:
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
                response = await client.post(
                    self.ai_api_url, json=payload, headers=headers, timeout=30
                )
                response.raise_for_status()

                data = response.json()
                return data["choices"][0]["message"]["content"]

        except Exception as e:
            return f"Ошибка при обращении к AI-сервису: {str(e)}"
