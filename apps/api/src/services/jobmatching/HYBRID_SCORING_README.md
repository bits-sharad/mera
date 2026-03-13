# Hybrid Semantic Scoring System for Job Matching

## Overview

This system implements a **Hybrid Semantic Scoring** strategy for job matching that significantly improves matching accuracy by combining:

1. **Structured Data Extraction**: Extracts key information from resumes and job descriptions
2. **Semantic Similarity**: Uses embeddings to compare text similarity
3. **Weighted Scoring**: Combines multiple factors with specific weights
4. **Threshold Filtering**: Only returns high-quality matches above a threshold

## Architecture

```
Resume/Job Description Text
    ↓
[Extraction Layer]
    ├── Title
    ├── Primary Skills
    ├── Secondary Skills
    ├── Years of Experience
    └── Location/Remote Preference
    ↓
[Hybrid Semantic Scoring]
    ├── Semantic Similarity (text embeddings)
    ├── Skills Match Score (60% weight)
    ├── Experience Match Score (30% weight)
    └── Location Match Score (10% weight)
    ↓
[Threshold Filtering] (Score > 0.7)
    ↓
[Filtered Matches]
```

## Components

### 1. Extraction Service (`extraction_service.py`)

Extracts structured JSON from both Resume and Job Description text:

**Resume Extraction:**
- `title`: Job title or most recent position
- `primary_skills`: List of 5-10 most important technical/professional skills
- `secondary_skills`: Additional relevant skills, tools, or technologies
- `years_of_experience`: Total years of professional experience (float)
- `location`: Preferred work location or "Remote"

**Job Description Extraction:**
- `title`: Job title
- `primary_skills`: List of 5-10 required technical/professional skills
- `secondary_skills`: Nice-to-have skills
- `years_of_experience_required`: Required years of experience (float)
- `location`: Job location
- `remote_preference`: "Remote", "On-site", "Hybrid", or "Not Specified"

### 2. Hybrid Semantic Scoring Service (`hybrid_semantic_scoring.py`)

Implements the weighted scoring system:

#### Scoring Weights:
- **Primary Skills Match**: 0.6 (60%)
- **Experience Level Match**: 0.3 (30%)
- **Location/Remote Preference**: 0.1 (10%)

#### Features:
- **Semantic Similarity**: Uses `text-embedding-3-large` (via MMC API) to compare resume and job description text
- **Skills Matching**: Calculates overlap between required and candidate skills (primary skills weighted higher)
- **Experience Matching**: Ensures candidate isn't significantly under/overqualified
  - Perfect match: ±1 year = 1.0
  - Good match: ±2 years = 0.85
  - Acceptable: 2-3 years difference = 0.65-0.75
  - Poor: >3 years difference = 0.2-0.4
- **Location Matching**: Matches location preferences with remote/on-site/hybrid options

#### Threshold:
- **Default Threshold**: 0.7
- Only matches with score ≥ 0.7 are returned
- Matches are sorted by score descending

## Usage

### Option 1: Use via Job Matching Agent (Recommended)

The `JobMatchingAgent` now includes hybrid semantic scoring automatically when matching jobs:

```python
from src.agents.job_matching import JobMatchingAgent
from src.core.audit import AuditTrail

# Initialize agent
agent = JobMatchingAgent(core_api)
audit = AuditTrail()

# Match resume to job
result = await agent.match_resume_to_job(
    resume_text="...",
    job_title="Senior Software Engineer",
    job_description="...",
    audit=audit,
)

if result['match']:
    print(f"Match found! Score: {result['total_score']:.4f}")
    print(f"Breakdown: {result['score_breakdown']}")
```

### Option 2: Use Services Directly

```python
from src.services.jobmatching.extraction_service import ExtractionService
from src.services.jobmatching.hybrid_semantic_scoring import HybridSemanticScoringService

# Initialize services
extraction_service = ExtractionService(agent_instance)
scoring_service = HybridSemanticScoringService()

# Extract data
resume_data = await extraction_service.extract_resume_data(resume_text, audit)
job_data = await extraction_service.extract_job_description_data(job_title, job_description, audit)

# Calculate score
score, breakdown = scoring_service.calculate_hybrid_score(
    resume_data=resume_data,
    job_data=job_data,
    resume_text=resume_text,
    job_description_text=job_description,
)

# Filter by threshold
if score >= 0.7:
    print(f"Match! Score: {score:.4f}")
```

## Running the Example

### Prerequisites

1. **Environment Variables**: Set up your `.env` file with:
   ```bash
   CORE_API_BASE_URL=your_api_url
   CORE_API_KEY=your_api_key
   MONGODB_URI=your_mongodb_uri
   ```

2. **Install Dependencies**: Already included in `requirements.txt`
   - `numpy`
   - `requests`
   - `pydantic`
   - (others already in project)

### Run the Example Script

