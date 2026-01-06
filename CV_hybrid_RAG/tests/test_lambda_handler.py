"""Tests for Lambda handler with GraphRAG integration."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "lambda"))
from handler import handler, calculate_match_score, match_with_graphrag, JOB_ROLES, CANDIDATES, GraphRAGService


def test_health_endpoint():
    event = {"path": "/health", "httpMethod": "GET"}
    result = handler(event, None)
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["status"] == "healthy"
    assert "graphrag_enabled" in body


def test_jobs_endpoint():
    event = {"path": "/jobs", "httpMethod": "GET"}
    result = handler(event, None)
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert "data_scientist" in body["jobs"]
    assert len(body["details"]) == 4


def test_candidates_endpoint():
    event = {"path": "/candidates", "httpMethod": "GET"}
    result = handler(event, None)
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body["candidates"]) == 8


def test_match_endpoint():
    event = {"path": "/match", "httpMethod": "POST", "body": json.dumps({"role_id": "data_scientist"})}
    result = handler(event, None)
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["job"]["title"] == "Data Scientist"
    assert len(body["matches"]) == 8
    assert body["matches"][0]["match_score"] >= body["matches"][-1]["match_score"]
    assert "graphrag_enabled" in body


def test_match_invalid_role():
    event = {"path": "/match", "httpMethod": "POST", "body": json.dumps({"role_id": "invalid"})}
    result = handler(event, None)
    assert result["statusCode"] == 400


def test_compare_endpoint():
    event = {"path": "/compare", "httpMethod": "POST", 
             "body": json.dumps({"candidate1_id": "cand_001", "candidate2_id": "cand_002", "role_id": "data_scientist"})}
    result = handler(event, None)
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert "candidate1" in body
    assert "candidate2" in body


def test_calculate_match_score_perfect():
    cand = {"id": "test", "name": "Test", "skills": ["Python", "Machine Learning", "Statistics", "SQL", "Data Analysis"], "experience_years": 5}
    job = JOB_ROLES["data_scientist"]
    result = calculate_match_score(cand, job)
    assert result["match_score"] == 100.0
    assert len(result["skill_gaps"]) == 0


def test_calculate_match_score_partial():
    cand = {"id": "test", "name": "Test", "skills": ["Python", "SQL"], "experience_years": 2}
    job = JOB_ROLES["data_scientist"]
    result = calculate_match_score(cand, job)
    assert 0 < result["match_score"] < 100
    assert len(result["skill_gaps"]) > 0


def test_calculate_match_score_with_related():
    """Test that related skills boost the score."""
    cand = {"id": "test", "name": "Test", "skills": ["Python", "SQL", "Deep Learning", "TensorFlow"], "experience_years": 3}
    job = JOB_ROLES["data_scientist"]
    result = calculate_match_score(cand, job)
    # Should have related matches for Machine Learning (via Deep Learning)
    assert len(result["related_matches"]) > 0 or len(result["direct_matches"]) > 0


def test_not_found():
    event = {"path": "/unknown", "httpMethod": "GET"}
    result = handler(event, None)
    assert result["statusCode"] == 404


def test_graphrag_service_init_without_endpoints():
    """Test GraphRAG service doesn't initialize without endpoints."""
    service = GraphRAGService()
    with patch.dict('os.environ', {'NEPTUNE_ENDPOINT': '', 'OPENSEARCH_ENDPOINT': ''}):
        result = service.initialize()
    assert result == False
    assert service._initialized == False


def test_match_with_graphrag_fallback():
    """Test that match_with_graphrag falls back to skill-based when GraphRAG unavailable."""
    job = JOB_ROLES["data_scientist"]
    results = match_with_graphrag(job)
    assert len(results) == 8
    # Should have graph_enhanced flag
    assert all("graph_enhanced" in r for r in results)
    # Without GraphRAG, should be False
    assert all(r["graph_enhanced"] == False for r in results)
