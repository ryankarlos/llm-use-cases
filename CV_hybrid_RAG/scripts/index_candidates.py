"""Local script to index candidates into Neptune graph and OpenSearch vector store.

Run this script locally to populate the GraphRAG stores before using the Lambda API.
Requires graphrag-toolkit: pip install https://github.com/awslabs/graphrag-toolkit/archive/refs/tags/v3.15.0.zip#subdirectory=lexical-graph

Usage:
    python scripts/index_candidates.py
"""

import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration - update these with your endpoints
NEPTUNE_ENDPOINT = os.environ.get("NEPTUNE_ENDPOINT", "cv-matcher-neptune-dev.cluster-cg9we74vymgv.us-east-1.neptune.amazonaws.com")
OPENSEARCH_ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT", "https://tfmcaeijoapbgqt7edc7.us-east-1.aoss.amazonaws.com")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Sample candidates to index
CANDIDATES = [
    {"id": "cand_001", "name": "Sarah Chen", "skills": ["Python", "Machine Learning", "Statistics", "SQL", "TensorFlow", "Deep Learning", "NLP", "Data Analysis"], "experience_years": 5},
    {"id": "cand_002", "name": "Marcus Johnson", "skills": ["Python", "SQL", "ETL", "Data Pipelines", "AWS", "Spark", "Airflow", "Kafka"], "experience_years": 4},
    {"id": "cand_003", "name": "Emily Rodriguez", "skills": ["Python", "Machine Learning", "MLOps", "Docker", "AWS", "Kubernetes", "SageMaker", "MLflow"], "experience_years": 6},
    {"id": "cand_004", "name": "David Kim", "skills": ["AWS", "Cloud Architecture", "Infrastructure as Code", "Security", "Terraform", "Kubernetes", "Networking"], "experience_years": 7},
    {"id": "cand_005", "name": "Priya Patel", "skills": ["Python", "Machine Learning", "Statistics", "R", "Data Analysis", "Computer Vision"], "experience_years": 3},
    {"id": "cand_006", "name": "James Wilson", "skills": ["Python", "SQL", "AWS", "Docker", "ETL", "dbt", "Snowflake"], "experience_years": 2},
    {"id": "cand_007", "name": "Lisa Thompson", "skills": ["Python", "Machine Learning", "Deep Learning", "PyTorch", "NLP", "Statistics", "SQL"], "experience_years": 4},
    {"id": "cand_008", "name": "Ahmed Hassan", "skills": ["AWS", "Azure", "Cloud Architecture", "Security", "Networking", "Serverless"], "experience_years": 5},
]


def main():
    """Index candidates into GraphRAG stores."""
    try:
        from graphrag_toolkit.lexical_graph import LexicalGraphIndex
        from graphrag_toolkit.lexical_graph.storage import GraphStoreFactory, VectorStoreFactory
        from llama_index.core import Document, Settings
        from llama_index.llms.bedrock_converse import BedrockConverse
        from llama_index.embeddings.bedrock import BedrockEmbedding
    except ImportError as e:
        logger.error(f"Missing dependencies: {e}")
        logger.info("Install with: pip install https://github.com/awslabs/graphrag-toolkit/archive/refs/tags/v3.15.0.zip#subdirectory=lexical-graph")
        return

    logger.info("Configuring Bedrock LLM and embeddings...")
    llm = BedrockConverse(model="amazon.nova-lite-v1:0", region_name=AWS_REGION)
    embed_model = BedrockEmbedding(model_name="amazon.titan-embed-text-v2:0", region_name=AWS_REGION)
    Settings.llm = llm
    Settings.embed_model = embed_model

    logger.info(f"Connecting to Neptune: {NEPTUNE_ENDPOINT}")
    graph_store = GraphStoreFactory.for_graph_store(f"neptune-db://{NEPTUNE_ENDPOINT}")

    logger.info(f"Connecting to OpenSearch: {OPENSEARCH_ENDPOINT}")
    vector_store = VectorStoreFactory.for_vector_store(f"aoss://{OPENSEARCH_ENDPOINT}")

    logger.info("Creating LexicalGraphIndex...")
    graph_index = LexicalGraphIndex(graph_store, vector_store)

    # Convert candidates to documents
    docs = []
    for c in CANDIDATES:
        content = f"""Candidate: {c['name']}
Skills: {', '.join(c['skills'])}
Experience: {c['experience_years']} years
"""
        doc = Document(
            text=content,
            metadata={
                "candidate_id": c["id"],
                "candidate_name": c["name"],
                "skills": ",".join(c["skills"]),
                "experience_years": c["experience_years"],
                "doc_type": "cv"
            }
        )
        docs.append(doc)
        logger.info(f"Prepared document for: {c['name']}")

    logger.info(f"Indexing {len(docs)} candidates...")
    graph_index.extract_and_build(docs)

    logger.info("Indexing complete!")
    logger.info(f"Neptune endpoint: {NEPTUNE_ENDPOINT}")
    logger.info(f"OpenSearch endpoint: {OPENSEARCH_ENDPOINT}")


if __name__ == "__main__":
    main()
