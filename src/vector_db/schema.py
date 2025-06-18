from pydantic import BaseModel
from weaviate.classes.config import (
    Configure,
    Property,
    # VectorIndexType,
    VectorDistances,
)


class TextFragment(BaseModel):
    content: str
    user_id: str
    source: str = "telegram"
    created_at: str  # ISO format


class WeaviateClassConfig(BaseModel):
    name: str
    properties: list[Property]
    vectorizer_config: Configure.Vectorizer
    vector_index_config: Configure.VectorIndex = Configure.VectorIndex.hnsw(
        distance_metric=VectorDistances.COSINE
    )


class SemanticSearchQuery(BaseModel):
    query: str
    user_id: str
    limit: int = 5
    certainty: float = 0.7
