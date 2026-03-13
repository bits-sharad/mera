"""
Example script demonstrating Hybrid Semantic Scoring for Job Matching

This script shows how to use the new hybrid semantic scoring system
to match resumes to job descriptions.
"""

import asyncio
import logging
from typing import Dict, Any
import sys
import os

# Add parent directory to path to import from src
# This allows running the script from different locations
current_dir = os.path.dirname(os.path.abspath(__file__))
api_src_dir = os.path.join(current_dir, '../../../')
sys.path.insert(0, os.path.abspath(api_src_dir))

from src.clients.core_api import CoreAPIClient
from src.core.audit import AuditTrail
from src.agents.job_matching import JobMatchingAgent
from src.services.jobmatching.extraction_service import ExtractionService
from src.services.jobmatching.hybrid_semantic_scoring import HybridSemanticScoringService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def example_resume_to_job_matching():
    """
    Example: Match a resume to a job description using hybrid semantic scoring
    """
    # Example resume text
    resume_text = """
    John Doe
    Software Engineer
    
    Experience:
    - Senior Software Engineer at Tech Corp (2019-Present, 5 years)
      • Developed scalable web applications using Python, React, and AWS
      • Led a team of 3 engineers
      • Implemented CI/CD pipelines with Docker and Kubernetes
      • Built RESTful APIs and microservices architecture
    
    - Software Engineer at StartupXYZ (2017-2019, 2 years)
      • Full-stack development using Python, JavaScript, PostgreSQL
      • Agile development methodologies
    
    Skills:
    Primary: Python, React, AWS, Docker, Kubernetes, RESTful APIs, Microservices
    Secondary: Git, CI/CD, PostgreSQL, JavaScript, Agile, Project Management
    
    Location: San Francisco, CA (Open to Remote)
    """
    
    # Example job description
    job_title = "Senior Full Stack Engineer"
    job_description = """
    We are looking for a Senior Full Stack Engineer to join our growing team.
    
    Requirements:
    - 5+ years of experience in software development
    - Strong experience with Python and React
    - Experience with cloud platforms (AWS preferred)
    - Knowledge of containerization (Docker, Kubernetes)
    - Experience with microservices architecture
    - Strong problem-solving skills
    
    Preferred:
    - Experience with CI/CD pipelines
    - Knowledge of PostgreSQL
    - Agile development experience
    
    Location: San Francisco, CA (Hybrid - 3 days in office)
    """
    
    # Initialize the agent (requires core_api client)
    # Note: In production, this would be initialized with actual CoreAPIClient
    # For testing, you may need to mock this or use a test configuration
    try:
        from src.core.config import settings
        
        # Initialize core API client
        core_api = CoreAPIClient(
            base_url=settings.core_api_base_url,
            api_key=settings.core_api_key,
        )
        
        # Create job matching agent
        agent = JobMatchingAgent(core_api)
        
        # Create audit trail
        audit = AuditTrail()
        
        # Match resume to job
        logger.info("=" * 80)
        logger.info("EXAMPLE: Matching Resume to Job Description")
        logger.info("=" * 80)
        logger.info(f"\nResume Summary: {resume_text[:200]}...")
        logger.info(f"\nJob Title: {job_title}")
        logger.info(f"\nJob Description Summary: {job_description[:200]}...")
        logger.info("\n" + "=" * 80)
        
        result = await agent.match_resume_to_job(
            resume_text=resume_text,
            job_title=job_title,
            job_description=job_description,
            audit=audit,
        )
        
        # Display results
        print("\n" + "=" * 80)
        print("MATCHING RESULTS")
        print("=" * 80)
        print(f"\nMatch Status: {'✓ MATCH' if result.get('match') else '✗ NO MATCH'}")
        print(f"Total Score: {result.get('total_score', 0.0):.4f}")
        print(f"Threshold: {result.get('threshold', 0.7)}")
        
        if result.get('score_breakdown'):
            breakdown = result['score_breakdown']
            print("\n" + "-" * 80)
            print("SCORE BREAKDOWN")
            print("-" * 80)
            print(f"Semantic Similarity: {breakdown.get('semantic_similarity', 0.0):.4f}")
            print(f"\nComponent Scores:")
            print(f"  Primary Skills Match: {breakdown.get('skills_score', 0.0):.4f} (Weight: 0.6)")
            print(f"  Experience Match: {breakdown.get('experience_score', 0.0):.4f} (Weight: 0.3)")
            print(f"  Location Match: {breakdown.get('location_score', 0.0):.4f} (Weight: 0.1)")
            
            weighted = breakdown.get('weighted_scores', {})
            print(f"\nWeighted Scores:")
            print(f"  Skills: {weighted.get('skills', 0.0):.4f}")
            print(f"  Experience: {weighted.get('experience', 0.0):.4f}")
            print(f"  Location: {weighted.get('location', 0.0):.4f}")
        
        if result.get('resume_data'):
            print("\n" + "-" * 80)
            print("EXTRACTED RESUME DATA")
            print("-" * 80)
            resume_data = result['resume_data']
            print(f"Title: {resume_data.get('title', 'N/A')}")
            print(f"Primary Skills: {', '.join(resume_data.get('primary_skills', []))}")
            print(f"Secondary Skills: {', '.join(resume_data.get('secondary_skills', []))}")
            print(f"Years of Experience: {resume_data.get('years_of_experience', 0.0)}")
            print(f"Location: {resume_data.get('location', 'N/A')}")
        
        if result.get('job_data'):
            print("\n" + "-" * 80)
            print("EXTRACTED JOB DATA")
            print("-" * 80)
            job_data = result['job_data']
            print(f"Title: {job_data.get('title', 'N/A')}")
            print(f"Primary Skills: {', '.join(job_data.get('primary_skills', []))}")
            print(f"Secondary Skills: {', '.join(job_data.get('secondary_skills', []))}")
            print(f"Years Required: {job_data.get('years_of_experience_required', 0.0)}")
            print(f"Location: {job_data.get('location', 'N/A')}")
            print(f"Remote Preference: {job_data.get('remote_preference', 'N/A')}")
        
        print("\n" + "=" * 80)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in example: {e}", exc_info=True)
        print(f"\nERROR: {e}")
        print("\nNote: Make sure you have configured:")
        print("  - CORE_API_BASE_URL")
        print("  - CORE_API_KEY")
        print("  - MongoDB connection settings")
        return None


