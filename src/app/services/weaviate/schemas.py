from pydantic import BaseModel
from typing import List


class DocumentSchema(BaseModel):
    id: str
    text: str
    vector: List[float]
    metadata: dict
