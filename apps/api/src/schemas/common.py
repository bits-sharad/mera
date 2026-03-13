from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class RAGSource(BaseModel):
    id: str
    score: float
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditBundle(BaseModel):
    events: list[dict[str, Any]]


class AgentResult(BaseModel):
    agent: str
    output: dict[str, Any] = Field(default_factory=dict)
    sources: list[RAGSource] = Field(default_factory=list)
    rationale: str | None = None
