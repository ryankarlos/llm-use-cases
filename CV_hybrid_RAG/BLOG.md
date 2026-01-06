# Building an Intelligent CV Matching System with AWS GraphRAG Toolkit

*Learn how to build a graph-enhanced candidate matching system using Amazon Neptune, OpenSearch Serverless, and Amazon Bedrock*

---

## Introduction

Matching candidates to job openings is a common challenge in HR technology. Traditional approaches rely on keyword matching or simple vector similarity, but these methods often miss candidates who have related skills or relevant experience that isn't explicitly stated. 

In this post, we'll show you how to build an intelligent CV matching system using the [AWS GraphRAG Toolkit](https://github.com/awslabs/graphrag-toolkit), which combines the power of knowledge graphs with retrieval-augmented generation (RAG) to find structurally relevant candidates that pure vector search might miss.

## Why Graph-Enhanced RAG?

Consider this scenario: You're looking for a **Machine Learning Engineer** who needs skills in "Deep Learning" and "Model Deployment." A candidate's CV mentions "TensorFlow," "PyTorch," and "MLOps" but doesn't explicitly say "Deep Learning."

**Traditional vector search** might rank this candidate lower because the exact terms don't match.

**Graph-enhanced RAG** understands that TensorFlow and PyTorch are *related to* Deep Learning, and MLOps is *related to* Model Deployment. The graph captures these relationships, enabling the system to find relevant candidates even when exact keywords don't match.

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

## Solution Architecture

Our CV matching system uses three AWS services:

1. **Amazon Neptune** - Graph database storing the lexical graph with entities (skills, experiences) and their relationships
2. **Amazon OpenSearch Serverless** - Vector store for semantic embeddings
3. **Amazon Bedrock** - Foundation models for entity extraction and response generation

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CV Matcher Application                          │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────────┐    ┌─────────────────────────┐  │
│  │  Gradio UI  │───▶│  CV Matcher     │───▶│  GraphRAG Service       │  │
│  │             │    │  Service        │    │  (lexical-graph)        │  │
│  └─────────────┘    └─────────────────┘    └───────────┬─────────────┘  │
└────────────────────────────────────────────────────────┼────────────────┘
                                                         │
                    ┌────────────────────────────────────┼────────────────┐
                    │              AWS Infrastructure    │                │
                    │  ┌─────────────────┐    ┌─────────▼─────────────┐  │
                    │  │ Amazon Neptune  │    │ OpenSearch Serverless │  │
                    │  │ (Graph Store)   │    │ (Vector Store)        │  │
                    │  └─────────────────┘    └───────────────────────┘  │
                    │                                                     │
                    │  ┌─────────────────────────────────────────────┐   │
                    │  │           Amazon Bedrock                     │   │
                    │  │  • Nova Lite (extraction/response)           │   │
                    │  │  • Titan Embeddings v2 (vectors)             │   │
                    │  └─────────────────────────────────────────────┘   │
                    └─────────────────────────────────────────────────────┘
```

## The Lexical Graph Model

The AWS GraphRAG Toolkit uses a three-tier lexical graph model:

### 1. Source Tier
Contains the original documents (CVs, job descriptions) broken into chunks.

### 2. Entity-Relationship Tier
Extracted entities (skills, companies, roles) and their relationships.

### 3. Summarization Tier
Topics, statements, and facts that provide context for retrieval.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Summarization Tier                           │
│  ┌─────────┐    ┌────────────┐    ┌─────────┐                  │
│  │ Topics  │───▶│ Statements │◀───│  Facts  │                  │
│  └─────────┘    └────────────┘    └─────────┘                  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                 Entity-Relationship Tier                        │
│  ┌────────┐    ┌──────────────┐    ┌────────────┐              │
│  │ Skills │───▶│ Relationships│◀───│ Experience │              │
│  └────────┘    └──────────────┘    └────────────┘              │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                      Source Tier                                │
│  ┌───────────┐    ┌────────┐    ┌────────────────┐             │
│  │ Documents │───▶│ Chunks │───▶│ Vector Embeddings│            │
│  └───────────┘    └────────┘    └────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Walkthrough

### Step 1: Deploy Infrastructure with Terraform

First, we deploy the required AWS infrastructure using Terraform:

```hcl
# neptune.tf - Neptune Serverless v2 Cluster
resource "aws_neptune_cluster" "graphrag" {
  cluster_identifier                  = "cv-matcher-neptune-dev"
  engine                              = "neptune"
  engine_version                      = "1.3.1.0"
  iam_database_authentication_enabled = true
  storage_encrypted                   = true

  serverless_v2_scaling_configuration {
    min_capacity = 1.0
    max_capacity = 8.0
  }
}

