"""
Hybrid Semantic Scoring Service for Job Matching
Implements weighted scoring system with semantic similarity
"""

from __future__ import annotations
import logging
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
from src.utils.text_utils import create_embedding

logger = logging.getLogger(__name__)


class HybridSemanticScoringService:
    """Service for hybrid semantic scoring with weighted components"""

    # Weight configuration
    PRIMARY_SKILLS_WEIGHT = 0.6
    EXPERIENCE_WEIGHT = 0.3
    LOCATION_WEIGHT = 0.1

    # Matching threshold
    SCORE_THRESHOLD = 0.7

    def __init__(self):
        """Initialize the scoring service"""
        pass

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors
        
        Args:
            vec1: First embedding vector
            vec2: Second embedding vector
            
        Returns:
            Cosine similarity score between 0 and 1
        """
        try:
            vec1_array = np.array(vec1, dtype=np.float32)
            vec2_array = np.array(vec2, dtype=np.float32)
            
            # Ensure same dimension
            if vec1_array.shape != vec2_array.shape:
                min_dim = min(len(vec1_array), len(vec2_array))
                vec1_array = vec1_array[:min_dim]
                vec2_array = vec2_array[:min_dim]
            
            if vec1_array.size == 0:
                return 0.0
                
            # Normalize vectors
            norm1 = np.linalg.norm(vec1_array)
            norm2 = np.linalg.norm(vec2_array)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            # Calculate cosine similarity
            similarity = float(np.dot(vec1_array, vec2_array) / (norm1 * norm2))
            # Clamp to [0, 1] range
            return max(0.0, min(1.0, similarity))
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}", exc_info=True)
            return 0.0

    def calculate_semantic_similarity(
        self, text1: str, text2: str
    ) -> float:
        """
        Calculate semantic similarity between two texts using embeddings
        
        Args:
            text1: First text (e.g., resume text)
            text2: Second text (e.g., job description)
            
        Returns:
            Semantic similarity score between 0 and 1
        """
        try:
            # Get embeddings for both texts
            # create_embedding returns a list of embeddings (one per input text)
            embeddings1_list = create_embedding(text1)
            embeddings2_list = create_embedding(text2)
            
            # Extract the first embedding from each list (should be single embedding per text)
            embedding1 = embeddings1_list[0] if isinstance(embeddings1_list, list) and len(embeddings1_list) > 0 else embeddings1_list
            embedding2 = embeddings2_list[0] if isinstance(embeddings2_list, list) and len(embeddings2_list) > 0 else embeddings2_list
            
            # Ensure we have lists of floats
            if not isinstance(embedding1, list) or not isinstance(embedding2, list):
                logger.warning(f"Invalid embedding format: embedding1={type(embedding1)}, embedding2={type(embedding2)}")
                return 0.0
            
            # Calculate cosine similarity
            similarity = self.cosine_similarity(embedding1, embedding2)
            
            logger.debug(f"Semantic similarity: {similarity:.4f}")
            return similarity
            
        except Exception as e:
            logger.error(f"Error calculating semantic similarity: {e}", exc_info=True)
            return 0.0

    def calculate_skills_match_score(
        self,
        resume_primary_skills: List[str],
        resume_secondary_skills: List[str],
        job_primary_skills: List[str],
        job_secondary_skills: List[str],
    ) -> float:
        """
        Calculate skills match score based on primary and secondary skills
        
        Args:
            resume_primary_skills: Primary skills from resume
            resume_secondary_skills: Secondary skills from resume
            job_primary_skills: Required primary skills from job
            job_secondary_skills: Desired secondary skills from job
            
        Returns:
            Skills match score between 0 and 1
        """
        if not job_primary_skills:
            return 0.5  # Neutral score if no skills specified
        
        # Normalize skills to lowercase for comparison
        resume_primary_normalized = [s.lower().strip() for s in resume_primary_skills]
        resume_secondary_normalized = [s.lower().strip() for s in resume_secondary_skills]
        job_primary_normalized = [s.lower().strip() for s in job_primary_skills]
        job_secondary_normalized = [s.lower().strip() for s in job_secondary_skills]
        
        # Combine all resume skills (primary weighted higher)
        all_resume_skills = set(resume_primary_normalized + resume_secondary_normalized)
        
        # Calculate primary skills match (most important)
        primary_matches = sum(
            1 for skill in job_primary_normalized if skill in all_resume_skills
        )
        primary_match_ratio = primary_matches / len(job_primary_normalized) if job_primary_normalized else 0.0
        
        # Calculate secondary skills match (bonus)
        secondary_matches = sum(
            1 for skill in job_secondary_normalized if skill in all_resume_skills
        )
        secondary_match_ratio = (
            secondary_matches / len(job_secondary_normalized)
            if job_secondary_normalized
            else 0.0
        )
        
        # Weighted combination: 80% primary, 20% secondary
        skills_score = (primary_match_ratio * 0.8) + (secondary_match_ratio * 0.2)
        
        logger.debug(
            f"Skills match - Primary: {primary_match_ratio:.2f}, Secondary: {secondary_match_ratio:.2f}, "
            f"Total: {skills_score:.4f}"
        )
        
        return max(0.0, min(1.0, skills_score))

    def calculate_experience_match_score(
        self, candidate_years: float, required_years: float
    ) -> float:
        """
        Calculate experience match score ensuring candidate isn't under/overqualified
        
        Args:
            candidate_years: Candidate's years of experience
            required_years: Required years of experience
            
        Returns:
            Experience match score between 0 and 1
            - 1.0: Perfect match (±1 year)
            - 0.8-0.9: Good match (slightly overqualified, within 2 years)
            - 0.6-0.7: Acceptable (underqualified by 1-2 years or overqualified by 3-5 years)
            - 0.3-0.5: Poor match (significantly under/overqualified)
            - 0.0-0.2: Very poor match (extremely under/overqualified)
        """
        if required_years == 0:
            return 0.8  # Neutral-high score if no requirement specified
        
        diff = candidate_years - required_years
        
        # Perfect match: within 1 year
        if abs(diff) <= 1.0:
            return 1.0
        
        # Good match: slightly overqualified (1-2 years more) or slightly underqualified (1-2 years less)
        elif -2.0 <= diff <= 2.0:
            return 0.85
        
        # Acceptable: underqualified by 2-3 years or overqualified by 2-5 years
        elif -3.0 <= diff < -2.0:
            return 0.65  # Underqualified
        elif 2.0 < diff <= 5.0:
            return 0.75  # Overqualified (still valuable)
        
        # Poor: significantly underqualified (3-5 years less)
        elif -5.0 <= diff < -3.0:
            return 0.4
        
        # Very poor: extremely underqualified (>5 years less) or extremely overqualified (>5 years)
        else:
            if diff < -5.0:
                return 0.2  # Very underqualified
            else:
                return 0.3  # Very overqualified (may be a concern but not as bad as underqualified)
        
    def calculate_location_match_score(
        self, candidate_location: str, job_location: str, job_remote_preference: str
    ) -> float:
        """
        Calculate location/remote preference match score
        
        Args:
            candidate_location: Candidate's preferred location
            job_location: Job location
            job_remote_preference: "Remote", "On-site", "Hybrid", or "Not Specified"
            
        Returns:
            Location match score between 0 and 1
        """
        candidate_location_lower = candidate_location.lower()
        job_location_lower = job_location.lower()
        job_remote_lower = job_remote_preference.lower()
        
        # If job is fully remote, high score for anyone (location doesn't matter)
        if job_remote_lower == "remote":
            if "remote" in candidate_location_lower or "not specified" in candidate_location_lower:
                return 1.0
            return 0.9  # Still high score, remote jobs accept anyone
        
        # If job is hybrid, flexible matching
        if job_remote_lower == "hybrid":
            if "remote" in candidate_location_lower or "hybrid" in candidate_location_lower:
                return 1.0
            # Check if locations match or are in same region
            if self._locations_match(candidate_location, job_location):
                return 1.0
            return 0.7
        
        # If job is on-site, check location match
        if job_remote_lower == "on-site" or job_remote_lower == "onsite":
            if self._locations_match(candidate_location, job_location):
                return 1.0
            # Penalize remote-only candidates for on-site jobs
            if "remote" in candidate_location_lower:
                return 0.3
            return 0.5  # Different locations
        
        # Not specified - neutral score
        if job_remote_lower == "not specified":
            return 0.7
        
        # Fallback: try to match locations
        if self._locations_match(candidate_location, job_location):
            return 1.0
        
        return 0.6  # Default neutral score

    def _locations_match(self, loc1: str, loc2: str) -> bool:
        """
        Check if two locations match (fuzzy matching)
        
        Args:
            loc1: First location
            loc2: Second location
            
        Returns:
            True if locations match (same city or "remote" in both)
        """
        loc1_lower = loc1.lower().strip()
        loc2_lower = loc2.lower().strip()
        
        # Check for exact match
        if loc1_lower == loc2_lower:
            return True
        
        # Check for "not specified" or empty
        if "not specified" in loc1_lower or loc1_lower == "":
            return False
        if "not specified" in loc2_lower or loc2_lower == "":
            return False
        
        # Extract city names (simple heuristic - take first part before comma)
        city1 = loc1_lower.split(",")[0].strip()
        city2 = loc2_lower.split(",")[0].strip()
        
        if city1 == city2 and city1:
            return True
        
        # Check if one location contains the other (e.g., "San Francisco, CA" contains "San Francisco")
        if city1 in loc2_lower or city2 in loc1_lower:
            return True
        
        return False

    def calculate_hybrid_score(
        self,
        resume_data: Dict[str, Any],
        job_data: Dict[str, Any],
        resume_text: str,
        job_description_text: str,
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate hybrid semantic score with weighted components
        
        Args:
            resume_data: Extracted resume data (from ExtractionService)
            job_data: Extracted job description data (from ExtractionService)
            resume_text: Full resume text for semantic similarity
            job_description_text: Full job description text for semantic similarity
            
        Returns:
            Tuple of (total_score, breakdown_dict)
            breakdown_dict contains:
                - semantic_similarity: float
                - skills_score: float
                - experience_score: float
                - location_score: float
                - weighted_scores: dict with component scores
        """
        try:
            # 1. Calculate semantic similarity (used as base for overall matching)
            semantic_sim = self.calculate_semantic_similarity(resume_text, job_description_text)
            
            # 2. Calculate skills match score
            skills_score = self.calculate_skills_match_score(
                resume_data.get("primary_skills", []),
                resume_data.get("secondary_skills", []),
                job_data.get("primary_skills", []),
                job_data.get("secondary_skills", []),
            )
            
            # 3. Calculate experience match score
            experience_score = self.calculate_experience_match_score(
                resume_data.get("years_of_experience", 0.0),
                job_data.get("years_of_experience_required", 0.0),
            )
            
            # 4. Calculate location match score
            location_score = self.calculate_location_match_score(
                resume_data.get("location", "Not Specified"),
                job_data.get("location", "Not Specified"),
                job_data.get("remote_preference", "Not Specified"),
            )
            
            # 5. Calculate weighted scores
            # Use semantic similarity to adjust the component scores
            # Higher semantic similarity boosts confidence in extracted data
            
            # Primary skills score (60% weight)
            weighted_skills = skills_score * self.PRIMARY_SKILLS_WEIGHT
            
            # Experience score (30% weight)
            weighted_experience = experience_score * self.EXPERIENCE_WEIGHT
            
            # Location score (10% weight)
            weighted_location = location_score * self.LOCATION_WEIGHT
            
            # Total weighted score
            total_score = weighted_skills + weighted_experience + weighted_location
            
            # Apply semantic similarity as a confidence multiplier
            # If semantic similarity is high, it validates the extracted data
            # If low, we reduce confidence slightly
            if semantic_sim < 0.5:
                total_score *= 0.9  # Reduce score by 10% if semantic similarity is low
            
            # Clamp to [0, 1]
            total_score = max(0.0, min(1.0, total_score))
            
            breakdown = {
                "semantic_similarity": semantic_sim,
                "skills_score": skills_score,
                "experience_score": experience_score,
                "location_score": location_score,
                "weighted_scores": {
                    "skills": weighted_skills,
                    "experience": weighted_experience,
                    "location": weighted_location,
                },
                "total_score": total_score,
            }
            
            logger.info(
                f"Hybrid score calculated: {total_score:.4f} "
                f"(Skills: {skills_score:.2f}, Experience: {experience_score:.2f}, "
                f"Location: {location_score:.2f}, Semantic: {semantic_sim:.2f})"
            )
            
            return total_score, breakdown
            
        except Exception as e:
            logger.error(f"Error calculating hybrid score: {e}", exc_info=True)
            return 0.0, {
                "semantic_similarity": 0.0,
                "skills_score": 0.0,
                "experience_score": 0.0,
                "location_score": 0.0,
                "weighted_scores": {
                    "skills": 0.0,
                    "experience": 0.0,
                    "location": 0.0,
                },
                "total_score": 0.0,
                "error": str(e),
            }

    def filter_by_threshold(
        self, matches: List[Dict[str, Any]], threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter matches by score threshold
        
        Args:
            matches: List of match dictionaries, each containing 'score' or 'total_score'
            threshold: Score threshold (default: SCORE_THRESHOLD = 0.7)
            
        Returns:
            Filtered list of matches above threshold, sorted by score descending
        """
        if threshold is None:
            threshold = self.SCORE_THRESHOLD
        
        filtered = []
        for match in matches:
            score = match.get("score") or match.get("total_score", 0.0)
            if score >= threshold:
                filtered.append(match)
        
        # Sort by score descending
        filtered.sort(key=lambda x: x.get("score") or x.get("total_score", 0.0), reverse=True)
        
        logger.info(f"Filtered {len(matches)} matches to {len(filtered)} above threshold {threshold}")
        return filtered
