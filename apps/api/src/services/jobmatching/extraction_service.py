"""
Extraction Service for Job Matching
Extracts structured JSON from Resume and Job Description text
"""

from __future__ import annotations
import json
import logging
from typing import Dict, Any, List, Optional
from src.core.audit import AuditTrail

logger = logging.getLogger(__name__)


class ExtractionService:
    """Service to extract structured data from Resume and Job Description text"""

    def __init__(self, agent_instance):
        """
        Initialize extraction service
        
        Args:
            agent_instance: Agent instance that has _llm_generate_with_retry method (e.g., AgentBase)
        """
        self.agent = agent_instance

    async def extract_resume_data(
        self, resume_text: str, audit: Optional[AuditTrail] = None
    ) -> Dict[str, Any]:
        """
        Extract structured data from resume text
        
        Returns:
            {
                "title": str,
                "primary_skills": List[str],
                "secondary_skills": List[str],
                "years_of_experience": float,
                "location": str
            }
        """
        system_prompt = """You are an expert HR data extraction specialist. 
Extract structured information from resume text and return ONLY valid JSON without any markdown formatting or code blocks."""

        prompt = f"""
Extract the following information from the RESUME text below and return a JSON object:

Required fields:
- title: Job title or most recent position title (string)
- primary_skills: List of 5-10 most important technical/professional skills mentioned (array of strings)
- secondary_skills: List of additional relevant skills, tools, or technologies (array of strings, can be empty)
- years_of_experience: Total years of professional experience as a number (float, e.g., 5.5 for 5.5 years)
- location: Preferred work location or current location if mentioned, "Remote" if remote work is preferred (string)

Rules:
- Extract only information explicitly mentioned or clearly inferable
- For years_of_experience, sum up all work experience periods or use the most relevant experience if multiple roles
- If location is not specified, use "Not Specified"
- Skills should be specific (e.g., "Python", "AWS", "Project Management") not generic terms
- Return ONLY the JSON object, no explanations or markdown

RESUME TEXT:
{resume_text}

Return JSON in this exact format:
{{
    "title": "Software Engineer",
    "primary_skills": ["Python", "React", "AWS", "Docker", "Kubernetes"],
    "secondary_skills": ["Git", "CI/CD", "PostgreSQL"],
    "years_of_experience": 5.5,
    "location": "San Francisco, CA"
}}
"""

        try:
            resp = await self.agent._llm_generate_with_retry(
                prompt=prompt,
                system=system_prompt,
                model="mmc-tech-gpt-4o",
                audit=audit,
            )

            # Extract content from response
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
                    logger.warning(f"Failed to extract content from LLM response: {e}")
                    output = str(output)

            # Clean up output - remove markdown code blocks if present
            output_str = str(output).strip()
            if output_str.startswith("```json"):
                output_str = output_str[7:]
            elif output_str.startswith("```"):
                output_str = output_str[3:]
            if output_str.endswith("```"):
                output_str = output_str[:-3]
            output_str = output_str.strip()

            # Parse JSON
            extracted_data = json.loads(output_str)

            # Validate and set defaults
            result = {
                "title": extracted_data.get("title", ""),
                "primary_skills": extracted_data.get("primary_skills", []),
                "secondary_skills": extracted_data.get("secondary_skills", []),
                "years_of_experience": float(extracted_data.get("years_of_experience", 0.0)),
                "location": extracted_data.get("location", "Not Specified"),
            }

            logger.info(f"Successfully extracted resume data: {result.get('title')}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from extraction: {e}. Raw output: {output_str}")
            # Return default structure
            return {
                "title": "",
                "primary_skills": [],
                "secondary_skills": [],
                "years_of_experience": 0.0,
                "location": "Not Specified",
            }
        except Exception as e:
            logger.error(f"Error extracting resume data: {e}", exc_info=True)
            return {
                "title": "",
                "primary_skills": [],
                "secondary_skills": [],
                "years_of_experience": 0.0,
                "location": "Not Specified",
            }

    async def extract_job_description_data(
        self, job_title: str, job_description: str, audit: Optional[AuditTrail] = None
    ) -> Dict[str, Any]:
        """
        Extract structured data from job description text
        
        Returns:
            {
                "title": str,
                "primary_skills": List[str],
                "secondary_skills": List[str],
                "years_of_experience_required": float,
                "location": str,
                "remote_preference": str  # "Remote", "On-site", "Hybrid", "Not Specified"
            }
        """
        system_prompt = """You are an expert HR data extraction specialist. 
Extract structured information from job description text and return ONLY valid JSON without any markdown formatting or code blocks."""

        prompt = f"""
Extract the following information from the JOB DESCRIPTION below and return a JSON object:

Job Title: {job_title}

Required fields:
- title: The job title (use the provided title above)
- primary_skills: List of 5-10 most important required technical/professional skills (array of strings)
- secondary_skills: List of additional nice-to-have skills, tools, or technologies (array of strings, can be empty)
- years_of_experience_required: Required years of experience as specified (float, e.g., 3.0 for "3 years", 5.5 for "5-6 years")
- location: Job location if specified (string)
- remote_preference: Work arrangement - "Remote", "On-site", "Hybrid", or "Not Specified" (string)

Rules:
- Extract only information explicitly mentioned in the job description
- For years_of_experience_required, extract the minimum required experience
- If location mentions "remote", "work from home", "WFH", set remote_preference to "Remote"
- If location mentions "hybrid", "flexible", set remote_preference to "Hybrid"
- If only a location is given without remote options, set remote_preference to "On-site"
- Skills should be specific and technical (e.g., "Python", "AWS", "Agile")
- Return ONLY the JSON object, no explanations or markdown

JOB DESCRIPTION:
{job_description}

Return JSON in this exact format:
{{
    "title": "Senior Software Engineer",
    "primary_skills": ["Python", "React", "AWS", "Docker", "Kubernetes"],
    "secondary_skills": ["GraphQL", "Redis", "MongoDB"],
    "years_of_experience_required": 5.0,
    "location": "San Francisco, CA",
    "remote_preference": "Hybrid"
}}
"""

        try:
            resp = await self.agent._llm_generate_with_retry(
                prompt=prompt,
                system=system_prompt,
                model="mmc-tech-gpt-4o",
                audit=audit,
            )

            # Extract content from response
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
                    logger.warning(f"Failed to extract content from LLM response: {e}")
                    output = str(output)

            # Clean up output - remove markdown code blocks if present
            output_str = str(output).strip()
            if output_str.startswith("```json"):
                output_str = output_str[7:]
            elif output_str.startswith("```"):
                output_str = output_str[3:]
            if output_str.endswith("```"):
                output_str = output_str[:-3]
            output_str = output_str.strip()

            # Parse JSON
            extracted_data = json.loads(output_str)

            # Validate and set defaults
            result = {
                "title": extracted_data.get("title", job_title),
                "primary_skills": extracted_data.get("primary_skills", []),
                "secondary_skills": extracted_data.get("secondary_skills", []),
                "years_of_experience_required": float(
                    extracted_data.get("years_of_experience_required", 0.0)
                ),
                "location": extracted_data.get("location", "Not Specified"),
                "remote_preference": extracted_data.get("remote_preference", "Not Specified"),
            }

            logger.info(f"Successfully extracted job description data: {result.get('title')}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from extraction: {e}. Raw output: {output_str}")
            # Return default structure
            return {
                "title": job_title,
                "primary_skills": [],
                "secondary_skills": [],
                "years_of_experience_required": 0.0,
                "location": "Not Specified",
                "remote_preference": "Not Specified",
            }
        except Exception as e:
            logger.error(f"Error extracting job description data: {e}", exc_info=True)
            return {
                "title": job_title,
                "primary_skills": [],
                "secondary_skills": [],
                "years_of_experience_required": 0.0,
                "location": "Not Specified",
                "remote_preference": "Not Specified",
            }
