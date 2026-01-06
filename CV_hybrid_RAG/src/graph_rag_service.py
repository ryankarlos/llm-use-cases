"""GraphRAG Service using AWS GraphRAG Toolkit lexical-graph for CV matching.

This module provides integration with the AWS GraphRAG Toolkit's lexical-graph
for building knowledge graphs from CVs and job descriptions, enabling
graph-enhanced retrieval for candidate matching.

Reference: https://github.com/awslabs/graphrag-toolkit/tree/main/lexical-graph
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import boto3

logger = logging.getLogger(__name__)


@dataclass
class GraphRAGConfig:
    """Configuration for GraphRAG service."""
    
    # Neptune Database settings
    neptune_endpoint: str = ""
    neptune_port: int = 8182
    
    # OpenSearch Serverless settings
    opensearch_endpoint: str = ""
    opensearch_index: str = "cv-matcher-index"
    
    # AWS Bedrock model settings (using Amazon Nova and Titan models)
    extraction_model_id: str = "amazon.nova-lite-v1:0"  # Nova Lite for entity extraction
    embedding_model_id: str = "amazon.titan-embed-text-v2:0"  # Titan for embeddings
    response_model_id: str = "amazon.nova-lite-v1:0"  # Nova Lite for response generation
    
    # AWS settings
    region: str = "us-east-1"
    
    @classmethod
    def from_env(cls) -> "GraphRAGConfig":
        """Load configuration from environment variables."""
        import os
        return cls(
            neptune_endpoint=os.getenv("NEPTUNE_ENDPOINT", ""),
            neptune_port=int(os.getenv("NEPTUNE_PORT", "8182")),
            opensearch_endpoint=os.getenv("OPENSEARCH_ENDPOINT", ""),
            opensearch_index=os.getenv("OPENSEARCH_INDEX", "cv-matcher-index"),
            extraction_model_id=os.getenv("EXTRACTION_MODEL_ID", "amazon.nova-lite-v1:0"),
            embedding_model_id=os.getenv("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0"),
            response_model_id=os.getenv("RESPONSE_MODEL_ID", "amazon.nova-lite-v1:0"),
            region=os.getenv("AWS_REGION", "us-east-1"),
        )


@dataclass
class CVDocument:
    """Represents a CV document for indexing."""
    candidate_id: str
    candidate_name: str
    content: str
    skills: List[str] = field(default_factory=list)
    experience_years: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JobDocument:
    """Represents a job description document for indexing."""
    job_id: str
    title: str
    content: str
    required_skills: List[str] = field(default_factory=list)
    preferred_skills: List[str] = field(default_factory=list)
    min_experience_years: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class GraphMatchResult:
    """Result from graph-based candidate matching."""
    candidate_id: str
    candidate_name: str
    match_score: float
    graph_paths: List[List[str]] = field(default_factory=list)
    matched_entities: List[str] = field(default_factory=list)
    explanation: str = ""
    context_statements: List[str] = field(default_factory=list)


class GraphRAGService:
    """Service for CV matching using AWS GraphRAG Toolkit lexical-graph.
    
    This service provides:
    - Indexing CVs and job descriptions into a lexical graph
    - Graph-enhanced retrieval for finding relevant candidates
    - Semantic + structural matching for better candidate ranking
    
    The lexical graph model consists of three tiers:
    1. Source tier: Documents and chunks
    2. Entity-relationship tier: Extracted entities and their relationships
    3. Summarization tier: Topics, statements, and facts
    """

    def __init__(self, config: Optional[GraphRAGConfig] = None):
        """Initialize GraphRAG service.
        
        Args:
            config: GraphRAG configuration. If None, loads from environment.
        """
        self.config = config or GraphRAGConfig.from_env()
        self._graph_index = None
        self._query_engine = None
        self._initialized = False
        
    def initialize(self) -> bool:
        """Initialize the GraphRAG components.
        
        Returns:
            True if initialization successful, False otherwise.
        """
        try:
            # Import graphrag-toolkit components
            # These imports are deferred to allow the module to load without the toolkit
            from graphrag_toolkit import LexicalGraphIndex
            from graphrag_toolkit.storage import NeptuneDatabase, OpenSearchVectorStore
            
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
                extraction_model_id=self.config.extraction_model_id,
                embedding_model_id=self.config.embedding_model_id
            )
            
            self._initialized = True
            logger.info("GraphRAG service initialized successfully")
            return True
            
        except ImportError as e:
            logger.warning(f"GraphRAG toolkit not installed: {e}")
            logger.info("Install with: pip install graphrag-toolkit-lexical-graph")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize GraphRAG service: {e}")
            return False

    def index_cv(self, cv: CVDocument) -> bool:
        """Index a CV document into the lexical graph.
        
        Args:
            cv: CV document to index.
            
        Returns:
            True if indexing successful.
        """
        if not self._initialized:
            logger.warning("GraphRAG service not initialized")
            return False
            
        try:
            # Format CV content for indexing
            formatted_content = self._format_cv_for_indexing(cv)
            
            # Create document with metadata
            from llama_index.core import Document
            doc = Document(
                text=formatted_content,
                metadata={
                    "candidate_id": cv.candidate_id,
                    "candidate_name": cv.candidate_name,
                    "skills": ",".join(cv.skills),
                    "experience_years": cv.experience_years,
                    "doc_type": "cv",
                    **cv.metadata
                }
            )
            
            # Index using extract_and_build for continuous ingestion
            self._graph_index.extract_and_build([doc])
            logger.info(f"Indexed CV for candidate: {cv.candidate_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index CV: {e}")
            return False

    def index_job(self, job: JobDocument) -> bool:
        """Index a job description into the lexical graph.
        
        Args:
            job: Job document to index.
            
        Returns:
            True if indexing successful.
        """
        if not self._initialized:
            logger.warning("GraphRAG service not initialized")
            return False
            
        try:
            # Format job content for indexing
            formatted_content = self._format_job_for_indexing(job)
            
            from llama_index.core import Document
            doc = Document(
                text=formatted_content,
                metadata={
                    "job_id": job.job_id,
                    "title": job.title,
                    "required_skills": ",".join(job.required_skills),
                    "preferred_skills": ",".join(job.preferred_skills),
                    "min_experience_years": job.min_experience_years,
                    "doc_type": "job",
                    **job.metadata
                }
            )
            
            self._graph_index.extract_and_build([doc])
            logger.info(f"Indexed job: {job.title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index job: {e}")
            return False

    def batch_index_cvs(self, cvs: List[CVDocument]) -> int:
        """Batch index multiple CV documents.
        
        Args:
            cvs: List of CV documents to index.
            
        Returns:
            Number of successfully indexed documents.
        """
        if not self._initialized:
            logger.warning("GraphRAG service not initialized")
            return 0
            
        try:
            from llama_index.core import Document
            
            documents = []
            for cv in cvs:
                formatted_content = self._format_cv_for_indexing(cv)
                doc = Document(
                    text=formatted_content,
                    metadata={
                        "candidate_id": cv.candidate_id,
                        "candidate_name": cv.candidate_name,
                        "skills": ",".join(cv.skills),
                        "experience_years": cv.experience_years,
                        "doc_type": "cv",
                        **cv.metadata
                    }
                )
                documents.append(doc)
            
            # Batch index all documents
            self._graph_index.extract_and_build(documents)
            logger.info(f"Batch indexed {len(documents)} CVs")
            return len(documents)
            
        except Exception as e:
            logger.error(f"Failed to batch index CVs: {e}")
            return 0

    def find_candidates_for_job(
        self,
        job: JobDocument,
        top_k: int = 10,
        use_semantic_guided: bool = True
    ) -> List[GraphMatchResult]:
        """Find matching candidates for a job using graph-enhanced retrieval.
        
        This method uses the lexical graph to find candidates that are:
        1. Semantically similar to the job requirements
        2. Structurally connected through skill/experience relationships
        
        Args:
            job: Job document to match against.
            top_k: Maximum number of candidates to return.
            use_semantic_guided: Use SemanticGuidedRetriever (True) or TraversalBasedRetriever (False).
            
        Returns:
            List of matching candidates with scores and explanations.
        """
        if not self._initialized:
            logger.warning("GraphRAG service not initialized")
            return []
            
        try:
            from graphrag_toolkit import LexicalGraphQueryEngine
            from graphrag_toolkit.retrieval import (
                SemanticGuidedRetriever,
                TraversalBasedRetriever
            )
            from graphrag_toolkit.storage import NeptuneDatabase, OpenSearchVectorStore
            
            # Initialize stores for querying
            graph_store = NeptuneDatabase(
                endpoint=self.config.neptune_endpoint,
                port=self.config.neptune_port,
                region=self.config.region
            )
            
            vector_store = OpenSearchVectorStore(
                endpoint=self.config.opensearch_endpoint,
                index_name=self.config.opensearch_index,
                region=self.config.region
            )
            
            # Select retriever strategy
            if use_semantic_guided:
                # SemanticGuidedRetriever: blends vector search with graph traversal
                # Uses beam search and path analysis for quality results
                retriever = SemanticGuidedRetriever(
                    graph_store=graph_store,
                    vector_store=vector_store
                )
            else:
                # TraversalBasedRetriever: combines top-down and bottom-up search
                # Top-down: vector similarity -> chunks -> topics -> statements
                # Bottom-up: keyword lookup -> entities -> facts -> statements
                retriever = TraversalBasedRetriever(
                    graph_store=graph_store,
                    vector_store=vector_store
                )
            
            # Build the query from job requirements
            query = self._build_candidate_search_query(job)
            
            # Create query engine
            query_engine = LexicalGraphQueryEngine(
                graph_store=graph_store,
                vector_store=vector_store,
                retriever=retriever,
                response_model_id=self.config.response_model_id
            )
            
            # Execute query
            response = query_engine.query(query)
            
            # Parse and rank results
            results = self._parse_candidate_results(response, job, top_k)
            return results
            
        except Exception as e:
            logger.error(f"Failed to find candidates: {e}")
            return []

    def find_jobs_for_candidate(
        self,
        cv: CVDocument,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Find matching jobs for a candidate using graph-enhanced retrieval.
        
        Args:
            cv: Candidate CV document.
            top_k: Maximum number of jobs to return.
            
        Returns:
            List of matching jobs with relevance scores.
        """
        if not self._initialized:
            logger.warning("GraphRAG service not initialized")
            return []
            
        try:
            from graphrag_toolkit import LexicalGraphQueryEngine
            from graphrag_toolkit.retrieval import SemanticGuidedRetriever
            from graphrag_toolkit.storage import NeptuneDatabase, OpenSearchVectorStore
            
            graph_store = NeptuneDatabase(
                endpoint=self.config.neptune_endpoint,
                port=self.config.neptune_port,
                region=self.config.region
            )
            
            vector_store = OpenSearchVectorStore(
                endpoint=self.config.opensearch_endpoint,
                index_name=self.config.opensearch_index,
                region=self.config.region
            )
            
            retriever = SemanticGuidedRetriever(
                graph_store=graph_store,
                vector_store=vector_store
            )
            
            query = self._build_job_search_query(cv)
            
            query_engine = LexicalGraphQueryEngine(
                graph_store=graph_store,
                vector_store=vector_store,
                retriever=retriever,
                response_model_id=self.config.response_model_id
            )
            
            response = query_engine.query(query)
            return self._parse_job_results(response, cv, top_k)
            
        except Exception as e:
            logger.error(f"Failed to find jobs: {e}")
            return []

    def get_skill_graph(self, skill: str) -> Dict[str, Any]:
        """Get the skill relationship graph for a specific skill.
        
        Args:
            skill: Skill name to explore.
            
        Returns:
            Dictionary containing related skills and their connections.
        """
        if not self._initialized:
            return {"skill": skill, "related": [], "error": "Service not initialized"}
            
        try:
            from graphrag_toolkit.storage import NeptuneDatabase
            
            graph_store = NeptuneDatabase(
                endpoint=self.config.neptune_endpoint,
                port=self.config.neptune_port,
                region=self.config.region
            )
            
            # Query for skill relationships in the graph
            query = f"""
            MATCH (s:Entity {{name: '{skill}'}})-[r]-(related)
            RETURN s.name as skill, type(r) as relationship, related.name as related_entity
            LIMIT 50
            """
            
            results = graph_store.execute_query(query)
            
            return {
                "skill": skill,
                "related": [
                    {"entity": r["related_entity"], "relationship": r["relationship"]}
                    for r in results
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get skill graph: {e}")
            return {"skill": skill, "related": [], "error": str(e)}

    def _format_cv_for_indexing(self, cv: CVDocument) -> str:
        """Format CV document for optimal graph extraction."""
        parts = [
            f"Candidate Profile: {cv.candidate_name}",
            f"Candidate ID: {cv.candidate_id}",
            f"Years of Experience: {cv.experience_years}",
            f"Skills: {', '.join(cv.skills)}",
            "",
            "Professional Summary:",
            cv.content
        ]
        return "\n".join(parts)

    def _format_job_for_indexing(self, job: JobDocument) -> str:
        """Format job document for optimal graph extraction."""
        parts = [
            f"Job Title: {job.title}",
            f"Job ID: {job.job_id}",
            f"Minimum Experience Required: {job.min_experience_years} years",
            f"Required Skills: {', '.join(job.required_skills)}",
            f"Preferred Skills: {', '.join(job.preferred_skills)}",
            "",
            "Job Description:",
            job.content
        ]
        return "\n".join(parts)

    def _build_candidate_search_query(self, job: JobDocument) -> str:
        """Build a search query to find candidates for a job."""
        skills_text = ", ".join(job.required_skills + job.preferred_skills)
        return f"""
        Find candidates who are qualified for the {job.title} position.
        
        Required qualifications:
        - Skills: {', '.join(job.required_skills)}
        - Minimum {job.min_experience_years} years of experience
        
        Preferred qualifications:
        - Additional skills: {', '.join(job.preferred_skills)}
        
        Job description: {job.content}
        
        Return candidates with matching skills and relevant experience.
        For each candidate, explain how their background aligns with the requirements.
        """

    def _build_job_search_query(self, cv: CVDocument) -> str:
        """Build a search query to find jobs for a candidate."""
        return f"""
        Find job opportunities suitable for {cv.candidate_name}.
        
        Candidate profile:
        - Skills: {', '.join(cv.skills)}
        - Years of experience: {cv.experience_years}
        
        Background: {cv.content}
        
        Return jobs that match the candidate's skills and experience level.
        """

    def _parse_candidate_results(
        self,
        response: Any,
        job: JobDocument,
        top_k: int
    ) -> List[GraphMatchResult]:
        """Parse query response into candidate match results."""
        results = []
        
        # Extract candidate information from response
        # The response contains statements and their source metadata
        if hasattr(response, 'source_nodes'):
            seen_candidates = set()
            
            for node in response.source_nodes[:top_k * 2]:  # Get extra to filter duplicates
                metadata = node.metadata or {}
                
                if metadata.get('doc_type') != 'cv':
                    continue
                    
                candidate_id = metadata.get('candidate_id', '')
                if candidate_id in seen_candidates:
                    continue
                seen_candidates.add(candidate_id)
                
                # Calculate match score based on node score and skill overlap
                base_score = node.score if hasattr(node, 'score') else 0.5
                skill_overlap = self._calculate_skill_overlap(
                    metadata.get('skills', '').split(','),
                    job.required_skills
                )
                match_score = (base_score * 0.6 + skill_overlap * 0.4) * 100
                
                result = GraphMatchResult(
                    candidate_id=candidate_id,
                    candidate_name=metadata.get('candidate_name', 'Unknown'),
                    match_score=min(100.0, match_score),
                    matched_entities=metadata.get('skills', '').split(','),
                    context_statements=[node.text] if hasattr(node, 'text') else []
                )
                results.append(result)
                
                if len(results) >= top_k:
                    break
        
        # Sort by match score
        results.sort(key=lambda x: x.match_score, reverse=True)
        return results[:top_k]

    def _parse_job_results(
        self,
        response: Any,
        cv: CVDocument,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Parse query response into job match results."""
        results = []
        
        if hasattr(response, 'source_nodes'):
            seen_jobs = set()
            
            for node in response.source_nodes[:top_k * 2]:
                metadata = node.metadata or {}
                
                if metadata.get('doc_type') != 'job':
                    continue
                    
                job_id = metadata.get('job_id', '')
                if job_id in seen_jobs:
                    continue
                seen_jobs.add(job_id)
                
                base_score = node.score if hasattr(node, 'score') else 0.5
                
                results.append({
                    "job_id": job_id,
                    "title": metadata.get('title', 'Unknown'),
                    "match_score": base_score * 100,
                    "required_skills": metadata.get('required_skills', '').split(','),
                    "min_experience": metadata.get('min_experience_years', 0)
                })
                
                if len(results) >= top_k:
                    break
        
        results.sort(key=lambda x: x['match_score'], reverse=True)
        return results[:top_k]

    def _calculate_skill_overlap(
        self,
        candidate_skills: List[str],
        required_skills: List[str]
    ) -> float:
        """Calculate skill overlap ratio."""
        if not required_skills:
            return 1.0
            
        candidate_lower = {s.lower().strip() for s in candidate_skills if s.strip()}
        required_lower = {s.lower().strip() for s in required_skills if s.strip()}
        
        if not required_lower:
            return 1.0
            
        matches = len(candidate_lower & required_lower)
        return matches / len(required_lower)
