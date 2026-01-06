# Building an Intelligent CV Matching System with AWS GraphRAG Toolkit

*Learn how to build a graph-enhanced candidate matching system using Amazon Neptune, OpenSearch Serverless, Amazon Bedrock, and AWS Lambda*

---

## Introduction

Recruiting teams face a persistent challenge: finding the right candidates from a growing pool of applicants. Traditional applicant tracking systems rely heavily on keyword matching, which often fails to identify qualified candidates whose resumes use different terminology. A candidate with extensive "PyTorch" and "neural network" experience might be overlooked for a role requiring "Deep Learning" skills, even though these concepts are closely related.

In this post, we demonstrate how to build an intelligent CV matching system that goes beyond simple keyword matching. By leveraging the [AWS GraphRAG Toolkit](https://github.com/awslabs/graphrag-toolkit), we combine knowledge graphs with retrieval-augmented generation (RAG) to understand the relationships between skills, technologies, and experiences. This approach enables the system to identify candidates with transferable skills and relevant experience that traditional search methods would miss.

We will walk through the complete implementation, from infrastructure deployment with Terraform to building a FastAPI application that runs on AWS Lambda. By the end of this post, you will have a working candidate matching system that demonstrates the power of graph-enhanced retrieval.

## The Problem with Traditional Keyword Matching

Consider a common recruiting scenario. Your company needs to hire a Machine Learning Engineer with experience in deep learning and model deployment. You receive hundreds of applications, and your ATS searches for exact keyword matches.

A highly qualified candidate submits their resume with the following skills listed: TensorFlow, PyTorch, Keras, MLOps, Kubernetes, and AWS SageMaker. Notice that the resume never explicitly mentions "Deep Learning" or "Model Deployment" as keywords. A traditional keyword-based system would rank this candidate lower than someone who happens to use those exact phrases, regardless of actual qualifications.

This is where graph-enhanced RAG provides significant value. By building a knowledge graph that captures relationships between concepts, we can understand that TensorFlow, PyTorch, and Keras are all deep learning frameworks. Similarly, MLOps, Kubernetes, and SageMaker are all related to model deployment. The graph structure enables semantic understanding that pure text matching cannot achieve.

```
                    ┌─────────────────┐
                    │  Deep Learning  │
                    └────────┬────────┘
                             │ related_to
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
    ┌───────────┐    ┌───────────┐    ┌───────────┐
    │ TensorFlow│    │  PyTorch  │    │   Keras   │
    └───────────┘    └───────────┘    └───────────┘
```

## Solution Overview

Our CV matching system combines several AWS services into a serverless architecture that scales automatically and minimizes operational overhead. The architecture uses Lambda Function URLs instead of Amazon API Gateway, which simplifies deployment and reduces costs for this demonstration use case.


The core components of our solution include:

**Amazon Neptune** serves as our graph database, storing the lexical graph that captures entities and their relationships. Neptune's serverless configuration automatically scales capacity based on workload, making it ideal for variable traffic patterns common in recruiting applications.

**Amazon OpenSearch Serverless** provides the vector store for semantic embeddings. When candidates and job descriptions are indexed, their text is converted to high-dimensional vectors that capture semantic meaning. This enables similarity search that goes beyond exact keyword matching.

**Amazon Bedrock** powers the intelligence layer of our system. We use Amazon Nova Lite for entity extraction and response generation, and Amazon Titan Embeddings v2 for creating vector representations of text. These foundation models run as managed services, eliminating the need to provision and manage GPU infrastructure.

**AWS Lambda** hosts our application logic in a container-based function. We chose container packaging because the GraphRAG toolkit and its dependencies exceed the 250MB limit for zip-based Lambda deployments. Lambda Function URLs provide a simple HTTPS endpoint without requiring API Gateway configuration.

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

## Understanding the GraphRAG Toolkit

Before diving into implementation, it helps to understand how the AWS GraphRAG Toolkit structures information. The toolkit uses a three-tier lexical graph model that organizes extracted knowledge at different levels of abstraction.

The **Source Tier** contains the original documents broken into manageable chunks. For our CV matching system, this tier stores the raw text from candidate resumes and job descriptions. Each chunk maintains a reference to its source document, enabling traceability when the system returns results.

The **Entity-Relationship Tier** captures the structured knowledge extracted from documents. When the system processes a resume, it identifies entities such as skills (Python, TensorFlow), organizations (previous employers), and roles (Senior Data Scientist). More importantly, it captures relationships between these entities. A candidate "worked at" a company, "has skill" in a technology, and "held role" of a particular title.

The **Summarization Tier** provides higher-level abstractions including topics, statements, and facts. This tier enables the system to answer questions that require synthesizing information across multiple documents or understanding implicit relationships.

For our CV matching use case, we primarily leverage the Entity-Relationship tier to understand skill relationships and the Source tier for retrieving relevant candidate information.


## Prerequisites

To follow along with this tutorial, you will need the following:

- An AWS account with permissions to create Neptune clusters, OpenSearch Serverless collections, Lambda functions, and ECR repositories
- AWS CLI configured with appropriate credentials
- Terraform 1.0 or later installed
- Docker installed for building container images
- Python 3.12 or later for local development

You should also have access to Amazon Bedrock foundation models in your AWS region. Specifically, this tutorial uses Amazon Nova Lite and Amazon Titan Embeddings v2. If you have not already enabled these models, navigate to the Amazon Bedrock console and request access through the Model access page.

## Step 1: Deploying the Infrastructure

We use Terraform to provision all required AWS resources. The infrastructure code is organized into several files, each handling a specific component of the architecture.

First, clone the repository and navigate to the terraform directory:

```bash
git clone https://github.com/ryankarlos/llm-use-cases/cv-hybrid-rag.git
cd llm-use-cases/CV_hybrid_RAG/terraform
```

Before running Terraform, you need to configure the required variables. Create a `terraform.tfvars` file with your specific values:

```hcl
aws_region         = "us-east-1"
env                = "dev"
vpc_id             = "vpc-xxxxxxxxx"
private_subnet_ids = ["subnet-xxxxxxxx", "subnet-yyyyyyyy"]
```

The VPC and subnet configuration is important because Neptune requires VPC connectivity. Your Lambda function will run inside this VPC to access Neptune, and the subnets should have NAT gateway access for reaching OpenSearch Serverless and Bedrock endpoints.

Now initialize and apply the Terraform configuration:

```bash
terraform init
terraform apply
```

Review the planned changes and type `yes` to proceed. The deployment typically takes 10-15 minutes, with Neptune cluster creation being the longest step.

When complete, Terraform outputs the key endpoints you will need:

```
api_endpoint = "https://xxxxxxxxxx.lambda-url.us-east-1.on.aws/"
neptune_endpoint = "cv-matcher-neptune-dev.cluster-xxxxxxxxx.us-east-1.neptune.amazonaws.com"
opensearch_endpoint = "https://xxxxxxxxxx.us-east-1.aoss.amazonaws.com"
ecr_repository_url = "123456789012.dkr.ecr.us-east-1.amazonaws.com/cv-matcher-api-dev"
```

Save these values as you will need them in subsequent steps.

## Step 2: Understanding the Lambda Handler

The heart of our application is the Lambda handler, which implements a FastAPI application wrapped with Mangum for Lambda compatibility. Let us examine the key components.

We chose FastAPI for several reasons. It provides automatic request validation through Pydantic models, generates OpenAPI documentation automatically, and offers clean routing syntax. Mangum is an adapter that translates Lambda events into ASGI requests that FastAPI can process.

Here is the structure of our handler:

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from pydantic import BaseModel

app = FastAPI(title="CV Matcher API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class MatchRequest(BaseModel):
    role_id: str

@app.get("/health")
def health():
    svc = get_graphrag()
    return {
        "status": "healthy",
        "graphrag_enabled": svc._initialized,
        "neptune": NEPTUNE_ENDPOINT,
        "opensearch": OPENSEARCH_ENDPOINT
    }

@app.post("/match")
def match_candidates(req: MatchRequest):
    if req.role_id not in JOB_ROLES:
        raise HTTPException(400, f"Invalid role_id. Available: {list(JOB_ROLES.keys())}")
    
    job = JOB_ROLES[req.role_id]
    results = [calculate_match_score(c, job) for c in CANDIDATES]
    results.sort(key=lambda x: -x["match_score"])
    
    return {"job": job, "matches": results, "graphrag_enabled": get_graphrag()._initialized}

# Mangum adapter converts Lambda events to ASGI
handler = Mangum(app, lifespan="off")
```

The `handler` variable at the bottom is what Lambda invokes. Mangum handles the translation between Lambda's event format and the ASGI protocol that FastAPI expects.


## Step 3: The Matching Algorithm

The candidate matching algorithm uses a weighted scoring formula that considers three factors: direct skill matches, related skill matches, and experience relevance. This approach provides explainable results that recruiters can understand and trust.

The scoring formula assigns weights as follows:
- 50% for direct skill matches
- 30% for related skill matches (transferable skills)
- 20% for experience relevance

Let us examine each component in detail.

**Direct Skill Matching** compares the candidate's listed skills against the job requirements. If a job requires Python, Machine Learning, Statistics, SQL, and Data Analysis, and a candidate has all five skills, they receive a perfect direct match score.

```python
def calculate_match_score(candidate: Dict, job: Dict) -> Dict[str, Any]:
    required = job["required_skills"]
    cand_skills = candidate["skills"]
    cand_lower = {s.lower() for s in cand_skills}
    
    # Direct matches - exact skill matches
    direct = [s for s in required if s.lower() in cand_lower]
    direct_score = (len(direct) / len(required) * 100) if required else 0
```

**Related Skill Matching** is where the graph-enhanced approach provides value. We maintain a mapping of related skills that represent transferable knowledge. When a candidate lacks a required skill but has a related skill, they receive partial credit.

```python
RELATED_SKILLS = {
    "Python": {"Java", "R", "Scala"},
    "Machine Learning": {"Deep Learning", "AI", "Data Science", "Statistics"},
    "Deep Learning": {"Machine Learning", "TensorFlow", "PyTorch"},
    "TensorFlow": {"PyTorch", "Keras", "Deep Learning"},
    "SQL": {"NoSQL", "PostgreSQL", "MySQL"},
    "AWS": {"Azure", "GCP", "Cloud"},
    "Docker": {"Kubernetes", "Containers"},
}

# Related matches - transferable skills
missing = set(required) - set(direct)
related = []
for skill in missing:
    if any(r.lower() in cand_lower for r in RELATED_SKILLS.get(skill, set())):
        related.append(skill)
related_score = (len(related) / len(missing) * 100) if missing else 100
```

For example, if a job requires "Deep Learning" but a candidate only lists "TensorFlow" and "PyTorch," the system recognizes these as related skills and awards partial credit. This prevents qualified candidates from being filtered out due to terminology differences.

**Experience Scoring** considers whether the candidate meets the minimum experience requirement. Candidates who exceed the requirement receive full points, while those with less experience receive proportionally lower scores.

```python
min_exp = job["min_experience_years"]
exp_score = 100.0 if candidate["experience_years"] >= min_exp else (
    (candidate["experience_years"] / min_exp * 100) if min_exp > 0 else 100
)

# Combine scores with weights
total = direct_score * 0.5 + related_score * 0.3 + exp_score * 0.2
```

The final output includes not just the score but also detailed breakdowns that help recruiters understand why a candidate ranked where they did:

```python
return {
    "candidate_id": candidate["id"],
    "candidate_name": candidate["name"],
    "match_score": round(total, 1),
    "direct_matches": direct,
    "related_matches": related,
    "skill_gaps": [s for s in required if s.lower() not in cand_lower],
    "experience_years": candidate["experience_years"]
}
```

This explainability is crucial for building trust in AI-assisted recruiting tools. Recruiters can see exactly which skills matched, which related skills contributed to the score, and what gaps exist.


## Step 4: Building and Deploying the Container

Our Lambda function uses a container image because the GraphRAG toolkit and its dependencies exceed Lambda's 250MB zip deployment limit. The container approach also provides better reproducibility and easier local testing.

The Dockerfile installs the GraphRAG toolkit directly from GitHub along with the required dependencies:

```dockerfile
FROM public.ecr.aws/lambda/python:3.12

# Install dependencies - FastAPI + Mangum for Lambda, GraphRAG toolkit
RUN pip install --no-cache-dir \
    https://github.com/awslabs/graphrag-toolkit/archive/refs/tags/v3.15.0.zip#subdirectory=lexical-graph \
    boto3 \
    opensearch-py \
    fastapi \
    mangum && \
    pip install --no-cache-dir --no-deps llama-index-vector-stores-opensearch

COPY handler.py ${LAMBDA_TASK_ROOT}/

CMD ["handler.handler"]
```

Note that we install `llama-index-vector-stores-opensearch` with `--no-deps` to avoid dependency conflicts with the GraphRAG toolkit's pinned versions.

Build the container image locally:

```bash
cd CV_hybrid_RAG/lambda
docker build -t cv-matcher-api:latest .
```

The build process takes several minutes as it downloads and installs the GraphRAG toolkit and its dependencies, which include spaCy language models and various ML libraries.

Once built, authenticate with ECR and push the image:

```bash
# Get the ECR repository URL from Terraform output
ECR_REPO="123456789012.dkr.ecr.us-east-1.amazonaws.com/cv-matcher-api-dev"

# Authenticate Docker with ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com

# Tag and push
docker tag cv-matcher-api:latest ${ECR_REPO}:latest
docker push ${ECR_REPO}:latest
```

After pushing, update the Lambda function to use the new image:

```bash
aws lambda update-function-code \
  --function-name cv-matcher-api-dev \
  --image-uri ${ECR_REPO}:latest \
  --region us-east-1
```

Wait for the update to complete:

```bash
aws lambda wait function-updated --function-name cv-matcher-api-dev --region us-east-1
```

## Step 5: Testing the API

With the Lambda function deployed, you can test the API using the Function URL. First, verify the health endpoint:

```bash
curl https://xxxxxxxxxx.lambda-url.us-east-1.on.aws/health
```

You should see a response indicating the service is healthy and whether GraphRAG is enabled:

```json
{
  "status": "healthy",
  "graphrag_enabled": true,
  "graphrag_error": null,
  "neptune": "cv-matcher-neptune-dev.cluster-xxxxxxxxx.us-east-1.neptune.amazonaws.com",
  "opensearch": "https://xxxxxxxxxx.us-east-1.aoss.amazonaws.com"
}
```

Next, retrieve the available job roles:

```bash
curl https://xxxxxxxxxx.lambda-url.us-east-1.on.aws/jobs
```

This returns the predefined job roles with their requirements:

```json
{
  "jobs": ["data_scientist", "data_engineer", "ml_engineer", "cloud_architect"],
  "details": {
    "data_scientist": {
      "title": "Data Scientist",
      "required_skills": ["Python", "Machine Learning", "Statistics", "SQL", "Data Analysis"],
      "preferred_skills": ["Deep Learning", "NLP", "TensorFlow", "PyTorch"],
      "min_experience_years": 3
    }
  }
}
```

Now test the matching endpoint:

```bash
curl -X POST https://xxxxxxxxxx.lambda-url.us-east-1.on.aws/match \
  -H "Content-Type: application/json" \
  -d '{"role_id": "data_scientist"}'
```

The response includes ranked candidates with detailed match information:

```json
{
  "job": {
    "role_id": "data_scientist",
    "title": "Data Scientist",
    "required_skills": ["Python", "Machine Learning", "Statistics", "SQL", "Data Analysis"],
    "min_experience_years": 3
  },
  "matches": [
    {
      "candidate_id": "cand_001",
      "candidate_name": "Sarah Chen",
      "match_score": 100.0,
      "direct_matches": ["Python", "Machine Learning", "Statistics", "SQL", "Data Analysis"],
      "related_matches": [],
      "skill_gaps": [],
      "experience_years": 5
    },
    {
      "candidate_id": "cand_005",
      "candidate_name": "Priya Patel",
      "match_score": 60.0,
      "direct_matches": ["Python", "Machine Learning", "Statistics", "Data Analysis"],
      "related_matches": [],
      "skill_gaps": ["SQL"],
      "experience_years": 3
    }
  ],
  "graphrag_enabled": true
}
```

Sarah Chen ranks first with a perfect score because she has all required skills and exceeds the experience requirement. Priya Patel ranks second with a 60% score due to a missing SQL skill.


## Step 6: Running the Gradio Interface

While the API is useful for integration with other systems, we also provide a Gradio-based web interface for interactive exploration. The interface connects to the Lambda Function URL and provides visualizations of match results.

Install the required dependencies:

```bash
cd CV_hybrid_RAG
pip install -r requirements.txt
```

Launch the Gradio application:

```bash
python -m CV_hybrid_RAG.src.app --api-url https://xxxxxxxxxx.lambda-url.us-east-1.on.aws/
```

Open your browser to http://localhost:7860 to access the interface. The application provides four main views:

The **Match Candidates** tab allows you to select a job role and see all candidates ranked by match score. Results are displayed in a table with bar chart and radar chart visualizations. The bar chart shows relative scores across all candidates, while the radar chart compares skill coverage for the top three matches.

The **Candidate Details** tab provides a deep dive into individual candidates. Select a candidate to see their complete profile including a pie chart breakdown of their skills by category (Programming, ML/AI, Data, Cloud).

The **Compare Candidates** tab enables side-by-side comparison of two candidates for a specific role. This is useful when making final hiring decisions between shortlisted candidates.

The **Skill Network** tab visualizes the relationships between skills as an interactive network graph. This helps users understand how the system identifies related and transferable skills.

## Integrating GraphRAG for Enhanced Matching

The implementation we have discussed so far uses a rule-based skill relationship mapping. For production systems with larger skill taxonomies, you can leverage the full GraphRAG toolkit to automatically discover and maintain skill relationships.

The GraphRAG service connects to Neptune and OpenSearch to provide graph-enhanced retrieval:

```python
class GraphRAGService:
    def initialize(self) -> bool:
        try:
            from graphrag_toolkit.lexical_graph import LexicalGraphQueryEngine
            from graphrag_toolkit.lexical_graph.storage import GraphStoreFactory, VectorStoreFactory
            
            # Connect to Neptune for graph storage
            neptune_uri = f"neptune-db://{NEPTUNE_ENDPOINT}"
            self._graph_store = GraphStoreFactory.for_graph_store(neptune_uri)
            
            # Connect to OpenSearch Serverless for vector storage
            oss_uri = f"aoss://{OPENSEARCH_ENDPOINT}"
            self._vector_store = VectorStoreFactory.for_vector_store(oss_uri)
            
            # Create query engine for traversal-based search
            self._query_engine = LexicalGraphQueryEngine.for_traversal_based_search(
     self._graph_store,
                self._vector_store
            )
            
            self._initialized = True
            return True
            
        except Exception as e:
            self._error = str(e)
            return False
```

The engine supports traversal-based search, which follows relationships in the graph to find relevant information. When searching for candidates matching a "Deep Learning" requirement, the engine can traverse relationships to find candidates with TensorFlow, PyTorch, or Keras skills even if they do not explicitly list "Deep Learning."

To populate the graph with candidate data, we provide a local indexing script. This script runs outside of Lambda because the GraphRAG toolkit's extraction pipeline uses Python multiprocessing, which has limitations in the Lambda environment:

```python
# scriptsdidates.py
from graphrag_t.lexical_graph import LexicalGraphIndex
from graphrag_toolkit.lexical_graph.storage import GraphStoreFactory, VectorStoreFactory
from llama_index.core import Document, Settings
from llama_index.llms.bedrock_converse import BedrockConverse
from llama_index.embeddings.bedrock import BedrockEmbedding

# Configure Bedrock models
Settings.llm = BedrockConverse(model="amazon.nova-lite-v1:0", region_name="us-east-1")
Settings.embed_model = BedrockEmbedding(model_name="amazon.titan-embed-text-v2:0", region_name="us-east-1")

# Connect to stores
graph_store = GraphStoreFactory.for_graph_store(f"neptune-db://{NEPTUNE_ENDPOINT}")
vector_store = VectorStoreFactory.for_vector_store(f"aoss://{OPENSEARCH_ENDPOINT}")

# Create index and build graph
graph_index = LexicalGraphIndex(graph_store, vector_store)
graph_index.extract_and_build(documents)
```

The `extract_and_build` method processes documents through the GraphRAG pipeline, extracting entities and relationships using the configured LLM and storing embeddings in the vector store.


## Cost Considerations

Understanding the cost structure helps you plan for production deployments. Our serverless architecture means you pay primarily for actual usage rather than provisioned capacity.

**Amazon Neptune Serverless** charges approximately $0.10 per Neptune Capacity Unit (NCU) hour. The serverless configuration automatically scales between minimum and maximum NCU settings based on workload. For development and testing with light usage, expect costs of $5-15 per day. You can reduce costs by setting a lower maximum NCU or stopping the cluster when not in use.

**Amazon OpenSearch Serverless** charges approximately $0.24 per OpenSearch Compute Unit (OCU) hour. The vector search collection type requires a minimum of 2 OCUs for indexing and 2 OCUs for search, resulting in a baseline cost even with no traffic. For this demonstration, expect approximately $20-25 per day for OpenSearch Serverless.

**AWS Lambda** charges based on invocations and duration. The first 1 million requests per month are free, and you pay $0.20 per additional million requests. Duration charges depend on memory allocation; our 1024MB function costs approximately $0.0000167 per second of execution. For typical API usage patterns, Lambda costs are negligible compared to the database services.

**Lambda Function URLs** are included with Lambda at no additional charge. This is a significant cost advantage over API Gateway, which charges $1.00 per million requests for HTTP APIs.

**Amazon Bedrock** charges per token for model inference. Amazon Nova Lite costs approximately $0.00006 per 1,000 input tokens and $0.00024 per 1,000 output tokens. Amazon Titan Embeddings v2 costs approximately $0.00002 per 1,000 tokens. For the matching operations in this demo, Bedrock costs are minimal since we primarily use pre-computed embeddings.

For development and testing, budget approximately $30-50 per day when resources are running. To minimize costs, run `terraform destroy` when you are not actively using the infrastructure.

## Extending the Solution

This demonstration provides a foundation that you can extend for production use cases. Here are several directions for enhancement:

**Integrate with Document Processing** - Add Amazon Textract to extract text from PDF resumes, enabling automatic ingestion of candidate documents. You could create an S3 bucket trigger that processes new uploads and adds them to the graph.

**Implement Real-time Updates** - Use Amazon EventBridge to trigger re-indexing when candidate profiles change. This keeps the graph current without manual intervention.

**Add Authentication** - For production deployments, configure Lambda Function URL authorization or add Amazon Cognito for user authentication. The current implementation uses `authorization_type = "NONE"` for simplicity.

**Scale the Skill Taxonomy** - Replace the hardcoded skill relationships with a dynamically maintained taxonomy. You could use the GraphRAG toolkit to automatically discover skill relationships from job posting data.

**Add Feedback Loops** - Implement a mechanism for recruiters to provide feedback on match quality. This data can improve the matching algorithm over time through techniques like learning to rank.

## Cleaning Up

To avoid ongoing charges, destroy the infrastructure when you are finished:

```bash
cd CV_hybrid_RAG/terraform
terraform destroy
```

Review the resources to be destroyed and type `yes` to confirm. This removes all AWS resources created by Terraform, including the Neptune cluster, OpenSearch collection, Lambda function, and ECR repository.

Note that Terraform does not delete container images stored in ECR. If you want to remove those as well, delete them manually through the AWS Console or CLI before destroying the ECR repository.

## Conclusion

In this post, we built an intelligent CV matching system that demonstrates the power of combining knowledge graphs with retrieval-augmented generation. By understanding relationships between skills and technologies, the system identifies qualified candidates that traditional keyword matching would overlook.

The key architectural decisions that made this solution effective include:

Using **Lambda Function URLs** instead of API Gateway simplified deployment and reduced costs while still providing a secure HTTPS endpoint for our API.

Choosing **FastAPI with Mangum** gave us clean routing, automatic request validation, and OpenAPI documentation generation, all running efficiently in the Lambda environment.

Implementing **container-based Lambda** allowed us to package the large GraphRAG toolkit dependencies without hitting Lambda's zip deployment limits.

Designing an **explainable scoring algorithm** builds trust with recruiters by showing exactly why candidates ranked where they did, including direct matches, related skills, and gaps.

The AWS GraphRAG Toolkit provides a powerful foundation for building graph-enhanced RAG applications. While we focused on CV matching, the same patterns apply to other use cases such as product recommendations, knowledge management, and research discovery.

We encourage you to deploy this solution in your own AWS account and experiment with extending it for your specific use cases. The combination of serverless infrastructure and foundation models makes it straightforward to build intelligent applications that scale automatically with demand.

---

## References

- [AWS GraphRAG Toolkit on GitHub](https://github.com/awslabs/graphrag-toolkit)
- [Introducing the GraphRAG Toolkit - AWS Database Blog](https://aws.amazon.com/blogs/database/introducing-the-graphrag-toolkit/)
- [Amazon Neptune Documentation](https://docs.aws.amazon.com/neptune/)
- [Amazon OpenSearch Serverless Documentation](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless.html)
- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Lambda Function URLs](https://docs.aws.amazon.com/lambda/latest/dg/lambda-urls.html)
- [Mangum - ASGI Adapter for AWS Lambda](https://mangum.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

*This blog post demonstrates building graph-enhanced RAG applications on AWS. The code and infrastructure templates are provided for educational purposes.*
