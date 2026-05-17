from typing import Any, Optional, Dict
from pydantic import BaseModel


class AnalysisResponse(BaseModel):
    prompt: str
    result: Any


class BiniTextRequestSchema(BaseModel):
    prompt: str
    schema_output: Optional[Dict] = None


class SemanticSearchRequestSchema(BaseModel):
    context: str
    question: str


class SemanticSearchResponseSchema(BaseModel):
    response: dict
