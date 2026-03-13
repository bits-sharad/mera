from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from src.agents.base import AgentBase
from src.core.audit import AuditTrail
from src.orchestrator.state import GraphState
from src.schemas.common import AgentResult
from src.services.mjl.mjl_job_matching import MJLJobMatching
from src.services.mjl.search.context_search import SearchInput, retrieve_and_rank
from src.utility.job_families_taxonomy import JobFamilyService

logger = logging.getLogger(__name__)

VALIDATOR_SYSTEM = """You are a validation specialist for job processing results.
Evaluate the quality and completeness of agent outputs.
Return JSON with keys: is_valid (bool), quality_score (0-1), issues (list), recommendations (list), should_escalate (bool), rationale.
"""


class ValidatorAgent(AgentBase):
    name = "validator"

    async def run(self, state: GraphState, audit: AuditTrail) -> AgentResult:
        """
        Validate outputs from grade, match, and jd agents.
        Processes each job in matching results separately.
        Uses LLM prompt for validation of alignment between specialization,
        organization context, additional instructions, job family, subfamily,
        and refined job description.
        """
        audit.add("agent_start", {"agent": self.name})

        grading = getattr(state, "grading", {})
        matching = getattr(state, "matching", {})
        jd_results = getattr(state, "jd_results", {})

        matches = matching.get("matches", [])
        if not matches:
            logger.warning("No matches found in matching results")
            audit.add(
                "agent_end",
                {
                    "agent": self.name,
                    "output": {
                        "validation": {
                            "is_valid": True,
                            "quality_score": 0,
                            "issues": ["No matches to validate"],
                        }
                    },
                },
            )
            return AgentResult(
                agent=self.name,
                output={
                    "validation": {
                        "is_valid": True,
                        "quality_score": 0,
                        "issues": ["No matches to validate"],
                    }
                },
                rationale="No matches to validate",
            )

        all_validations = []
        for idx, job_match in enumerate(matches):
            max_retries = 5
            retry_count = 0
            job_id = job_match.get("job_id", "unknown")
            job_title = job_match.get("job_title", "unknown")
            search_input: SearchInput = job_match.get("search_input", {})
            is_valid = False
            job_family_codes = []
            additional_instructions = ""
            rationale = ""
            validation_result = None
            recommendations = []
            issues = []

            while not is_valid and retry_count < max_retries:
                specialization_llm = getattr(search_input, "specialization", "")
                rationale += getattr(search_input, "rationale", "")
                org_context = getattr(search_input, "project_description", "")
                additional_instructions += getattr(
                    search_input, "Additional_instructions", ""
                )
                job_family_codes.append(getattr(search_input, "job_family_codes", []))
                job_sub_families = getattr(search_input, "job_sub_families", [])
                refined_job_description = getattr(search_input, "job_description", "")
                specialization_db = job_match["matched"]["candidates"][0].get(
                    "specializationDescription", ""
                )
                original_prompt = getattr(search_input, "prompt", "")

                # Extract numeric part from subfamily codes for validation
                subfamily_numeric = [
                    s.split("-")[-1] for s in job_sub_families if isinstance(s, str)
                ]

                validation_prompt = f"""
You are a validation specialist for job processing results. Your task is to check the alignment between the LLM-generated specialization and the matched specialization from the database.
Indicate any issues or discrepancies between these specializations, and provide a clear assessment of whether the match is valid or invalid.
Return JSON with keys: is_valid (bool), quality_score (0-1), issues (list), recommendations (list), should_escalate (bool), rationale.

Job info:
    job_id: {job_id}
    job_title: {job_title}
    specialization_llm: {specialization_llm}
    specialization_db: {specialization_db}
    org_context: {org_context}
    additional_instructions: {additional_instructions}
    rationale: {rationale}
    job_family_codes: {job_family_codes}
    job_sub_families: {subfamily_numeric}
    refined_job_description: {refined_job_description}
"""

                resp = await self._llm_generate_with_retry(
                    prompt=validation_prompt,
                    system=VALIDATOR_SYSTEM,
                    model="mmc-tech-gpt-4o",
                    audit=audit,
                )
                output = resp.get("output") or resp
                if isinstance(output, dict) and "choices" in output:
                    try:
                        content = (
                            output.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content", "")
                        )
                        output = content
                    except (IndexError, KeyError) as e:
                        logger.warning(
                            f"Failed to extract content from LLM response: {e}"
                        )
                        output = str(output)
                if isinstance(output, dict):
                    output = output.get("validation", str(output))

                try:
                    # Strip markdown code fence if present
                    output_str = f"{output}".strip()
                    if output_str.startswith("```"):
                        output_str = (
                            output_str.split("\n", 1)[1]
                            if "\n" in output_str
                            else output_str
                        )
                        if output_str.endswith("```"):
                            output_str = output_str[:-3]
                        output_str = output_str.strip()

                    validation_result = json.loads(output_str)
                except Exception as e:
                    logger.warning(
                        f"Failed to parse validation result for job {job_id}: {e}"
                    )
                    validation_result = {
                        "is_valid": False,
                        "quality_score": 0,
                        "issues": ["LLM validation failed or returned invalid JSON"],
                        "recommendations": [],
                        "should_escalate": True,
                        "rationale": "LLM validation failed or returned invalid JSON",
                    }

                is_valid = validation_result.get("is_valid", False)
                retry_count += 1
                if not is_valid and retry_count < max_retries:
                    rationale += validation_result.get("rationale", "")
                    issues.append(validation_result.get("issues", []))
                    mitigation_prompt = f"""
You are a HR Specialist working on a job matching use-case. Original selected job family code has failed the validation for following reasons:
{rationale}.
Founded issues: {issues}.

**Using the original prompt context and instructions, select a new job family(other than:{getattr(search_input, "job_family_codes", [])}) from the original prompt that best mitigates the issues found in validation and aligned with context and job family instructions.
** Do not repeat the same mistakes from the previous selection.
** Do not select a job family/subfamily that is the same as the previous selection.
** Do not select a job family that is not in the original prompt.

Return JSON with keys: job_family_code, job_sub_family_code, rationale.
"""
                    print(state)
                    state.project_id = getattr(state, "project_id", "unknown")
                    state.job_ids = [{"job_id": job_id, "feedback": mitigation_prompt}]
                    ret = await MJLJobMatching(self.core_api).match(state, audit)
                    job_match["matched"] = ret.matching["matches"][0]["matched"]

                all_validations.append(
                    {
                        "job_id": job_id,
                        "job_title": job_title,
                        "validation": validation_result,
                    }
                )

                audit.add(
                    "job_validated",
                    {
                        "job_id": job_id,
                        "job_title": job_title,
                        "status": "validated",
                    },
                )

                is_valid = all(
                    v["validation"].get("is_valid", False) for v in all_validations
                )
                quality_score = (
                    min(
                        [
                            v["validation"].get("quality_score", 0)
                            for v in all_validations
                        ]
                    )
                    if all_validations
                    else 0
                )
                issues.append(
                    [
                        issue
                        for v in all_validations
                        for issue in v["validation"].get("issues", [])
                    ]
                )
                recommendations.append(
                    [
                        rec
                        for v in all_validations
                        for rec in v["validation"].get("recommendations", [])
                    ]
                )
                should_escalate = any(
                    v["validation"].get("should_escalate", False)
                    for v in all_validations
                )

                audit.add(
                    "agent_end",
                    {"agent": self.name, "total_jobs_validated": len(matches)},
                )

                # Compose explicit status and rationale
                status = "valid" if is_valid else "invalid"
                rationale += f" Validation status: {status}. "
                if not is_valid:
                    rationale += (
                        " " + "; ".join(issues)
                        if issues
                        else "No explicit reason provided."
                    )
                    # If invalid, prompt LLM to select new job family/subfamily mitigating the issues
                    job_id = job_match.get("job_id", "unknown")
                    job_title = job_match.get("job_title", "unknown")
                    search_input: SearchInput = job_match.get("search_input", {})
                    refined_job_description = getattr(
                        search_input, "job_description", ""
                    )
                    org_context = getattr(search_input, "project_description", "")
                    additional_instructions += getattr(
                        search_input, "Additional_instructions", ""
                    )
                    original_prompt = getattr(search_input, "prompt", "")
                    mitigation_prompt = f"""
You are a HR Specialist working on a job matching use-case. Original selected job family code has failed the validation for following reasons:
{rationale}.

**Using the original prompt context and instructions, select a new job family(other than:{getattr(search_input, "job_family_codes", [])}) from the original prompt that best mitigates the issues found in validation and aligned with context and job family instructions.
** Do not repeat the same mistakes from the previous selection.
** Do not select a job family/subfamily that is the same as the previous selection.
** Do not select a job family that is not in the original prompt.

Return JSON with keys: job_family_code, job_sub_family_code, rationale.
"""
                    print(state)
                    state.project_id = getattr(state, "project_id", "unknown")
                    state.job_ids = [{"job_id": job_id, "feedback": mitigation_prompt}]
                    ret = await MJLJobMatching(self.core_api).match(state, audit)
                    job_match["matched"] = ret.matching["matches"][0]["matched"]

        return AgentResult(
            agent=self.name,
            output={
                "validation": {
                    "jobs": all_validations,
                    "is_valid": is_valid,
                    "status": status,
                    "quality_score": round(quality_score, 2),
                    "issues": issues,
                    "recommendations": recommendations,
                    "should_escalate": should_escalate,
                    "rationale": rationale,
                    "mitigation": [
                        m.get("mitigation") for m in matches if m.get("mitigation")
                    ]
                    if not is_valid
                    else None,
                }
            },
            rationale=rationale,
        )
