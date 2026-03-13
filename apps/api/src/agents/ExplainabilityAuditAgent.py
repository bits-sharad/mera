from __future__ import annotations

from typing import Any

from src.agents.base import AgentBase
from src.core.audit import AuditTrail
from src.schemas.common import AgentResult


class ExplainabilityAuditAgent(AgentBase):
    name = "explainability_audit"

    async def run(self, state: Any, audit: AuditTrail) -> AgentResult:
        audit.add("agent_start", {"agent": self.name})

        agent_results = getattr(state, "agent_results", [])

        # Handle both AgentResult objects and dicts (from serialization)
        sources_used = []
        for r in agent_results:
            if isinstance(r, dict):
                # Already serialized to dict
                agent_name = r.get("agent", "unknown")
                sources = r.get("sources", [])
            else:
                # AgentResult object
                agent_name = r.agent
                sources = [s.model_dump() for s in r.sources]
            sources_used.append({"agent": agent_name, "sources": sources})

        out = {
            "reasoning_path": getattr(state, "routing", {}),
            "sources_used": sources_used,
            "notes": "Persist this bundle via Core API metadata/audit store in production.",
        }

        audit.add("agent_end", {"agent": self.name})
        return AgentResult(agent=self.name, output=out)
