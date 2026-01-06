# CV Job Matcher - Source Package
"""CV Job Matcher using AWS GraphRAG Toolkit for intelligent candidate matching.

This package provides CV-to-job matching using:
1. Local skill-based scoring (CVMatcherService)
2. Graph-enhanced retrieval using AWS GraphRAG Toolkit lexical-graph (GraphRAGService)

Reference: https://github.com/awslabs/graphrag-toolkit/tree/main/lexical-graph
"""

from .models import JobRole, CandidateMatch, IngestionResult, IngestionStatus
from .job_roles import JobRoleService
from .cv_matcher import CVMatcherService, CandidateProfile
from .graph_rag_service import (
    GraphRAGService,
    GraphRAGConfig,
    CVDocument,
    JobDocument,
    GraphMatchResult,
)

__all__ = [
    # Models
    "JobRole",
    "CandidateMatch", 
    "IngestionResult",
    "IngestionStatus",
    # Services
    "JobRoleService",
    "CVMatcherService",
    "CandidateProfile",
    # GraphRAG components
    "GraphRAGService",
    "GraphRAGConfig",
    "CVDocument",
    "JobDocument",
    "GraphMatchResult",
]