```bash
# Navigate to the API directory
cd apps/api

# Run the example (direct scoring - no API needed)
python -m src.services.jobmatching.example_hybrid_scoring

# Or run with full API integration (requires credentials)
python -m src.services.jobmatching.example_hybrid_scoring
```

### Expected Output

```
================================================================================
HYBRID SEMANTIC SCORING - EXAMPLE SCRIPT
================================================================================

================================================================================
EXAMPLE: Direct Scoring with Pre-extracted Data
================================================================================

Total Score: 0.8234
Meets Threshold (>=0.7): True

Breakdown: {
    'semantic_similarity': 0.9123,
    'skills_score': 0.9000,
    'experience_score': 1.0000,
    'location_score': 1.0000,
    'weighted_scores': {
        'skills': 0.5400,
        'experience': 0.3000,
        'location': 0.1000
    },
    'total_score': 0.8234
}
```

## Integration with Existing Job Matching

The hybrid semantic scoring is automatically integrated into the existing job matching flow:

1. **Job Description Processing**: When processing jobs, structured data is extracted
2. **Candidate Enhancement**: Vector search results are enhanced with hybrid scores
3. **Threshold Filtering**: Only candidates above 0.7 threshold are returned
4. **Improved Ranking**: Results are re-ranked by hybrid score

## Configuration

### Adjusting Weights

Edit `apps/api/src/services/jobmatching/hybrid_semantic_scoring.py`:

```python
class HybridSemanticScoringService:
    PRIMARY_SKILLS_WEIGHT = 0.6  # Change to adjust skills importance
    EXPERIENCE_WEIGHT = 0.3       # Change to adjust experience importance
    LOCATION_WEIGHT = 0.1         # Change to adjust location importance
    SCORE_THRESHOLD = 0.7         # Change to adjust filtering threshold
```

### Changing Embedding Model

The system uses `text-embedding-3-large` via the MMC API. To change:

1. Update `apps/api/src/utils/text_utils.py` - `create_embedding()` function
2. Or modify the URL/model in `HybridSemanticScoringService.calculate_semantic_similarity()`

## Accuracy Improvements

The hybrid semantic scoring system improves matching accuracy by:

1. **Structured Extraction**: Reduces noise by focusing on key attributes
2. **Multi-factor Scoring**: Considers skills, experience, and location together
3. **Semantic Understanding**: Uses embeddings to understand context beyond keywords
4. **Threshold Filtering**: Eliminates low-quality matches automatically
5. **Weighted Importance**: Prioritizes most important factors (skills > experience > location)

## Testing

### Unit Tests

Create tests in `apps/api/src/tests/services/jobmatching/`:

```python
import pytest
from src.services.jobmatching.hybrid_semantic_scoring import HybridSemanticScoringService

def test_skills_matching():
    service = HybridSemanticScoringService()
    score = service.calculate_skills_match_score(
        resume_primary_skills=["Python", "React", "AWS"],
        resume_secondary_skills=["Git"],
        job_primary_skills=["Python", "React", "AWS", "Docker"],
        job_secondary_skills=["Kubernetes"],
    )
    assert 0.0 <= score <= 1.0

def test_experience_matching():
    service = HybridSemanticScoringService()
    # Perfect match
    assert service.calculate_experience_match_score(5.0, 5.0) == 1.0
    # Slightly overqualified
    assert 0.8 <= service.calculate_experience_match_score(6.0, 5.0) <= 1.0
```

### Integration Tests

Test the full flow:

```python
@pytest.mark.asyncio
async def test_resume_to_job_matching():
    agent = JobMatchingAgent(mock_core_api)
    result = await agent.match_resume_to_job(
        resume_text="...",
        job_title="...",
        job_description="...",
        audit=AuditTrail(),
    )
    assert "match" in result
    assert "total_score" in result
    assert result["total_score"] >= 0.0
```

## Troubleshooting

### Common Issues

1. **Low Scores**: 
   - Check if skills are being extracted correctly
   - Verify experience years are numeric
   - Ensure location/remote preferences are set

2. **API Errors**:
   - Verify `CORE_API_BASE_URL` and `CORE_API_KEY` are set
   - Check network connectivity
   - Review API rate limits

3. **Embedding Errors**:
   - Verify embedding API endpoint is accessible
   - Check API key permissions
   - Ensure text is not empty

4. **No Matches Above Threshold**:
   - Consider lowering threshold temporarily for debugging
   - Check extracted data quality
   - Verify job/resume content is sufficient

## Future Enhancements

Potential improvements:

1. **Secondary Skills Weighting**: Currently secondary skills have less weight - could be tuned
2. **Industry Matching**: Add industry-specific matching logic
3. **Education Matching**: Include education requirements in scoring
4. **Salary Range Matching**: Consider salary expectations
5. **Soft Skills**: Extract and match soft skills separately
6. **Learning**: Incorporate feedback from successful matches to improve weights

## Support

For questions or issues, refer to:
- Main project README: `apps/api/README.md`
- Job Matching Service README: `apps/api/src/services/jobmatching/README.md`
