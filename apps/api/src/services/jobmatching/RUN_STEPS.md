# How to Run Hybrid Semantic Scoring System

## Quick Start Guide

### Step 1: Environment Setup

Ensure you have the required environment variables set in your `.env` file:

```bash
# Required for API calls
CORE_API_BASE_URL=https://your-api-url.com
CORE_API_KEY=your-api-key-here

# Required for database operations (if using)
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/
MONGODB_DATABASE=your_database_name

# Optional: Embedding API configuration
EMBEDDINGS_BASE_URL=https://stg1.mmc-bedford-int-non-prod-ingress.mgti.mmc.com/coreapi/llm/embeddings/v1
EMBEDDINGS_MODEL=mmc-tech-text-embedding-3-large
```

### Step 2: Install Dependencies

Dependencies are already in `requirements.txt`. If needed, reinstall:

```bash
cd apps/api
pip install -r requirements.txt
```

Required packages (already included):
- `numpy` - for vector calculations
- `requests` - for API calls
- `pydantic` - for data validation
- `pymongo` or `motor` - for database operations

### Step 3: Run the Example Script

#### Option A: Run Direct Scoring Example (No API Required)

This example demonstrates the scoring logic without making API calls:

```bash
cd apps/api
python -m src.services.jobmatching.example_hybrid_scoring
```

Expected output:
```
================================================================================
HYBRID SEMANTIC SCORING - EXAMPLE SCRIPT
================================================================================

Running examples...

================================================================================
EXAMPLE: Direct Scoring with Pre-extracted Data
================================================================================

Total Score: 0.8234
Meets Threshold (>=0.7): True
...
```

#### Option B: Run Full Resume-to-Job Matching (Requires API)

Uncomment the last line in `example_hybrid_scoring.py`:

```python
# Uncomment this line:
asyncio.run(example_resume_to_job_matching())
```

Then run:

```bash
cd apps/api
python -m src.services.jobmatching.example_hybrid_scoring
```

### Step 4: Integrate into Your Application

#### Using the Job Matching Agent

The hybrid scoring is already integrated into the `JobMatchingAgent`. Use it like this:

```python
from src.agents.job_matching import JobMatchingAgent
from src.clients.core_api import CoreAPIClient
from src.core.audit import AuditTrail
from src.core.config import settings

# Initialize
core_api = CoreAPIClient(
    base_url=settings.core_api_base_url,
    api_key=settings.core_api_key,
)
agent = JobMatchingAgent(core_api)
audit = AuditTrail()

# Match resume to job
result = await agent.match_resume_to_job(
    resume_text="Your resume text here...",
    job_title="Senior Software Engineer",
    job_description="Job description text here...",
    audit=audit,
)

# Check results
if result['match']:
    print(f"✓ Match found! Score: {result['total_score']:.4f}")
    print(f"  Skills: {result['score_breakdown']['skills_score']:.2f}")
    print(f"  Experience: {result['score_breakdown']['experience_score']:.2f}")
    print(f"  Location: {result['score_breakdown']['location_score']:.2f}")
else:
    print(f"✗ No match (Score: {result['total_score']:.4f}, Threshold: {result['threshold']})")
```

#### Using Services Directly

```python
from src.services.jobmatching.extraction_service import ExtractionService
from src.services.jobmatching.hybrid_semantic_scoring import HybridSemanticScoringService

# Initialize services
extraction_service = ExtractionService(agent_instance)  # agent_instance must have _llm_generate_with_retry
scoring_service = HybridSemanticScoringService()

# Extract structured data
resume_data = await extraction_service.extract_resume_data(resume_text, audit)
job_data = await extraction_service.extract_job_description_data(
    job_title, job_description, audit
)

# Calculate hybrid score
total_score, breakdown = scoring_service.calculate_hybrid_score(
    resume_data=resume_data,
    job_data=job_data,
    resume_text=resume_text,
    job_description_text=job_description,
)

# Filter by threshold
if total_score >= 0.7:
    print(f"Match! Score: {total_score:.4f}")
else:
    print(f"Below threshold. Score: {total_score:.4f}")
```

## Running Tests

### Run Unit Tests

Create a test file `test_hybrid_scoring.py`:

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
    assert score > 0.5  # Should have good match

def test_experience_matching():
    service = HybridSemanticScoringService()
    # Perfect match
    assert service.calculate_experience_match_score(5.0, 5.0) == 1.0
    # Good match
    assert service.calculate_experience_match_score(6.0, 5.0) >= 0.8

def test_threshold_filtering():
    service = HybridSemanticScoringService()
    matches = [
        {"score": 0.85, "job_id": "1"},
        {"score": 0.65, "job_id": "2"},
        {"score": 0.75, "job_id": "3"},
    ]
    filtered = service.filter_by_threshold(matches, threshold=0.7)
    assert len(filtered) == 2
    assert all(m["score"] >= 0.7 for m in filtered)
