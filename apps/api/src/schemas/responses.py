from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from src.schemas.common import AgentResult, AuditBundle


class ChatResponse(BaseModel):
    session_id: str
    final_answer: str
    fused: dict[str, Any] = Field(default_factory=dict)
    agent_results: list[AgentResult] = Field(default_factory=list)
    audit: AuditBundle | None = None