# oss.tf - OpenSearch Serverless Collection
resource "aws_opensearchserverless_collection" "vectors" {
  name        = "cv-vectors-dev"
  type        = "VECTORSEARCH"
  description = "Vector store for CV matcher GraphRAG"
}
```

Deploy with:

```bash
$ cd terraform
$ terraform init
$ terraform apply

Apply complete! Resources: 14 added, 0 changed, 0 destroyed.

Outputs:
neptune_endpoint = "cv-matcher-neptune-dev.cluster-xxx.us-east-1.neptune.amazonaws.com"
neptune_port = 8182
opensearch_endpoint = "https://xxx.us-east-1.aoss.amazonaws.com"
```

### Step 2: Define the Matching Logic

Our matching algorithm uses a weighted scoring formula:

```python
# cv_matcher.py
def calculate_match_score(self, candidate, job_role) -> float:
    """
    Scoring formula:
    - 50% weight for direct skill matches
    - 30% weight for related skill matches  
    - 20% weight for experience relevance
    """
    direct_score = self._calculate_direct_skill_score(candidate, job_role)
    related_score = self._calculate_related_skill_score(candidate, job_role)
    experience_score = self._calculate_experience_score(candidate, job_role)
    
    return (
        direct_score * 0.50 +
        related_score * 0.30 +
        experience_score * 0.20
    )
```

We also define skill relationships to identify transferable skills:

```python
RELATED_SKILLS = {
    "Python": {"Java", "R", "Scala", "Julia"},
    "Machine Learning": {"Deep Learning", "AI", "Data Science", "Statistics"},
    "TensorFlow": {"PyTorch", "Keras", "Deep Learning"},
    "AWS": {"Azure", "GCP", "Cloud"},
    "Docker": {"Kubernetes", "Containers"},
    "Terraform": {"Infrastructure as Code", "CloudFormation", "Pulumi"},
}
```

### Step 3: Integrate with GraphRAG Toolkit

The GraphRAG service handles indexing and querying:

```python
# graph_rag_service.py
from graphrag_toolkit import LexicalGraphIndex, LexicalGraphQueryEngine
from graphrag_toolkit.storage import NeptuneDatabase, OpenSearchVectorStore

class GraphRAGService:
    def initialize(self):
        # Initialize graph store (Neptune)
        graph_store = NeptuneDatabase(
            endpoint=self.config.neptune_endpoint,
            port=self.config.neptune_port,
            region=self.config.region
        )
        
        # Initialize vector store (OpenSearch Serverless)
        vector_store = OpenSearchVectorStore(
            endpoint=self.config.opensearch_endpoint,
            index_name=self.config.opensearch_index,
            region=self.config.region
        )
        
        # Create the lexical graph index
        self._graph_index = LexicalGraphIndex(
            graph_store=graph_store,
            vector_store=vector_store,
            extraction_model_id="amazon.nova-lite-v1:0",
            embedding_model_id="amazon.titan-embed-text-v2:0"
        )
```

### Step 4: Build the Interactive UI

We use Gradio to create an interactive interface with visualizations:

```python
# app.py
import gradio as gr
import plotly.graph_objects as go

class CVMatcherApp:
    def match_candidates_to_job(self, job_selection):
        # Rank candidates
        matches = self.matcher.rank_candidates(self.candidates, job_role)
        
        # Create bar chart visualization
        fig = go.Figure(data=[
            go.Bar(
                x=[m.candidate_name for m in matches],
                y=[m.match_score for m in matches],
                marker_color=[
                    '#2ecc71' if m.match_score >= 80 else 
                    '#f39c12' if m.match_score >= 50 else 
                    '#e74c3c' 
                    for m in matches
                ]
            )
        ])
        
        return results_df, fig
```

## Running the Demo

### Local Mode (No AWS Required)

Run the demo without AWS infrastructure to test the matching logic:

```bash
$ .venv/Scripts/python.exe -m CV_hybrid_RAG.src.demo --mode demo

============================================================
CV Matching Demo - Using Local Skill-Based Matching
============================================================
Loaded 8 candidates
Available job roles: ['data_scientist', 'data_engineer', 'ml_engineer', 'cloud_architect']

============================================================
Job: Data Scientist
Required Skills: Python, Machine Learning, Statistics, SQL, Data Analysis
Min Experience: 3 years
------------------------------------------------------------
Top Candidates:

  1. Sarah Chen
     Match Score: 100.0%
     Direct Skill Matches: Machine Learning, Python, Data Analysis, SQL, Statistics
     Skill Gaps: None

  2. Lisa Thompson
     Match Score: 60.0%
     Direct Skill Matches: Machine Learning, Statistics, SQL, Python
     Skill Gaps: Data Analysis

  3. Priya Patel
     Match Score: 60.0%
     Direct Skill Matches: Machine Learning, Statistics, Data Analysis, Python
     Skill Gaps: SQL
     Transferable: R
