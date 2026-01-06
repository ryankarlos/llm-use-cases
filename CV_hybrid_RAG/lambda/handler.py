"""CV Matcher API with GraphRAG - FastAPI + Mangum for Lambda."""

import logging
import os
from typing import Any, Dict, List, Optional, Set

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment config
NEPTUNE_ENDPOINT = os.environ.get("NEPTUNE_ENDPOINT", "")
OPENSEARCH_ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT", "")
AWS_REGION = os.environ.get("AWS_REGION_NAME", "us-east-1")

# Skill relationships for matching
RELATED_SKILLS: Dict[str, Set[str]] = {
    "Python": {"Java", "R", "Scala"},
    "Machine Learning": {"Deep Learning", "AI", "Data Science", "Statistics"},
    "Deep Learning": {"Machine Learning", "TensorFlow", "PyTorch"},
    "TensorFlow": {"PyTorch", "Keras", "Deep Learning"},
    "PyTorch": {"TensorFlow", "Keras", "Deep Learning"},
    "SQL": {"NoSQL", "PostgreSQL", "MySQL"},
    "AWS": {"Azure", "GCP", "Cloud"},
    "Docker": {"Kubernetes", "Containers"},
    "Kubernetes": {"Docker", "K8s"},
    "ETL": {"Data Pipelines", "Airflow"},
    "MLOps": {"DevOps", "CI/CD"},
    "Terraform": {"Infrastructure as Code", "CloudFormation"},
    "Cloud Architecture": {"AWS", "Azure", "GCP"},
}

JOB_ROLES = {
    "data_scientist": {
        "title": "Data Scientist",
        "required_skills": ["Python", "Machine Learning", "Statistics", "SQL", "Data Analysis"],
        "preferred_skills": ["Deep Learning", "NLP", "TensorFlow", "PyTorch"],
        "min_experience_years": 3
    },
    "data_engineer": {
        "title": "Data Engineer",
        "required_skills": ["Python", "SQL", "ETL", "Data Pipelines", "AWS"],
        "preferred_skills": ["Spark", "Airflow", "Kafka", "Terraform"],
        "min_experience_years": 3
    },
    "ml_engineer": {
        "title": "Machine Learning Engineer",
        "required_skills": ["Python", "Machine Learning", "MLOps", "Docker", "AWS"],
        "preferred_skills": ["Kubernetes", "SageMaker", "MLflow"],
        "min_experience_years": 4
    },
    "cloud_architect": {
        "title": "Cloud Architect",
        "required_skills": ["AWS", "Cloud Architecture", "Infrastructure as Code", "Security", "Networking"],
        "preferred_skills": ["Terraform", "Kubernetes", "Serverless"],
        "min_experience_years": 5
    }
}

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

# FastAPI app
app = FastAPI(title="CV Matcher API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# GraphRAG service singleton
_graphrag_service = None


class GraphRAGService:
    """GraphRAG service using AWS GraphRAG Toolkit."""
    
    def __init__(self):
        self._initialized = False
        self._graph_store = None
        self._vector_store = None
        self._query_engine = None
        self._error = None
    
    def initialize(self) -> bool:
        if not NEPTUNE_ENDPOINT or not OPENSEARCH_ENDPOINT:
            self._error = "Neptune/OpenSearch endpoints not configured"
            return False
        try:
            from graphrag_toolkit.lexical_graph import LexicalGraphQueryEngine
            from graphrag_toolkit.lexical_graph.storage import GraphStoreFactory, VectorStoreFactory
            
            self._graph_store = GraphStoreFactory.for_graph_store(f"neptune-db://{NEPTUNE_ENDPOINT}")
            self._vector_store = VectorStoreFactory.for_vector_store(f"aoss://{OPENSEARCH_ENDPOINT}")
            self._query_engine = LexicalGraphQueryEngine.for_traversal_based_search(self._graph_store, self._vector_store)
            self._initialized = True
            logger.info("GraphRAG initialized")
            return True
        except Exception as e:
            self._error = str(e)
            logger.warning(f"GraphRAG init failed: {e}")
            return False


def get_graphrag() -> GraphRAGService:
    global _graphrag_service
    if _graphrag_service is None:
        _graphrag_service = GraphRAGService()
        _graphrag_service.initialize()
    return _graphrag_service


def calculate_match_score(candidate: Dict, job: Dict) -> Dict[str, Any]:
    """Calculate match score: 50% direct + 30% related + 20% experience."""
    required = job["required_skills"]
    cand_skills = candidate["skills"]
    cand_lower = {s.lower() for s in cand_skills}
    
    direct = [s for s in required if s.lower() in cand_lower]
    direct_score = (len(direct) / len(required) * 100) if required else 0
    
    missing = set(required) - set(direct)
    related = [s for s in missing if any(r.lower() in cand_lower for r in RELATED_SKILLS.get(s, set()))]
    related_score = (len(related) / len(missing) * 100) if missing else 100
    
    min_exp = job["min_experience_years"]
    exp_score = 100.0 if candidate["experience_years"] >= min_exp else (candidate["experience_years"] / min_exp * 100)
    
    gaps = [s for s in required if s.lower() not in cand_lower]
    total = max(0.0, min(100.0, direct_score * 0.5 + related_score * 0.3 + exp_score * 0.2))
    
    return {
        "candidate_id": candidate["id"],
        "candidate_name": candidate["name"],
        "match_score": round(total, 1),
        "direct_matches": direct,
        "related_matches": related,
        "skill_gaps": gaps,
        "experience_years": candidate["experience_years"]
    }


# Pydantic models
class MatchRequest(BaseModel):
    role_id: str

class CompareRequest(BaseModel):
    candidate1_id: str
    candidate2_id: str
    role_id: str


@app.get("/health")
def health():
    svc = get_graphrag()
    return {
        "status": "healthy",
        "graphrag_enabled": svc._initialized,
        "graphrag_error": svc._error if not svc._initialized else None,
        "neptune": NEPTUNE_ENDPOINT,
        "opensearch": OPENSEARCH_ENDPOINT
    }


@app.get("/jobs")
def get_jobs():
    return {"jobs": list(JOB_ROLES.keys()), "details": JOB_ROLES}


@app.get("/candidates")
def get_candidates():
    return {"candidates": CANDIDATES}


@app.post("/match")
def match_candidates(req: MatchRequest):
    if req.role_id not in JOB_ROLES:
        raise HTTPException(400, f"Invalid role_id. Available: {list(JOB_ROLES.keys())}")
    
    job = JOB_ROLES[req.role_id]
    results = [calculate_match_score(c, job) for c in CANDIDATES]
    results.sort(key=lambda x: -x["match_score"])
    
    svc = get_graphrag()
    return {
        "job": {"role_id": req.role_id, **job},
        "matches": results,
        "graphrag_enabled": svc._initialized
    }


@app.post("/compare")
def compare_candidates(req: CompareRequest):
    cand1 = next((c for c in CANDIDATES if c["id"] == req.candidate1_id), None)
    cand2 = next((c for c in CANDIDATES if c["id"] == req.candidate2_id), None)
    job = JOB_ROLES.get(req.role_id)
    
    if not all([cand1, cand2, job]):
        raise HTTPException(404, "Candidate or job not found")
    
    return {
        "job": {"role_id": req.role_id, **job},
        "candidate1": calculate_match_score(cand1, job),
        "candidate2": calculate_match_score(cand2, job)
    }


# Mangum handler for Lambda
handler = Mangum(app, lifespan="off")
