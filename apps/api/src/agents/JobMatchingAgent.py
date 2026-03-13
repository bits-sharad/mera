from __future__ import annotations
import logging
from typing import Any
from src.services.mjl.match_result import MatchResultService
from src.services.mjl.search.context_search import (
    SearchInput,
    retrieve_and_rank,
)
from src.agents.base import AgentBase
from src.core.audit import AuditTrail
from src.orchestrator.state import GraphState
from src.services.mmc_project import ProjectService
from src.services.mmc_jobs import JobService
from src.services.mmc_job_subfamilies import JobSubfamilyService
from src.services.mmc_job_families import JobFamilyService
from src.services.mjl.mjl_job_matching import MJLJobMatching

# from src.services.hybrid_search_service import HybridSearchService
import json
import pandas as pd
import uuid
import os

logger = logging.getLogger(__name__)

MATCHING_SYSTEM = """You are a job matching agent.
Return JSON with keys: matches (list of {job_id, title, score, why}), confidence, rationale.
"""

class JobMatchingAgent(AgentBase):
    # Cache for processed (job_title, job_description) -> result
    _job_cache = {}
    name = "job_matching"

    def __init__(self, core_api):
        """Initialize job matching agent"""
        super().__init__(core_api)
        self.project_service = None
        self.job_service = None
        self.job_subfamily_service = None

    async def run(self, state: GraphState, audit: AuditTrail) -> GraphState:
        return await MJLJobMatching(self.core_api).match(state, audit)