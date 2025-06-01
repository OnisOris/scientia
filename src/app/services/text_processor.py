from app.utils.text import normalize_text
from app.repositories.concept_repository import ConceptRepository
from app.repositories.user_knowledge_repository import UserKnowledgeRepository
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from razdel import tokenize, sentenize
from app.models.user_knowledge import UserKnowledge
from datetime import datetime, timedelta
import re
import logging
from app.services.nlp_loader import get_nlp_model

logger = logging.getLogger(__name__)

ALLOWED_ENT_TYPES = {"PER", "ORG", "LOC", "MISC", "GPE", "EVENT", "PRODUCT"}


class TextProcessorService:
    def __init__(self, prompt_service=None):
        self.nlp = get_nlp_model()
        self.prompt_service = prompt_service

    async def _extract_concepts(self, text: str):
        if not text.strip():
            return set()

        concepts = set()
        sentences = [s.text for s in sentenize(text)]

        for sentence in sentences:
            doc = self.nlp(sentence)

            for ent in doc.ents:
                if ent.label_ in ALLOWED_ENT_TYPES and len(ent.text) > 3:
                    normalized = normalize_text(ent.text)
                    concepts.add(normalized)

            tokens = [token.text for token in tokenize(sentence)]

            pos_tags = {token.text: token.pos_ for token in doc}

            for i in range(len(tokens)):
                token = tokens[i]
                if len(token) < 4:
                    continue

                pos_tag = pos_tags.get(token, "")

                if pos_tag in {"NOUN", "PROPN"}:
                    concepts.add(normalize_text(token))
                if i < len(tokens) - 1:
                    next_token = tokens[i + 1]
                    next_pos = pos_tags.get(next_token, "")

                    if pos_tag == "ADJ" and next_pos in {"NOUN", "PROPN"}:
                        phrase = f"{token} {next_token}"
                        if len(phrase) > 7:
                            concepts.add(normalize_text(phrase))
                if i < len(tokens) - 2:
                    next_token1 = tokens[i + 1]
                    next_token2 = tokens[i + 2]
                    next_pos1 = pos_tags.get(next_token1, "")
                    next_pos2 = pos_tags.get(next_token2, "")

                    if (
                        pos_tag == "ADJ"
                        and next_pos1 == "ADJ"
                        and next_pos2 in {"NOUN", "PROPN"}
                    ):
                        phrase = f"{token} {next_token1} {next_token2}"
                        if len(phrase) > 10:
                            concepts.add(normalize_text(phrase))
        custom_defs = {}
        lines = text.split("\n")
        for line in lines:
            if "::" in line:
                parts = line.split("::", 1)
                concept_name = normalize_text(parts[0].strip())
                definition = parts[1].strip()
                custom_defs[concept_name] = definition

        return concepts

    @staticmethod
    def normalize_text(text: str) -> str:
        """Нормализует текст для обработки"""
        text = re.sub(r"\s+", " ", text).strip()
        return text.lower()

    def _extract_custom_definitions(self, text: str) -> dict:
        """Извлекает пользовательские определения из текста"""
        custom_defs = {}
        lines = text.split("\n")

        for line in lines:
            if "::" in line:
                parts = line.split("::", 1)
                concept_name = self.normalize_text(parts[0].strip())
                definition = parts[1].strip()
                custom_defs[concept_name] = definition

        return custom_defs

    async def process_text(
        self,
        text: str,
        user_id: uuid.UUID,
        domain_id: int,
        session: AsyncSession,
    ) -> list:
        concepts = await self._extract_concepts(text)
        custom_defs = self._extract_custom_definitions(text)

        concept_repo = ConceptRepository(session)
        knowledge_repo = UserKnowledgeRepository(session)

        new_concepts_to_generate = []
        added_concepts = []

        for concept_name in concepts:
            if not concept_name:
                continue
            if concept_name in custom_defs:
                description = custom_defs[concept_name]
                concept = await concept_repo.get_or_create(
                    name=concept_name,
                    domain_id=domain_id,
                    description=description,
                )
                added_concepts.append(concept_name)
            else:
                existing_concept = await concept_repo.get_first(
                    name=concept_name
                )

                if existing_concept and existing_concept.description:
                    concept = existing_concept
                else:
                    new_concepts_to_generate.append(concept_name)
                    concept = await concept_repo.get_or_create(
                        name=concept_name,
                        domain_id=domain_id,
                        description="Автоматически извлеченный термин",
                    )
                    added_concepts.append(concept_name)

            knowledge = await knowledge_repo.get_first(
                user_id=user_id, concept_id=concept.id
            )

            if not knowledge:
                await knowledge_repo.add(
                    UserKnowledge(
                        user_id=user_id,
                        concept_id=concept.id,
                        retention=0.5,
                        last_reviewed=datetime.utcnow(),
                        next_review=datetime.utcnow() + timedelta(days=1),
                    )
                )

        if new_concepts_to_generate and self.prompt_service:
            for concept_name in new_concepts_to_generate:
                ai_definition = (
                    await self.prompt_service.generate_concept_definition(
                        concept_name
                    )
                )
                concept = await concept_repo.get_first(name=concept_name)
                if concept:
                    concept.description = ai_definition
                    await session.commit()

        return added_concepts

    async def find_concept_relations(
        self, concepts: list, session: AsyncSession
    ) -> dict:
        """Находит связи между концептами на основе совместного употребления"""
        if not concepts:
            return {}
        concept_repo = ConceptRepository(session)
        concept_ids = []
        for concept_name in concepts:
            concept = await concept_repo.get_first(name=concept_name)
            if concept:
                concept_ids.append(concept.id)

        if not concept_ids:
            return {}
        query = text("""
            SELECT c1.name AS concept_from, c2.name AS concept_to, COUNT(*) AS cooccurrence_count
            FROM user_knowledge uk1
            JOIN user_knowledge uk2 ON uk1.user_id = uk2.user_id
            JOIN concepts c1 ON uk1.concept_id = c1.id
            JOIN concepts c2 ON uk2.concept_id = c2.id
            WHERE c1.id IN :concept_ids
            AND c2.id IN :concept_ids
            AND c1.id != c2.id
            GROUP BY c1.name, c2.name
            ORDER BY cooccurrence_count DESC
        """)
        result = await session.execute(
            query, {"concept_ids": tuple(concept_ids)}
        )
        relations = {concept: [] for concept in concepts}
        for row in result.all():
            concept_from = row[0]
            concept_to = row[1]

            if concept_from in relations and len(relations[concept_from]) < 3:
                relations[concept_from].append(concept_to)

        return relations
