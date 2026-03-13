from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field, ConfigDict

from src.schemas.common import AgentResult


class GraphState(BaseModel):
    """LangGraph state for multi-agent orchestration pipeline."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Inputs
    session_id: str
    user_query: str
    task: str = "auto"  # classification|grading|matching|job_description|auto

    # Context identifiers
    project_id: str | None = None
    job_ids: list[str] = Field(default_factory=list)

    # Document processing
    document_extracted: dict[str, Any] = Field(default_factory=dict)
    normalized_text: str = ""

    # Intermediate outputs
    synonyms: dict[str, Any] = Field(default_factory=dict)
    grading: dict[str, Any] = Field(default_factory=dict)
    matching: dict[str, Any] = Field(default_factory=dict)
    jd_results: dict[str, Any] = Field(default_factory=dict)
    validation: dict[str, Any] = Field(default_factory=dict)
    validation_iteration_count: int = 0  # Current iteration index
    validation_max_iterations: int = 3  # Maximum iterations allowed

    # Results
    agent_results: list[AgentResult] = Field(default_factory=list)
    fused: dict[str, Any] = Field(default_factory=dict)
    routing: dict[str, Any] = Field(default_factory=dict)
