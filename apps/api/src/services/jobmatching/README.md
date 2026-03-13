# Job Matching System with Hybrid Search and Reranking

A comprehensive job matching system using MongoDB Atlas Vector Search, full-text search, and reranking for intelligent job recommendations.

## Features

- **Hybrid Search**: Combines vector search (semantic) and full-text search using MongoDB's `$rankFusion`
- **Dual Collection Architecture**: 
  - Job Specialties: Searches spec title + description embeddings
  - Job Aliases: Searches alias titles (expanded from comma-separated values)
- **Reranking**: Uses BGE Reranker for final ranking refinement
- **Full Explainability**: Provides detailed scores (cosine similarity, hybrid scores, reranker scores) with reasoning

## Architecture

```
User Query
    ↓
[Hybrid Search Engine]
    ├── Specialties Collection (Top 20)
    │   ├── Vector Search (embeddings)
    │   └── Full-text Search (spec_title, description)
    └── Aliases Collection (Top 20)
        ├── Vector Search (embeddings)
        └── Full-text Search (alias_title)
    ↓
[Combine & Deduplicate] (Max 40 unique results)
    ↓
[Reranker] (BGE Reranker Large)
    ↓
[Top N Results with Full Explainability]
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure MongoDB Connection

Edit `config.py` and update your MongoDB connection string:

```python
MONGODB_URI = "mongodb+srv://username:password@cluster.mongodb.net/"
```

### 3. Prepare Your Data

Place your Excel file in the project directory with these columns:
- `family code`
- `fam title`
- `sub fam code`
- `sub fam title`
- `spec code`
- `spec title`
- `spec description`
- `alias titles` (comma-separated values)

Update the file path in `config.py`:
```python
INPUT_EXCEL_FILE = "your_job_data.xlsx"
```

## Usage

### Step 1: Data Ingestion

Load data from Excel, create embeddings, and ingest into MongoDB:

```bash
python data_ingestion.py
```

This will:
- Read your Excel file
- Process specialties (combine title + description for embedding)
- Process aliases (expand comma-separated values into rows)
- Create embeddings using BGE-large-en-v1.5
- Ingest into two MongoDB collections

### Step 2: Create Search Indexes

Create vector and full-text search indexes:

```bash
python create_indexes.py
```

This creates:
- `spec_vector_index` - Vector search on specialties embeddings
- `spec_fulltext_index` - Full-text search on specialties
- `alias_vector_index` - Vector search on aliases embeddings
- `alias_fulltext_index` - Full-text search on aliases

**Note**: Index creation may take a few minutes. The script waits until indexes are ready.

### Step 3: Run Job Matching Queries

Search for job matches with full explainability:

```bash
# Basic search
python main.py "data analyst"

# Get top 15 results
python main.py "software engineer" --top-n 15

# Save results to JSON file
python main.py "data analyst" --save results.json

# Suppress console output
python main.py "data analyst" --save results.json --no-display
```

## Output

The system provides comprehensive explainability for each result:

```
RANK #1
============
Spec Code: 12345
Spec Title: Data Analyst
Match Type: Alias Title Match
Matched Text: data analyst

Family Info:
  - Family: Information Technology (IT-001)
  - Sub-Family: Data & Analytics (DA-001)

Scores:
  - Reranker Score: 0.892345
  - Hybrid Combined Score: 0.785621
  - Vector Score (weighted): 0.425000
  - Vector Raw Score (cosine): 0.891234
  - Fulltext Score (weighted): 0.360621
  - Fulltext Raw Score: 3.245678

Reasoning:
  Very strong semantic match (reranker score: 0.8923).
  Stronger vector similarity (cosine: 0.8912) than text match (0.3606).
  Matched through alias: 'data analyst'
```

## Configuration

Key settings in `config.py`:

```python
# Search weights (adjust based on your needs)
VECTOR_WEIGHT = 0.5      # Weight for semantic search
FULLTEXT_WEIGHT = 0.5    # Weight for text search

# Results limits
TOP_K_PER_SEARCH = 20    # Top results from each search
TOTAL_CANDIDATES = 100   # Vector search candidates
FINAL_RESULTS_LIMIT = 10 # Final top results

