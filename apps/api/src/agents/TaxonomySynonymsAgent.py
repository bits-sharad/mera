from __future__ import annotations

from typing import Any, Dict

from src.agents.base import AgentBase
from src.core.audit import AuditTrail
from src.schemas.common import AgentResult


class TaxonomySynonymsAgent(AgentBase):
    name = "taxonomy_synonyms"

    async def run(self, state: Dict[str, Any], audit: AuditTrail) -> AgentResult:
        audit.add("agent_start", {"agent": self.name})

        out = {"synonyms": {}}

        audit.add(
            "agent_end", {"agent": self.name, "synonyms_count": len(out["synonyms"])}
        )
        return AgentResult(agent=self.name, output=out, sources=[])
