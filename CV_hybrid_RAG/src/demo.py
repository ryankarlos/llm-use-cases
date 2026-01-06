"""Demo script for CV matching using AWS GraphRAG Toolkit lexical-graph.

This script demonstrates how to use the GraphRAG service for:
1. Indexing CVs and job descriptions into a lexical graph
2. Finding matching candidates for job openings
3. Finding suitable jobs for candidates

Usage:
    # With real AWS infrastructure
    python -m CV_hybrid_RAG.src.demo --mode live
    
    # Demo mode with mock data (no AWS required)
    python -m CV_hybrid_RAG.src.demo --mode demo

Reference: https://github.com/awslabs/graphrag-toolkit/tree/main/lexical-graph
"""

import argparse
import json
import logging
from pathlib import Path
from typing import List

from .cv_matcher import CVMatcherService, CandidateProfile
from .graph_rag_service import (
    CVDocument,
    GraphMatchResult,
    GraphRAGConfig,
    GraphRAGService,
    JobDocument,
)
from .job_roles import JobRoleService
from .models import JobRole

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_sample_cvs(data_path: Path) -> List[CVDocument]:
    """Load sample CVs from JSON file."""
    cv_file = data_path / "sample_cvs.json"
    
    if not cv_file.exists():
        logger.warning(f"Sample CVs file not found: {cv_file}")
        return []
    
    with open(cv_file) as f:
        data = json.load(f)
    
    cvs = []
    for candidate in data.get("candidates", []):
        cv = CVDocument(
            candidate_id=candidate["candidate_id"],
            candidate_name=candidate["candidate_name"],
            content=candidate.get("experience_summary", ""),
            skills=candidate.get("skills", []),
            experience_years=candidate.get("experience_years", 0),
            metadata={"skill_connections": candidate.get("skill_connections", 0)}
        )
        cvs.append(cv)
    
    return cvs


def create_job_documents(job_service: JobRoleService) -> List[JobDocument]:
    """Create job documents from predefined roles."""
    jobs = []
    
    for role in job_service.get_all_roles():
        job = JobDocument(
            job_id=role.role_id,
            title=role.title,
            content=role.description,
            required_skills=role.required_skills,
            preferred_skills=role.preferred_skills,
            min_experience_years=role.min_experience_years,
            metadata={"department": role.department}
        )
        jobs.append(job)
    
    return jobs


def run_demo_mode():
    """Run demo with mock matching (no AWS infrastructure required)."""
    logger.info("=" * 60)
    logger.info("CV Matching Demo - Using Local Skill-Based Matching")
    logger.info("=" * 60)
    
    # Load sample data
    data_path = Path(__file__).parent.parent / "data"
    cvs = load_sample_cvs(data_path)
    
    if not cvs:
        logger.error("No sample CVs found. Please check data/sample_cvs.json")
        return
    
    # Initialize services
    job_service = JobRoleService()
    matcher_service = CVMatcherService()
    
    # Convert CVs to CandidateProfiles for local matching
    candidates = [
        CandidateProfile(
            candidate_id=cv.candidate_id,
            candidate_name=cv.candidate_name,
            skills=cv.skills,
            experience_years=cv.experience_years,
            experience_summary=cv.content,
            skill_connections=cv.metadata.get("skill_connections", 0)
        )
        for cv in cvs
    ]
    
    logger.info(f"\nLoaded {len(candidates)} candidates")
    logger.info(f"Available job roles: {job_service.get_role_ids()}")
    
    # Demo: Match candidates to each job role
    for role_id in job_service.get_role_ids():
        job_role = job_service.get_role(role_id)
        
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Job: {job_role.title}")
        logger.info(f"Required Skills: {', '.join(job_role.required_skills)}")
        logger.info(f"Min Experience: {job_role.min_experience_years} years")
        logger.info("-" * 60)
        
        # Rank candidates
        matches = matcher_service.rank_candidates(candidates, job_role)
        
        logger.info("Top Candidates:")
        for i, match in enumerate(matches[:3], 1):
            logger.info(f"\n  {i}. {match.candidate_name}")
            logger.info(f"     Match Score: {match.match_score:.1f}%")
            logger.info(f"     Direct Skill Matches: {', '.join(match.direct_skill_matches) or 'None'}")
            logger.info(f"     Related Skills: {', '.join(match.related_skill_matches) or 'None'}")
            logger.info(f"     Skill Gaps: {', '.join(match.skill_gaps) or 'None'}")
            logger.info(f"     Transferable: {', '.join(match.transferable_skills) or 'None'}")