async def example_direct_scoring():
    """
    Example: Use scoring service directly with extracted data
    """
    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE: Direct Scoring with Pre-extracted Data")
    logger.info("=" * 80)
    
    # Example extracted data
    resume_data = {
        "title": "Software Engineer",
        "primary_skills": ["Python", "React", "AWS", "Docker", "Kubernetes"],
        "secondary_skills": ["Git", "CI/CD", "PostgreSQL"],
        "years_of_experience": 5.5,
        "location": "San Francisco, CA",
    }
    
    job_data = {
        "title": "Senior Full Stack Engineer",
        "primary_skills": ["Python", "React", "AWS", "Docker", "Kubernetes"],
        "secondary_skills": ["GraphQL", "Redis", "MongoDB"],
        "years_of_experience_required": 5.0,
        "location": "San Francisco, CA",
        "remote_preference": "Hybrid",
    }
    
    resume_text = "Software Engineer with 5+ years experience in Python, React, AWS, Docker, Kubernetes"
    job_description = "Senior Full Stack Engineer position requiring Python, React, AWS experience"
    
    scoring_service = HybridSemanticScoringService()
    
    score, breakdown = scoring_service.calculate_hybrid_score(
        resume_data=resume_data,
        job_data=job_data,
        resume_text=resume_text,
        job_description_text=job_description,
    )
    
    print(f"\nTotal Score: {score:.4f}")
    print(f"Meets Threshold (>={scoring_service.SCORE_THRESHOLD}): {score >= scoring_service.SCORE_THRESHOLD}")
    print(f"\nBreakdown: {breakdown}")
    
    return score, breakdown


if __name__ == "__main__":
    print("=" * 80)
    print("HYBRID SEMANTIC SCORING - EXAMPLE SCRIPT")
    print("=" * 80)
    print("\nThis script demonstrates the Hybrid Semantic Scoring system for job matching.")
    print("\nRunning examples...\n")
    
    # Run direct scoring example (doesn't require API)
    asyncio.run(example_direct_scoring())
    
    # Run full resume-to-job matching (requires API configuration)
    # Uncomment the line below if you have API credentials configured
    # asyncio.run(example_resume_to_job_matching())
