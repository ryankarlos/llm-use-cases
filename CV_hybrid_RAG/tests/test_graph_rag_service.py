"""Tests for GraphRAG service."""

import pytest
from unittest.mock import MagicMock, patch

from CV_hybrid_RAG.src.graph_rag_service import (
    CVDocument,
    GraphMatchResult,
    GraphRAGConfig,
    GraphRAGService,
    JobDocument,
)


class TestGraphRAGConfig:
    """Tests for GraphRAGConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = GraphRAGConfig()
        
        assert config.neptune_port == 8182
        assert config.opensearch_index == "cv-matcher-index"
        assert config.region == "us-east-1"
        assert "nova" in config.extraction_model_id
        assert "titan" in config.embedding_model_id
        assert "nova" in config.response_model_id

    def test_from_env(self):
        """Test loading config from environment."""
        with patch.dict("os.environ", {
            "NEPTUNE_ENDPOINT": "test-neptune.amazonaws.com",
            "OPENSEARCH_ENDPOINT": "test-opensearch.amazonaws.com",
            "AWS_REGION": "eu-west-1"
        }):
            config = GraphRAGConfig.from_env()
            
            assert config.neptune_endpoint == "test-neptune.amazonaws.com"
            assert config.opensearch_endpoint == "test-opensearch.amazonaws.com"
            assert config.region == "eu-west-1"


class TestCVDocument:
    """Tests for CVDocument dataclass."""

    def test_cv_document_creation(self):
        """Test creating a CV document."""
        cv = CVDocument(
            candidate_id="cand_001",
            candidate_name="Test User",
            content="Experienced developer",
            skills=["Python", "AWS"],
            experience_years=5
        )
        
        assert cv.candidate_id == "cand_001"
        assert cv.candidate_name == "Test User"
        assert len(cv.skills) == 2
        assert cv.experience_years == 5

    def test_cv_document_defaults(self):
        """Test CV document default values."""
        cv = CVDocument(
            candidate_id="cand_002",
            candidate_name="Test",
            content="Content"
        )
        
        assert cv.skills == []
        assert cv.experience_years == 0
        assert cv.metadata == {}


class TestJobDocument:
    """Tests for JobDocument dataclass."""

    def test_job_document_creation(self):
        """Test creating a job document."""
        job = JobDocument(
            job_id="job_001",
            title="Data Scientist",
            content="Looking for DS",
            required_skills=["Python", "ML"],
            preferred_skills=["TensorFlow"],
            min_experience_years=3
        )
        
        assert job.job_id == "job_001"
        assert job.title == "Data Scientist"
        assert len(job.required_skills) == 2
        assert len(job.preferred_skills) == 1
        assert job.min_experience_years == 3


class TestGraphRAGService:
    """Tests for GraphRAGService."""

    def test_service_initialization_without_toolkit(self):
        """Test service behavior when toolkit is not installed."""
        config = GraphRAGConfig(
            neptune_endpoint="test-endpoint",
            opensearch_endpoint="test-opensearch"
        )
        service = GraphRAGService(config)
        
        # Should not be initialized yet
        assert not service._initialized

    def test_format_cv_for_indexing(self):
        """Test CV formatting for indexing."""
        config = GraphRAGConfig()
        service = GraphRAGService(config)
        
        cv = CVDocument(
            candidate_id="cand_001",
            candidate_name="Sarah Chen",
            content="Senior Data Scientist",
            skills=["Python", "ML"],
            experience_years=5
        )
        
        formatted = service._format_cv_for_indexing(cv)
        
        assert "Sarah Chen" in formatted
        assert "cand_001" in formatted
        assert "Python" in formatted
        assert "5" in formatted

    def test_format_job_for_indexing(self):
        """Test job formatting for indexing."""
        config = GraphRAGConfig()
        service = GraphRAGService(config)
        
        job = JobDocument(
            job_id="job_001",
            title="Data Scientist",
            content="Build ML models",
            required_skills=["Python", "SQL"],
            preferred_skills=["TensorFlow"],
            min_experience_years=3
        )
        
        formatted = service._format_job_for_indexing(job)
        
        assert "Data Scientist" in formatted
        assert "Python" in formatted
        assert "3 years" in formatted

    def test_build_candidate_search_query(self):
        """Test building search query for candidates."""
        config = GraphRAGConfig()
        service = GraphRAGService(config)
        
        job = JobDocument(
            job_id="job_001",
            title="ML Engineer",
            content="Deploy ML models",
            required_skills=["Python", "Docker"],
            preferred_skills=["Kubernetes"],
            min_experience_years=4
        )
        
        query = service._build_candidate_search_query(job)
        
        assert "ML Engineer" in query
        assert "Python" in query
        assert "Docker" in query
        assert "4" in query

    def test_calculate_skill_overlap(self):
        """Test skill overlap calculation."""
        config = GraphRAGConfig()
        service = GraphRAGService(config)
        
        # Full overlap
        overlap = service._calculate_skill_overlap(
            ["Python", "SQL", "AWS"],
            ["Python", "SQL"]
        )
        assert overlap == 1.0
        
        # Partial overlap
        overlap = service._calculate_skill_overlap(
            ["Python", "Java"],
            ["Python", "SQL", "AWS"]
        )
        assert abs(overlap - 0.333) < 0.01
        
        # No overlap
        overlap = service._calculate_skill_overlap(
            ["Java", "C++"],
            ["Python", "SQL"]
        )
        assert overlap == 0.0
        
        # Empty required skills
        overlap = service._calculate_skill_overlap(
            ["Python"],
            []
        )
        assert overlap == 1.0

    def test_index_cv_without_initialization(self):
        """Test indexing CV when service not initialized."""
        config = GraphRAGConfig()
        service = GraphRAGService(config)
        
        cv = CVDocument(
            candidate_id="cand_001",
            candidate_name="Test",
            content="Content"
        )
        
        result = service.index_cv(cv)
        assert result is False

    def test_find_candidates_without_initialization(self):
        """Test finding candidates when service not initialized."""
        config = GraphRAGConfig()
        service = GraphRAGService(config)
        
        job = JobDocument(
            job_id="job_001",
            title="Test",
            content="Content"
        )
        
        results = service.find_candidates_for_job(job)
        assert results == []


class TestGraphMatchResult:
    """Tests for GraphMatchResult dataclass."""

    def test_match_result_creation(self):
        """Test creating a match result."""
        result = GraphMatchResult(
            candidate_id="cand_001",
            candidate_name="Test User",
            match_score=85.5,
            matched_entities=["Python", "ML"],
            explanation="Strong match"
        )
        
        assert result.candidate_id == "cand_001"
        assert result.match_score == 85.5
        assert len(result.matched_entities) == 2
        assert result.explanation == "Strong match"

    def test_match_result_defaults(self):
        """Test match result default values."""
        result = GraphMatchResult(
            candidate_id="cand_001",
            candidate_name="Test",
            match_score=50.0
        )
        
        assert result.graph_paths == []
        assert result.matched_entities == []
        assert result.context_statements == []
        assert result.explanation == ""
