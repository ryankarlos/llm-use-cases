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
                       │           Lambda Function (Container)              │
                       │  ┌─────────────────────────────────────────────┐  │
                       │  │  FastAPI + Mangum                           │  │
                       │  │  GraphRAG Service (lexical-graph v3.15.0)   │  │
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

- Python 3.12+, AWS CLI, Docker, Terraform 1.0+

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

### Build and Deploy Lambda

```bash
cd CV_hybrid_RAG/lambda

# Build container
docker build -t cv-matcher-api:latest .

# Push to ECR (after terraform creates the repo)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker tag cv-matcher-api:latest <account>.dkr.ecr.us-east-1.amazonaws.com/cv-matcher-api-dev:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/cv-matcher-api-dev:latest

# Update Lambda
aws lambda update-function-code --function-name cv-matcher-api-dev \
  --image-uri <account>.dkr.ecr.us-east-1.amazonaws.com/cv-matcher-api-dev:latest
```

### Index Candidates (Optional - for GraphRAG)

Run from a Linux/Mac environment or Docker (Windows has path issues with the toolkit):

```bash
# From Docker container with graphrag-toolkit installed
docker run --rm -e NEPTUNE_ENDPOINT=xxx -e OPENSEARCH_ENDPOINT=xxx \
  -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_SESSION_TOKEN \
  cv-matcher-api:latest python scripts/index_candidates.py
```

### Run Gradio UI

```bash
cd CV_hybrid_RAG
pip install -r requirements.txt

# Run with Lambda Function URL
python -m CV_hybrid_RAG.src.app --api-url https://xxx.lambda-url.us-east-1.on.aws/
```

Open http://localhost:7860

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
    {"candidate_name": "Sarah Chen", "match_score": 100.0, "direct_matches": [...], "skill_gaps": []},
    {"candidate_name": "Priya Patel", "match_score": 60.0, "skill_gaps": ["SQL"]}
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
│   └── app.py               # Gradio UI (API client)
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

## Key Features

- **No API Gateway** - Uses Lambda Function URLs (free, simpler)
- **FastAPI + Mangum** - Clean routing, automatic OpenAPI docs at `/docs`
- **Container Lambda** - Handles GraphRAG toolkit's large dependencies
- **Skill-based matching** - Works immediately without graph indexing
- **Graph-enhanced** - Optional GraphRAG for semantic skill relationships

## Cost Considerations

| Service | Pricing | Notes |
|---------|---------|-------|
| Neptune Serverless | ~$0.10/NCU-hour | Scales based on load |
| OpenSearch Serverless | ~$0.24/OCU-hour | Minimum 2 OCUs |
| Lambda | Pay per invocation | First 1M free/month |
| Lambda Function URL | Free | Included with Lambda |

**Tip:** Run `terraform destroy` when not using infrastructure.

## References

- [AWS GraphRAG Toolkit](https://github.com/awslabs/graphrag-toolkit)
- [Lambda Function URLs](https://docs.aws.amazon.com/lambda/latest/dg/lambda-urls.html)
- [Mangum - ASGI adapter for Lambda](https://mangum.io/)
- [Amazon Neptune](https://aws.amazon.com/neptune/)
