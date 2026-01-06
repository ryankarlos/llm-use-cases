# CV Hybrid RAG - GraphRAG Toolkit Integration

CV matching system using AWS GraphRAG Toolkit's [lexical-graph](https://github.com/awslabs/graphrag-toolkit/tree/main/lexical-graph) for intelligent candidate-to-job matching.

## Overview

This project demonstrates how to use graph-enhanced RAG for CV matching:

1. **Local Skill-Based Matching**: Fast, rule-based matching using skill overlap and experience
2. **Graph-Enhanced Matching**: Uses lexical graph to find structurally relevant candidates beyond semantic similarity

The lexical graph model provides three tiers:
- **Source tier**: Documents and chunks
- **Entity-relationship tier**: Extracted skills, experiences, and their relationships  
- **Summarization tier**: Topics, statements, and facts

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   CVs / Jobs    │────▶│  LexicalGraph    │────▶│ Neptune Database│
│   (Documents)   │     │  Index           │     │ (Graph Store)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌──────────────────┐
                        │ OpenSearch       │
                        │ (Vector Store)   │
                        └──────────────────┘
                                │
                                ▼
┌─────────────────┐     ┌──────────────────┐
│   Query         │────▶│ LexicalGraph     │────▶ Matched Candidates
│   (Job Req)     │     │ QueryEngine      │     with explanations
└─────────────────┘     └──────────────────┘
```

## Quick Start

### Demo Mode (No AWS Required)

```bash
cd CV_hybrid_RAG
pip install -r requirements.txt
python -m src.demo --mode demo
```

### Live Mode (With AWS Infrastructure)

1. Deploy infrastructure:
```bash
cd terraform
terraform init
terraform apply
```

2. Install GraphRAG toolkit:
```bash
pip install "graphrag-toolkit-lexical-graph @ git+https://github.com/awslabs/graphrag-toolkit.git#subdirectory=lexical-graph"
```

3. Set environment variables:
```bash
export NEPTUNE_ENDPOINT="your-neptune-endpoint"
export OPENSEARCH_ENDPOINT="your-opensearch-endpoint"
export AWS_REGION="us-east-1"
```

4. Run with live infrastructure:
```bash
python -m src.demo --mode live
```

## Project Structure

```
CV_hybrid_RAG/
├── src/
│   ├── __init__.py
│   ├── cv_matcher.py        # Local skill-based matching
│   ├── graph_rag_service.py # GraphRAG toolkit integration
│   ├── job_roles.py         # Job role definitions
│   ├── models.py            # Data models
│   └── demo.py              # Demo script
├── data/
│   └── sample_cvs.json      # Sample candidate data
├── terraform/
│   ├── knowledge_base.tf    # OpenSearch + Bedrock KB
│   ├── neptune.tf           # Neptune for graph store
│   ├── variables.tf
│   └── output.tf
├── tests/
└── requirements.txt
```

## Usage Examples

### Index CVs and Jobs

```python
from src import GraphRAGService, GraphRAGConfig, CVDocument, JobDocument

# Initialize service
config = GraphRAGConfig.from_env()
service = GraphRAGService(config)
service.initialize()

# Index a CV
cv = CVDocument(
    candidate_id="cand_001",
    candidate_name="Sarah Chen",
    content="Senior Data Scientist with 5 years experience...",
    skills=["Python", "Machine Learning", "TensorFlow"],
    experience_years=5
)
service.index_cv(cv)

# Index a job
job = JobDocument(
    job_id="ds_001",
    title="Data Scientist",
    content="Looking for experienced data scientist...",
    required_skills=["Python", "Machine Learning", "SQL"],
    min_experience_years=3
)
service.index_job(job)
```

### Find Matching Candidates

```python
# Find candidates for a job using graph-enhanced retrieval
results = service.find_candidates_for_job(job, top_k=5)

for result in results:
    print(f"{result.candidate_name}: {result.match_score:.1f}%")
    print(f"  Matched entities: {result.matched_entities}")
```

### Hybrid Matching

```python
from src import CVMatcherService, CandidateProfile

# Local skill-based matching
matcher = CVMatcherService()
candidates = [...]  # List of CandidateProfile

local_matches = matcher.rank_candidates(candidates, job_role)

# Combine with graph results for hybrid scoring
```

## AWS Services Used

- **Amazon Neptune**: Graph database for lexical graph storage
- **Amazon OpenSearch Serverless**: Vector store for embeddings
- **Amazon Bedrock**: LLM for entity extraction and response generation
  - Claude 3 Sonnet: Entity extraction
  - Titan Embeddings v2: Vector embeddings

## References

- [AWS GraphRAG Toolkit](https://github.com/awslabs/graphrag-toolkit)
- [Introducing the GraphRAG Toolkit](https://aws.amazon.com/blogs/database/introducing-the-graphrag-toolkit/)
- [lexical-graph Documentation](https://github.com/awslabs/graphrag-toolkit/tree/main/lexical-graph)