```

### Gradio UI

Launch the interactive UI:

```bash
$ .venv/Scripts/python.exe -m CV_hybrid_RAG.src.app

* Running on local URL:  http://0.0.0.0:7860
```

The UI provides four tabs:

1. **🔍 Match Candidates** - Select a job and see ranked candidates with bar charts
2. **👤 Candidate Details** - View individual profiles with skill distribution pie charts
3. **⚖️ Compare Candidates** - Side-by-side comparison with grouped bar charts
4. **🕸️ Skill Network** - Interactive network graph showing skill relationships

### Running Tests

Verify the implementation with the test suite:

```bash
$ .venv/Scripts/python.exe -m pytest tests/ -v

============================= test session starts =============================
collected 34 items

test_cv_matcher.py::TestCVMatcherService::test_calculate_match_score_perfect PASSED
test_cv_matcher.py::TestCVMatcherService::test_find_direct_skill_matches PASSED
test_cv_matcher.py::TestCVMatcherService::test_find_related_skill_matches PASSED
test_cv_matcher.py::TestCVMatcherService::test_rank_candidates PASSED
test_graph_rag_service.py::TestGraphRAGConfig::test_default_config PASSED
test_graph_rag_service.py::TestGraphRAGService::test_calculate_skill_overlap PASSED
...
============================= 34 passed in 0.42s ==============================
```

## Key Benefits of This Approach

### 1. Beyond Keyword Matching
The graph captures skill relationships, so a candidate with "PyTorch" experience is recognized as relevant for a "Deep Learning" role.

### 2. Explainable Results
Each match includes:
- Direct skill matches
- Related/transferable skills
- Skill gaps
- Experience comparison

### 3. Scalable Architecture
- Neptune Serverless scales automatically based on workload
- OpenSearch Serverless handles vector search at scale
- Bedrock provides on-demand access to foundation models

### 4. Cost-Effective
- Pay only for what you use with serverless components
- No infrastructure management overhead

## Cost Considerations

| Service | Pricing Model | Estimated Cost |
|---------|---------------|----------------|
| Neptune Serverless | NCU-hours | ~$0.10/NCU-hour |
| OpenSearch Serverless | OCU-hours | ~$0.24/OCU-hour |
| Bedrock (Nova Lite) | Input/Output tokens | ~$0.0001/1K tokens |
| Bedrock (Titan Embed) | Input tokens | ~$0.0001/1K tokens |

**Tip:** Use `terraform destroy` when not actively using the infrastructure to minimize costs.

## Extending the Solution

Here are some ways to extend this solution:

1. **Add More Data Sources** - Ingest CVs from S3, parse PDFs with Amazon Textract
2. **Real-time Updates** - Use Amazon EventBridge to trigger re-indexing when new CVs arrive
3. **Multi-language Support** - Use Amazon Translate for international candidates
4. **Interview Scheduling** - Integrate with Amazon Connect for automated outreach

## Clean Up

To avoid ongoing charges, destroy the infrastructure when done:

```bash
$ terraform destroy

Destroy complete! Resources: 14 destroyed.
```

## Conclusion

In this post, we demonstrated how to build an intelligent CV matching system using the AWS GraphRAG Toolkit. By combining knowledge graphs with vector search, we can find relevant candidates that traditional keyword matching would miss.

The key takeaways are:

1. **Graph-enhanced RAG** provides structural relevance beyond semantic similarity
2. **The lexical graph model** captures entities, relationships, and context
3. **Serverless architecture** provides scalability without operational overhead
4. **Explainable results** help recruiters understand why candidates match

Try building your own graph-enhanced RAG application using the [AWS GraphRAG Toolkit](https://github.com/awslabs/graphrag-toolkit)!

---

## References

- [AWS GraphRAG Toolkit](https://github.com/awslabs/graphrag-toolkit)
- [Introducing the GraphRAG Toolkit](https://aws.amazon.com/blogs/database/introducing-the-graphrag-toolkit/)
- [Amazon Neptune Documentation](https://docs.aws.amazon.com/neptune/)
- [Amazon OpenSearch Serverless](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless.html)
- [Amazon Bedrock](https://docs.aws.amazon.com/bedrock/)

---

*About the Author: This blog post was created for educational purposes to demonstrate building graph-enhanced RAG applications on AWS.*