def run_live_mode(config: GraphRAGConfig):
    """Run with live AWS GraphRAG infrastructure."""
    logger.info("=" * 60)
    logger.info("CV Matching Demo - Using AWS GraphRAG Toolkit")
    logger.info("=" * 60)
    
    # Initialize GraphRAG service
    graph_service = GraphRAGService(config)
    
    if not graph_service.initialize():
        logger.error("Failed to initialize GraphRAG service")
        logger.info("Make sure you have:")
        logger.info("  1. Neptune Database endpoint configured")
        logger.info("  2. OpenSearch Serverless endpoint configured")
        logger.info("  3. Bedrock model access enabled")
        logger.info("  4. graphrag-toolkit installed: pip install graphrag-toolkit-lexical-graph")
        return
    
    # Load sample data
    data_path = Path(__file__).parent.parent / "data"
    cvs = load_sample_cvs(data_path)
    
    if not cvs:
        logger.error("No sample CVs found")
        return
    
    job_service = JobRoleService()
    jobs = create_job_documents(job_service)
    
    # Index CVs into the lexical graph
    logger.info(f"\nIndexing {len(cvs)} CVs into lexical graph...")
    indexed_count = graph_service.batch_index_cvs(cvs)
    logger.info(f"Successfully indexed {indexed_count} CVs")
    
    # Index job descriptions
    logger.info(f"\nIndexing {len(jobs)} job descriptions...")
    for job in jobs:
        graph_service.index_job(job)
    logger.info("Job indexing complete")
    
    # Demo: Find candidates for each job
    for job in jobs:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Finding candidates for: {job.title}")
        logger.info("-" * 60)
        
        # Use graph-enhanced retrieval
        results = graph_service.find_candidates_for_job(
            job,
            top_k=5,
            use_semantic_guided=True
        )
        
        if not results:
            logger.info("No matching candidates found")
            continue
        
        logger.info("Top Candidates (Graph-Enhanced Matching):")
        for i, result in enumerate(results, 1):
            logger.info(f"\n  {i}. {result.candidate_name}")
            logger.info(f"     Match Score: {result.match_score:.1f}%")
            logger.info(f"     Matched Entities: {', '.join(result.matched_entities[:5])}")
            if result.graph_paths:
                logger.info(f"     Graph Paths: {len(result.graph_paths)} connections found")
            if result.explanation:
                logger.info(f"     Explanation: {result.explanation[:200]}...")
    
    # Demo: Find jobs for a specific candidate
    if cvs:
        test_cv = cvs[0]
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Finding jobs for: {test_cv.candidate_name}")
        logger.info(f"Skills: {', '.join(test_cv.skills)}")
        logger.info("-" * 60)
        
        job_matches = graph_service.find_jobs_for_candidate(test_cv, top_k=3)
        
        if job_matches:
            logger.info("Recommended Jobs:")
            for i, job_match in enumerate(job_matches, 1):
                logger.info(f"\n  {i}. {job_match['title']}")
                logger.info(f"     Match Score: {job_match['match_score']:.1f}%")
        else:
            logger.info("No matching jobs found")


def run_hybrid_mode(config: GraphRAGConfig):
    """Run hybrid matching combining local scoring with graph retrieval."""
    logger.info("=" * 60)
    logger.info("CV Matching Demo - Hybrid Mode")
    logger.info("(Local scoring + Graph-enhanced retrieval)")
    logger.info("=" * 60)
    
    # Initialize services
    graph_service = GraphRAGService(config)
    graph_initialized = graph_service.initialize()
    
    job_service = JobRoleService()
    matcher_service = CVMatcherService()
    
    # Load data
    data_path = Path(__file__).parent.parent / "data"
    cvs = load_sample_cvs(data_path)
    
    if not cvs:
        logger.error("No sample CVs found")
        return
    
    candidates = [
        CandidateProfile(
            candidate_id=cv.candidate_id,
            candidate_name=cv.candidate_name,
            skills=cv.skills,
            experience_years=cv.experience_years,
            experience_summary=cv.content,
            skill_connections=cv.metadata.get("skill_connections", 0)
        )
        for cv in cvs
    ]
    
    # Process each job role
    for role_id in job_service.get_role_ids():
        job_role = job_service.get_role(role_id)
        
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Job: {job_role.title}")
        logger.info("-" * 60)
        
        # Local skill-based matching
        local_matches = matcher_service.rank_candidates(candidates, job_role)
        
        logger.info("\nLocal Skill-Based Ranking:")
        for i, match in enumerate(local_matches[:3], 1):
            logger.info(f"  {i}. {match.candidate_name}: {match.match_score:.1f}%")
        
        # Graph-enhanced matching (if available)
        if graph_initialized:
            job_doc = JobDocument(
                job_id=job_role.role_id,
                title=job_role.title,
                content=job_role.description,
                required_skills=job_role.required_skills,
                preferred_skills=job_role.preferred_skills,
                min_experience_years=job_role.min_experience_years
            )
            
            graph_results = graph_service.find_candidates_for_job(job_doc, top_k=3)
            
            if graph_results:
                logger.info("\nGraph-Enhanced Ranking:")
                for i, result in enumerate(graph_results, 1):
                    logger.info(f"  {i}. {result.candidate_name}: {result.match_score:.1f}%")
        else:
            logger.info("\n(Graph-enhanced matching not available)")


def main():
    """Main entry point for the demo."""
    parser = argparse.ArgumentParser(
        description="CV Matching Demo using AWS GraphRAG Toolkit"
    )
    parser.add_argument(
        "--mode",
        choices=["demo", "live", "hybrid"],
        default="demo",
        help="Run mode: demo (local), live (AWS), or hybrid"
    )
    parser.add_argument(
        "--neptune-endpoint",
        help="Neptune Database endpoint"
    )
    parser.add_argument(
        "--opensearch-endpoint", 
        help="OpenSearch Serverless endpoint"
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region"
    )
    
    args = parser.parse_args()
    
    if args.mode == "demo":
        run_demo_mode()
    else:
        # Build config from args or environment
        config = GraphRAGConfig(
            neptune_endpoint=args.neptune_endpoint or "",
            opensearch_endpoint=args.opensearch_endpoint or "",
            region=args.region
        )
        
        if not config.neptune_endpoint:
            config = GraphRAGConfig.from_env()
        
        if args.mode == "live":
            run_live_mode(config)
        else:
            run_hybrid_mode(config)


if __name__ == "__main__":
    main()
