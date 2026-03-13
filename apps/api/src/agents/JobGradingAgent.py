from __future__ import annotations

import logging
from typing import Any

from src.agents.base import AgentBase
from src.core.audit import AuditTrail
from src.schemas.common import AgentResult
from src.services.mmc_project import ProjectService
from src.services.mmc_jobs import JobService


logger = logging.getLogger(__name__)

GRADING_SYSTEM = """You are a job grading specialist using Mercer IPE factors.
Return JSON with keys: points, career_level, position_class, factors (object), confidence (0-1), rationale.
"""


class JobGradingAgent(AgentBase):
    name = "job_grading"

    def __init__(self, core_api):
        """Initialize job grading agent"""

    async def run(self, state: dict[str, Any], audit: AuditTrail) -> AgentResult:
        pass