```

Run tests:

```bash
cd apps/api
pytest src/tests/services/jobmatching/test_hybrid_scoring.py -v
```

## Running with Real Data

### Example: Match Multiple Resumes to a Job

```python
import asyncio
from src.agents.job_matching import JobMatchingAgent
from src.core.audit import AuditTrail

async def match_multiple_resumes():
    agent = JobMatchingAgent(core_api)
    audit = AuditTrail()
    
    job_title = "Senior Software Engineer"
    job_description = "..."  # Your job description
    
    resumes = [
        "Resume 1 text...",
        "Resume 2 text...",
        "Resume 3 text...",
    ]
    
    results = []
    for resume_text in resumes:
        result = await agent.match_resume_to_job(
            resume_text=resume_text,
            job_title=job_title,
            job_description=job_description,
            audit=audit,
        )
        results.append({
            "resume_index": len(results),
            "match": result["match"],
            "score": result["total_score"],
            "breakdown": result["score_breakdown"],
        })
    
    # Sort by score
    results.sort(key=lambda x: x["score"], reverse=True)
    
    # Print top matches
    print("Top Matches:")
    for i, result in enumerate(results[:5], 1):
        if result["match"]:
            print(f"{i}. Resume {result['resume_index']}: {result['score']:.4f}")

asyncio.run(match_multiple_resumes())
```

### Example: Batch Processing

```python
import asyncio
from src.services.jobmatching.hybrid_semantic_scoring import HybridSemanticScoringService

async def batch_match(resumes, jobs):
    """Match multiple resumes against multiple jobs"""
    service = HybridSemanticScoringService()
    all_matches = []
    
    for resume in resumes:
        for job in jobs:
            # Extract and score (simplified - in reality you'd use extraction service)
            score, breakdown = service.calculate_hybrid_score(...)
            
            if score >= 0.7:
                all_matches.append({
                    "resume_id": resume["id"],
                    "job_id": job["id"],
                    "score": score,
                    "breakdown": breakdown,
                })
    
    # Sort by score
    all_matches.sort(key=lambda x: x["score"], reverse=True)
    return all_matches
```

## Configuration

### Adjust Scoring Weights

Edit `apps/api/src/services/jobmatching/hybrid_semantic_scoring.py`:

```python
class HybridSemanticScoringService:
    # Change these values to adjust importance
    PRIMARY_SKILLS_WEIGHT = 0.6  # Default: 0.6 (60%)
    EXPERIENCE_WEIGHT = 0.3       # Default: 0.3 (30%)
    LOCATION_WEIGHT = 0.1         # Default: 0.1 (10%)
    SCORE_THRESHOLD = 0.7         # Default: 0.7
```

**Important**: Weights should sum to 1.0 for proper normalization.

### Adjust Threshold

```python
# In your code
scoring_service = HybridSemanticScoringService()
scoring_service.SCORE_THRESHOLD = 0.75  # Higher threshold = stricter filtering

# Or when filtering
filtered = scoring_service.filter_by_threshold(matches, threshold=0.8)
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'src'"

**Solution**: Make sure you're running from the correct directory:

```bash
cd apps/api
python -m src.services.jobmatching.example_hybrid_scoring
```

Or set PYTHONPATH:

```bash
export PYTHONPATH="${PYTHONPATH}:/path/to/apps/api"
python src/services/jobmatching/example_hybrid_scoring.py
```

### Issue: "API Error" or "Connection Refused"

**Solution**: 
1. Check your `.env` file has correct `CORE_API_BASE_URL` and `CORE_API_KEY`
2. Verify network connectivity
3. Check API endpoint is accessible: `curl $CORE_API_BASE_URL/health`

### Issue: "Low scores" or "No matches above threshold"

**Solutions**:
1. Lower threshold temporarily: `SCORE_THRESHOLD = 0.6`
2. Check extracted data quality - review logs for extraction results
3. Verify resume/job description text is complete and well-formatted
4. Ensure skills are clearly stated in both resume and job description

### Issue: "Embedding API timeout"

**Solution**:
1. Check embedding API endpoint is accessible
2. Reduce batch size if processing multiple items
3. Add retry logic (already included in some cases)
4. Consider caching embeddings for frequently used text

## Performance Tips

1. **Cache Embeddings**: Cache embeddings for frequently matched job descriptions
2. **Batch Processing**: Process multiple matches in parallel (with rate limiting)
3. **Threshold Early**: Filter low-scoring candidates before expensive operations
4. **Extract Once**: Extract structured data once and reuse for multiple matches

## Next Steps

1. **Review Results**: Check match quality and adjust weights/threshold as needed
2. **Monitor Performance**: Track match rates and scores over time
3. **Gather Feedback**: Collect feedback on match quality to fine-tune weights
4. **Scale Up**: Integrate into production job matching pipeline

For more details, see `HYBRID_SCORING_README.md`.