# Models
EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"
RERANKER_MODEL = "BAAI/bge-reranker-large"
```

## Using Local Models

If you want to use the models from your `model/` folder:

Update `config.py`:
```python
EMBEDDING_MODEL = "c:/Users/richardson-jebasunda/OneDrive - MMC/job solution/model/bge-large-en-v1.5"
RERANKER_MODEL = "c:/Users/richardson-jebasunda/OneDrive - MMC/job solution/model/bge-reranker-large"
```

## Collections Schema

### Job Specialties Collection

```json
{
  "spec_code": "12345",
  "spec_title": "Data Analyst",
  "spec_description": "Analyzes data and creates insights...",
  "family_code": "IT-001",
  "family_title": "Information Technology",
  "sub_family_code": "DA-001",
  "sub_family_title": "Data & Analytics",
  "combined_text": "Data Analyst. Analyzes data and creates insights...",
  "embedding": [0.123, -0.456, ...]  // 1024-dimensional vector
}
```

### Job Aliases Collection

```json
{
  "alias_title": "data analyst",
  "spec_code": "12345",
  "spec_title": "Data Analyst",
  "family_code": "IT-001",
  "family_title": "Information Technology",
  "sub_family_code": "DA-001",
  "sub_family_title": "Data & Analytics",
  "embedding": [0.123, -0.456, ...]  // 1024-dimensional vector
}
```

## Hybrid Search Methodology

The system uses MongoDB's `$rankFusion` to combine:

1. **Vector Search**: Semantic similarity using cosine distance on embeddings
2. **Full-text Search**: Keyword matching with fuzzy search (1 edit distance)

Results are ranked using reciprocal rank fusion:
```
score = weight × (1 / (document_position + 60))
```

## Explainability Scores

Each result includes:

- **Reranker Score**: Cross-encoder similarity (0-1, higher is better)
- **Hybrid Combined Score**: Weighted combination of vector + text
- **Vector Score (weighted)**: Weighted cosine similarity contribution
- **Vector Raw Score**: Raw cosine similarity (0-1)
- **Fulltext Score (weighted)**: Weighted text match contribution
- **Fulltext Raw Score**: Raw text search score

## Troubleshooting

### MongoDB Connection Issues
- Verify your connection string in `config.py`
- Ensure your IP is whitelisted in MongoDB Atlas
- Check database user permissions

### Index Creation Timeout
- Atlas indexes can take several minutes
- The script automatically waits and polls for readiness
- Check Atlas UI to verify index status

### Low Quality Results
- Adjust `VECTOR_WEIGHT` and `FULLTEXT_WEIGHT` in config
- Increase `TOP_K_PER_SEARCH` for more candidates
- Verify embedding model is loaded correctly

### Performance Issues
- Use local model files instead of downloading from HuggingFace
- Reduce `TOTAL_CANDIDATES` for faster vector search
- Consider batching large ingestion jobs

## File Structure

```
job-matching-system/
├── config.py                 # Configuration settings
├── data_ingestion.py         # Data loading and embedding creation
├── create_indexes.py         # MongoDB index creation
├── hybrid_search.py          # Hybrid search implementation
├── reranker_scorer.py        # Reranking and scoring logic
├── main.py                   # Main orchestration script
├── requirements.txt          # Python dependencies
├── README.md                 # This file
└── your_job_data.xlsx        # Input Excel file
```

## Advanced Usage

### Programmatic API

```python
from main import JobMatchingSystem

# Initialize system
system = JobMatchingSystem()
system.initialize()

# Perform search
results, report = system.search_and_rank("data analyst", top_n=10)

# Process results
for result in results:
    print(f"{result['spec_title']}: {result['reranker_score']}")

# Save to file
system.save_results(results, report, "data analyst", "output.json")

# Clean up
system.close()
```

### Batch Processing

```python
queries = ["data analyst", "software engineer", "project manager"]

for query in queries:
    results, report = system.search_and_rank(query, top_n=10)
    system.save_results(results, report, query, f"{query.replace(' ', '_')}.json")
```

## License

MIT

## Support

For issues or questions, please check the code comments or MongoDB Atlas documentation.
