from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph, END

from src.clients.core_api import CoreAPIClient
from src.core.audit import AuditTrail
from src.orchestrator.state import GraphState
from src.agents.ingestion import DataIngestionPreprocessAgent
from src.agents.taxonomy import TaxonomySynonymsAgent
from src.agents.job_grading import JobGradingAgent
from src.agents.job_matching import JobMatchingAgent
from src.agents.job_description import JobDescriptionGenerationAgent
from src.agents.validator import ValidatorAgent
from src.agents.feedback import ConversationalFeedbackAgent
from src.agents.explainability import ExplainabilityAuditAgent
from src.agents.fusion import FusionAgent
from src.agents.mercer_workbook_ingestion import MercerWorkbookIngestionAgent


def _infer_route(
    task: str,
    query: str,
    project_id: str | None = None,
    job_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Infer the primary task from explicit task param or keyword matching.

    Args:
        task: Explicit task parameter
        query: User query string
        project_id: Project ID from context
        job_ids: List of job IDs from context

    Returns:
        dict with 'task' and 'reason' keys
    """
    task = (task or "auto").lower()
    if task != "auto":
        return {"task": task, "reason": "explicit_task_param"}

    q = query.lower()

    # Check for ingest operations
    if any(
        k in q for k in ["ingest", "merge workbook", "populate vector", "import mercer"]
    ):
        return {"task": "ingest_mercer", "reason": "keyword"}

    # Check for grading operations
    if any(k in q for k in ["grade", "grading", "ipe", "points"]):
        return {"task": "grading", "reason": "keyword"}

    # Check for matching operations
    if any(
        k in q for k in ["match", "matching", "similar role", "closest role", "catalog"]
    ):
        return {"task": "matching", "reason": "keyword"}

    # Check for job description operations
    if any(k in q for k in ["job description", "jd", "rewrite", "standardize"]):
        return {"task": "job_description", "reason": "keyword"}

    # Infer from context: if project_id or job_ids present, likely matching or grading
    if project_id or job_ids:
        if any(k in q for k in ["match", "matching"]):
            return {"task": "matching", "reason": "context_and_keyword"}
        elif any(k in q for k in ["grade", "grading"]):
            return {"task": "grading", "reason": "context_and_keyword"}
        # Default to matching if context provided but no clear keyword
        return {"task": "matching", "reason": "context_inference"}

    return {"task": "classification", "reason": "default"}


class Orchestrator:
    """Core Agent (Reasoning/Orchestration) implemented as a LangGraph state machine.

    Architecture:
    - Pre-processing pipeline (ingestion → taxonomy → routing)
    - Task-specific agent execution based on routing
    - Fusion layer (validation, quality check, escalation)
    - Post-processing (explainability)
    """

    def __init__(self, core_api: CoreAPIClient, max_iterations: int = 3) -> None:
        self.core_api = core_api
        self.max_iterations = max_iterations
        self.iteration_count = 0
        self.audit = None  # Will be set when run() is called

        self.ingestion = DataIngestionPreprocessAgent(core_api)
        self.taxonomy = TaxonomySynonymsAgent(core_api)
        self.grader = JobGradingAgent(core_api)
        self.matcher = JobMatchingAgent(core_api)
        self.jd = JobDescriptionGenerationAgent(core_api)
        self.validator = ValidatorAgent(core_api)
        self.feedback = ConversationalFeedbackAgent(core_api)
        self.explain = ExplainabilityAuditAgent(core_api)
        self.fusion = FusionAgent(core_api)
        self.mercer_ingestion = MercerWorkbookIngestionAgent(core_api)

        self.graph = self._build()

    def _build(self):
        """Build the LangGraph with task-based routing, agent execution, and fusion-layer validation."""
        g = StateGraph(GraphState)

        # ==================== PRE-PROCESSING NODES ====================
        async def route_node(state: GraphState) -> GraphState:
            """Infer task from user query if not explicit."""
            state.routing = _infer_route(
                state.task, state.user_query, state.project_id, state.job_ids
            )
            return state

        async def ingestion_node(state: GraphState) -> GraphState:
            """Extract and normalize document text."""
            if state.document_extracted:
                res = await self.ingestion.run(state.model_dump(), self.audit)
                state.normalized_text = res.output.get("normalized_text", "")
                state.agent_results.append(res)
            return state

        async def taxonomy_node(state: GraphState) -> GraphState:
            """Extract synonyms and aliases from input."""
            res = await self.taxonomy.run(state.model_dump(), self.audit)
            state.synonyms = res.output.get("synonyms", [])
            # Only append if not already present (prevent duplicates)
            if not any(r.agent == res.agent for r in state.agent_results):
                state.agent_results.append(res)
            return state

        # ==================== TASK-SPECIFIC AGENT NODES ====================
        async def grade_node(state: GraphState) -> GraphState:
            """Execute job grading."""
            res = await self.grader.run(state.model_dump(), self.audit)
            state.grading = res.output
            # Only append if not already present (prevent duplicates)
            if not any(r.agent == res.agent for r in state.agent_results):
                state.agent_results.append(res)
            return state

        async def match_node(state: GraphState) -> GraphState:
            """Execute job matching."""
            state = await self.matcher.run(state, self.audit)
            return state

        async def jd_node(state: GraphState) -> GraphState:
            """Execute job description generation."""
            res = await self.jd.run(state.model_dump(), self.audit)
            state.jd_results = res.output
            # Only append if not already present (prevent duplicates)
            if not any(r.agent == res.agent for r in state.agent_results):
                state.agent_results.append(res)
            return state

        # ==================== VALIDATION NODE ====================
        async def validate_node(state: GraphState) -> GraphState:
            """Validate outputs from executed agents."""
            res = await self.validator.run(state.model_dump(), self.audit)
            state.validation = res.output
            # Only append if not already present (prevent duplicates)
            if not any(r.agent == res.agent for r in state.agent_results):
                state.agent_results.append(res)
            return state

        # ==================== MERCER INGESTION NODE ====================
        async def mercer_ingestion_node(state: GraphState) -> GraphState:
            """Ingest Mercer Workbook into vector store."""
            res = await self.mercer_ingestion.run(state.model_dump(), self.audit)
            state.agent_results.append(res)
            return state

        # ==================== FUSION & VALIDATION NODE ====================
        async def fusion_node(state: GraphState) -> GraphState:
            """Fusion layer: validate results, check quality, and handle escalations."""
            res = await self.fusion.run(state.model_dump(), self.audit)
            state.fused = res.output
            # Only append if not already present (prevent duplicates)
            if not any(r.agent == res.agent for r in state.agent_results):
                state.agent_results.append(res)
            return state

        # ==================== POST-PROCESSING NODES ====================
        async def explain_node(state: GraphState) -> GraphState:
            """Generate explainability audit trail."""
            res = await self.explain.run(state.model_dump(), self.audit)
            # Only append if not already present (prevent duplicates)
            if not any(r.agent == res.agent for r in state.agent_results):
                state.agent_results.append(res)
            return state

        # ==================== CONDITIONAL ROUTING ====================
        def route_to_agent(state: GraphState) -> str:
            """Route to task-specific agent based on classification."""
            task = state.routing.get("task", "execute")

            if task == "ingest_mercer":
                return "mercer_ingestion"
            elif task == "grading":
                return "grade"
            elif task == "matching":
                return "match"
            elif task == "job_description":
                return "jd"
            else:
                # Default: execute all agents
                return "execute"

        def should_continue_escalation(state: GraphState) -> str:
            """Check if validation requires escalation/re-execution or proceeds to fusion.

            Repeats validation loop up to max_iterations if escalation is needed.
            """
            validation = state.validation.get("validation", {})

            # Check if validation indicates escalation is needed
            should_escalate = (
                validation.get("should_escalate", False)
                if isinstance(validation, dict)
                else False
            )

            # Loop back to validation (not agents) for up to max_iterations times
            if (
                should_escalate
                and state.validation_iteration_count < state.validation_max_iterations
            ):
                state.validation_iteration_count += 1
                return "validate"

            # Reset counter and proceed to fusion
            state.validation_iteration_count = 0
            return "fusion"

        # ==================== BUILD GRAPH ====================
        g.add_node("route", route_node)
        g.add_node("ingestion", ingestion_node)
        g.add_node("taxonomy", taxonomy_node)
        g.add_node("grade", grade_node)
        g.add_node("match", match_node)
        g.add_node("jd", jd_node)
        g.add_node("validate", validate_node)
        g.add_node("mercer_ingestion", mercer_ingestion_node)
        g.add_node("fusion", fusion_node)
        g.add_node("explain", explain_node)

        # ==================== EDGES ====================
        g.set_entry_point("route")

        # Pre-processing pipeline
        g.add_edge("route", "ingestion")
        g.add_edge("ingestion", "taxonomy")

        # Route from taxonomy directly to task-specific agent
        g.add_conditional_edges(
            "taxonomy",
            route_to_agent,
            {
                "grade": "grade",
                "match": "match",
                "jd": "jd",
                "mercer_ingestion": "mercer_ingestion",
                "execute": "validate",
            },
        )

        # All agents → validation layer
        g.add_edge("grade", "validate")
        g.add_edge("match", "validate")
        g.add_edge("jd", "validate")
        g.add_edge("mercer_ingestion", "fusion")

        # Validation layer with escalation check
        g.add_conditional_edges(
            "validate",
            should_continue_escalation,
            {"validate": "validate", "fusion": "fusion"},
        )

        # Post-processing
        g.add_edge("fusion", "explain")
        g.add_edge("explain", END)

        return g.compile()

    async def run(self, state: GraphState, audit: AuditTrail) -> GraphState:
        # Store audit trail in orchestrator instance for access by all nodes
        self.audit = audit
        out = await self.graph.ainvoke(state)
        # Convert dict output back to GraphState
        return GraphState(**out) if isinstance(out, dict) else out
