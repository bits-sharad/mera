from __future__ import annotations

import logging
from typing import Any

from src.agents.base import AgentBase
from src.core.audit import AuditTrail
from src.orchestrator.state import GraphState
from src.schemas.common import AgentResult

logger = logging.getLogger(__name__)


class FusionAgent(AgentBase):
    name = "fusion"

    async def run(self, state: GraphState, audit: AuditTrail) -> AgentResult:
        """
        Fuse outputs from all agents in the state after validation passes.

        Reads validated outputs from state and creates final AgentResult.
        Applies conditional logic for each agent output.
        """
        audit.add("agent_start", {"agent": self.name, "action": "fusion_start"})

        try:
            fused: dict[str, Any] = {}

            # Conditional: Process grading output
            grading = getattr(state, "grading", None)
            if isinstance(grading, dict) and grading.get("status") == "completed":
                fused["grading"] = {
                    "score": grading.get("score"),
                    "ipe_factors": grading.get("ipe_factors"),
                    "rationale": grading.get("rationale"),
                    "status": "included",
                }
                audit.add(
                    "fusion_grading",
                    {"status": "included", "has_score": "score" in grading},
                )
            else:
                fused["grading"] = {"status": "unavailable"}
                audit.add(
                    "fusion_grading",
                    {"status": "skipped", "reason": "grading_incomplete"},
                )

            # Conditional: Process matching output
            matching = getattr(state, "matching", None)
            if isinstance(matching, dict) and matching.get("status") == "completed":
                matches = matching.get("matches", [])
                valid_matches = [
                    m for m in matches if m.get("status") in ["matched", "no_match"]
                ]

                fused["matching"] = {
                    "project_id": matching.get("project_id"),
                    "project_name": matching.get("project_name"),
                    "total_jobs_processed": matching.get("total_jobs_processed"),
                    "matched_count": len(
                        [m for m in valid_matches if m.get("status") == "matched"]
                    ),
                    "matches": valid_matches,
                    "status": "included",
                }
                audit.add(
                    "fusion_matching",
                    {
                        "status": "included",
                        "total_jobs": matching.get("total_jobs_processed"),
                        "matched_jobs": len(
                            [m for m in valid_matches if m.get("status") == "matched"]
                        ),
                    },
                )
            else:
                fused["matching"] = {"status": "unavailable"}
                audit.add(
                    "fusion_matching",
                    {"status": "skipped", "reason": "matching_incomplete"},
                )

            # Debug: Log types and values before included_outputs calculation
            grading_val = getattr(state, "grading", None)
            matching_val = getattr(state, "matching", None)
            jd_results_val = getattr(state, "jd_results", None)
            logger.warning(
                f"[FusionAgent] grading type: {type(grading_val)}, value: {repr(grading_val)}"
            )
            logger.warning(
                f"[FusionAgent] matching type: {type(matching_val)}, value: {repr(matching_val)}"
            )
            logger.warning(
                f"[FusionAgent] jd_results type: {type(jd_results_val)}, value: {repr(jd_results_val)}"
            )

            # Add metadata
            included_outputs = sum(
                1
                for v in [
                    getattr(state, "grading", None),
                    getattr(state, "matching", None),
                    getattr(state, "jd_results", None),
                ]
                if isinstance(v, dict) and v.get("status") == "completed"
            )

            final_output = {
                "fused_results": fused,
                "included_outputs": included_outputs,
                "total_outputs": 3,
                "status": "completed",
            }

            audit.add(
                "agent_end",
                {
                    "agent": self.name,
                    "action": "fusion_complete",
                    "included_outputs": included_outputs,
                },
            )

            return AgentResult(
                agent=self.name,
                output=final_output,
                rationale=f"Successfully fused {included_outputs}/3 validated outputs from agents",
            )

        except Exception as e:
            audit.add(
                "agent_error",
                {"agent": self.name, "error": str(e), "action": "fusion_failed"},
            )

            return AgentResult(
                agent=self.name,
                output={"error": str(e), "status": "failed"},
                rationale=f"Fusion failed: {str(e)}",
            )
