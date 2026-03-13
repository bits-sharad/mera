from __future__ import annotations

from typing import Any, Dict

from src.agents.base import AgentBase
from src.core.audit import AuditTrail
from src.schemas.common import AgentResult


class ConversationalFeedbackAgent(AgentBase):
    name = "conversational_feedback"

    async def run(self, state: Dict[str, Any], audit: AuditTrail) -> AgentResult:
        pass
