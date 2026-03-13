from __future__ import annotations

from typing import Any, Dict

from src.agents.base import AgentBase
from src.core.audit import AuditTrail
from src.schemas.common import AgentResult

JD_SYSTEM = """You are a job description generation agent.
Return JSON with keys: job_description (markdown), responsibilities (list), requirements (list), confidence, rationale.
"""


class JobDescriptionGenerationAgent(AgentBase):
    name = "job_description_generation"

    async def run(self, state: Dict[str, Any], audit: AuditTrail) -> AgentResult:
        pass
