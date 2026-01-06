"""Data models for CV Job Matcher."""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class IngestionStatus(Enum):
    """Status of CV ingestion process."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class JobRole:
    """Represents a job role with required skills and qualifications."""
    role_id: str
    title: str
    department: str
    required_skills: List[str]
    preferred_skills: List[str]
    min_experience_years: int
    education_requirements: List[str]
    description: str


@dataclass
class CandidateMatch:
    """Represents a matched candidate with scoring details."""
    candidate_id: str
    candidate_name: str
    match_score: float  # 0-100
    direct_skill_matches: List[str] = field(default_factory=list)
    related_skill_matches: List[str] = field(default_factory=list)
    skill_gaps: List[str] = field(default_factory=list)
    transferable_skills: List[str] = field(default_factory=list)
    experience_summary: str = ""
    graph_path: List[str] = field(default_factory=list)
    explanation: str = ""


@dataclass
class IngestionResult:
    """Result of CV ingestion operation."""
    status: IngestionStatus
    documents_processed: int = 0
    documents_failed: int = 0
    entities_extracted: int = 0
    error_message: Optional[str] = None
