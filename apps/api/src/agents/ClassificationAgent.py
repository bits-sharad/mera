from __future__ import annotations

from typing import Any, Dict

from src.agents.base import AgentBase
from src.core.audit import AuditTrail
from src.schemas.common import AgentResult


CLASSIFY_SYSTEM = """You are a job architecture classification expert.
Return a JSON object with keys: job_family, sub_family, career_stream, level, confidence (0-1), rationale.
Be concise and use only evidence provided in the prompt/context.
"""


class ClassificationAgent(AgentBase):
    name = "classification_model"

    async def run(self, state: Dict[str, Any], audit: AuditTrail) -> AgentResult:
        pass
