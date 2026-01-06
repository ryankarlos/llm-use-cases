# CV Hybrid RAG - GraphRAG Toolkit for Candidate Matching

An intelligent CV-to-job matching system using AWS GraphRAG Toolkit's [lexical-graph](https://github.com/awslabs/graphrag-toolkit/tree/main/lexical-graph) for graph-enhanced retrieval augmented generation.

## Architecture

```
┌─────────────────┐     ┌──────────────────────────────────────────────────┐
│   Gradio UI     │────▶│         Lambda Function URL                      │
│   (app.py)      │     │  (FastAPI + Mangum - no API Gateway needed)      │
└─────────────────┘     └──────────────────────┬───────────────────────────┘
                                               │
                       ┌───────────────────────────────────────────────────┐
                       │                Lambda Function                     │
                       │  ┌─────────────────────────────────────────────┐  │
                       │  │  GraphRAG Service (lexical-graph)           │  │
                       │  │  • Skill-based matching (fallback)          │  │
                       │  │  • Graph-enhanced retrieval (when indexed)  │  │
                       │  └─────────────────────────────────────────────┘  │
                       └───────────────────────┬───────────────────────────┘
                                               │
          ┌────────────────────────────────────┼────────────────────────────┐
          │                                    │                            │
          ▼                                    ▼                            ▼
┌─────────────────┐              ┌─────────────────────┐        ┌──────────────────┐
│ Amazon Neptune  │              │ OpenSearch          │        │ Amazon Bedrock   │
│ Serverless v2   │              │ Serverless          │        │ • Nova Lite      │
│ (Graph Store)   │              │ (Vector Store)      │        │ • Titan Embed v2 │
└─────────────────┘              └─────────────────────┘        └──────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.12+, [uv](https://docs.astral.sh/uv/), AWS CLI, Terraform 1.0+

### Deploy Infrastructure

```bash
cd CV_hybrid_RAG/terraform
terraform init
terraform apply
```

**Outputs:**
```
api_endpoint = "https://xxx.lambda-url.us-east-1.on.aws/"
neptune_endpoint = "cv-matcher-neptune-dev.cluster-xxx.us-east-1.neptune.amazonaws.com"
opensearch_endpoint = "https://xxx.us-east-1.aoss.amazonaws.com"
```

### Index Candidates (Local Script)

Run locally to populate Neptune graph and OpenSearch vectors:

```bash
cd CV_hybrid_RAG
uv venv .venv
uv pip install -r requirements.txt --python .venv/Scripts/python.exe

# Set endpoints and run indexing
export NEPTUNE_ENDPOINT="cv-matcher-neptune-dev.cluster-xxx.us-east-1.neptune.amazonaws.com"
export OPENSEARCH_ENDPOINT="https://xxx.us-east-1.aoss.amazonaws.com"
.venv/Scripts/python.exe scripts/index_candidates.py
```

### Run Gradio UI

```bash
# Run with Lambda Function URL
.venv/Scripts/python.exe -m CV_hybrid_RAG.src.app --api-url https://xxx.lambda-url.us-east-1.on.aws/
```

Open http://localhost:7860

### Run Tests

```bash
.venv/Scripts/python.exe -m pytest tests/ -v
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with GraphRAG status |
| `/jobs` | GET | List available job roles |
| `/candidates` | GET | List all candidates |
| `/match` | POST | Match candidates to job role |
| `/compare` | POST | Compare two candidates |

### Example: Match Candidates

```bash
curl -X POST https://xxx.lambda-url.us-east-1.on.aws/match \
  -H "Content-Type: application/json" \
  -d '{"role_id": "data_scientist"}'
```

**Response:**
```json
{
  "job": {"role_id": "data_scientist", "title": "Data Scientist", ...},
  "matches": [
    {"candidate_name": "Sarah Chen", "match_score": 100.0, ...},
    {"candidate_name": "Priya Patel", "match_score": 60.0, ...}
  ],
  "graphrag_enabled": true
}
```

## Scoring Formula

- **50%** - Direct skill matches
- **30%** - Related skill matches (transferable skills)
- **20%** - Experience relevance

## Project Structure

```
CV_hybrid_RAG/
├── src/
│   └── app.py               # Gradio UI (API-only mode)
├── lambda/
│   ├── handler.py           # FastAPI + Mangum Lambda handler
│   ├── Dockerfile           # Container with GraphRAG toolkit
│   └── requirements.txt
├── scripts/
│   └── index_candidates.py  # Local script to populate graph/vectors
├── terraform/
│   ├── lambda_api.tf        # Lambda + Function URL
│   ├── neptune.tf           # Neptune Serverless v2
│   ├── oss.tf               # OpenSearch Serverless
│   └── output.tf
├── tests/
│   └── test_lambda_handler.py
└── requirements.txt
```

## GraphRAG Integration

The Lambda handler includes GraphRAG service integration using AWS GraphRAG Toolkit:

```python
from graphrag_toolkit.lexical_graph import LexicalGraphQueryEngine
from graphrag_toolkit.lexical_graph.storage import GraphStoreFactory, VectorStoreFactory

# Connect to Neptune and OpenSearch
graph_store = GraphStoreFactory.for_graph_store(f"neptune-db://{NEPTUNE_ENDPOINT}")
vector_store = VectorStoreFactory.for_vector_store(f"aoss://{OPENSEARCH_ENDPOINT}")

# Query with graph-enhanced retrieval
query_engine = LexicalGraphQueryEngine.for_traversal_based_search(graph_store, vector_store)
```

## Cost Considerations

| Service | Pricing |
|---------|---------|
| Neptune Serverless | ~$0.10/NCU-hour |
| OpenSearch Serverless | ~$0.24/OCU-hour |
| Lambda | Pay per invocation |
| Lambda Function URL | Free (included with Lambda) |

**Tip:** Run `terraform destroy` when not using infrastructure.

## References

- [AWS GraphRAG Toolkit](https://github.com/awslabs/graphrag-toolkit)
- [Introducing the GraphRAG Toolkit](https://aws.amazon.com/blogs/database/introducing-the-graphrag-toolkit/)
- [Amazon Neptune](https://aws.amazon.com/neptune/)
- [Amazon Bedrock](https://aws.amazon.com/bedrock/)
