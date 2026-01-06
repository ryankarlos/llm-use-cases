"""CV Matcher Service for matching candidates to job roles."""

from dataclasses import dataclass
from typing import List, Set, Optional

from .models import JobRole, CandidateMatch


@dataclass
class CandidateProfile:
    """Represents a candidate's profile extracted from CV."""
    candidate_id: str
    candidate_name: str
    skills: List[str]
    experience_years: int
    experience_summary: str = ""
    skill_connections: int = 0  # Graph centrality measure


class CVMatcherService:
    """Service for matching candidates to job roles using skill-based scoring."""

    # Skill relationship mapping for related skill detection
    RELATED_SKILLS: dict[str, Set[str]] = {
        "Python": {"Java", "R", "Scala", "Julia"},
        "Machine Learning": {"Deep Learning", "AI", "Data Science", "Statistics"},
        "Deep Learning": {"Machine Learning", "Neural Networks", "TensorFlow", "PyTorch"},
        "TensorFlow": {"PyTorch", "Keras", "Deep Learning"},
        "PyTorch": {"TensorFlow", "Keras", "Deep Learning"},
        "SQL": {"NoSQL", "PostgreSQL", "MySQL", "Database"},
        "AWS": {"Azure", "GCP", "Cloud"},
        "Docker": {"Kubernetes", "Containers", "Containerization"},
        "Kubernetes": {"Docker", "Container Orchestration", "K8s"},
        "Spark": {"Hadoop", "Big Data", "Distributed Computing"},
        "ETL": {"Data Pipelines", "Data Integration", "Data Transformation"},
        "Data Pipelines": {"ETL", "Airflow", "Data Engineering"},
        "MLOps": {"DevOps", "CI/CD", "Model Deployment"},
        "Statistics": {"Mathematics", "Data Analysis", "Probability"},
        "NLP": {"Natural Language Processing", "Text Mining", "LLM"},
        "Computer Vision": {"Image Processing", "CNN", "Object Detection"},
        "Terraform": {"Infrastructure as Code", "CloudFormation", "Pulumi"},
        "Infrastructure as Code": {"Terraform", "CloudFormation", "Ansible"},
        "Cloud Architecture": {"AWS", "Azure", "GCP", "System Design"},
        "Security": {"Cybersecurity", "IAM", "Encryption"},
        "Networking": {"VPC", "DNS", "Load Balancing"},
    }

    def __init__(self):
        """Initialize CVMatcherService."""
        pass

    def calculate_match_score(
        self,
        candidate: CandidateProfile,
        job_role: JobRole
    ) -> float:
        """Calculate match score for a candidate-job pair.
        
        Scoring formula:
        - 50% weight for direct skill matches
        - 30% weight for related skill matches  
        - 20% weight for experience relevance
        
        Args:
            candidate: The candidate profile to score.
            job_role: The job role to match against.
            
        Returns:
            Match score between 0 and 100.
        """
        # Calculate direct skill match percentage
        direct_matches = self._find_direct_skill_matches(candidate.skills, job_role.required_skills)
        direct_score = (len(direct_matches) / len(job_role.required_skills) * 100) if job_role.required_skills else 0
        
        # Calculate related skill match percentage
        related_matches = self._find_related_skill_matches(
            candidate.skills, 
            job_role.required_skills,
            direct_matches
        )
        # Related skills can contribute up to 100% if all missing required skills have related matches
        missing_required = set(job_role.required_skills) - direct_matches
        related_score = (len(related_matches) / len(missing_required) * 100) if missing_required else 100
        
        # Calculate experience score
        experience_score = self._calculate_experience_score(
            candidate.experience_years,
            job_role.min_experience_years
        )
        
        # Apply weights: 50% direct, 30% related, 20% experience
        total_score = (
            direct_score * 0.50 +
            related_score * 0.30 +
            experience_score * 0.20
        )
        
        # Ensure score is within bounds [0, 100]
        return max(0.0, min(100.0, total_score))

    def _find_direct_skill_matches(
        self,
        candidate_skills: List[str],
        required_skills: List[str]
    ) -> Set[str]:
        """Find skills that directly match between candidate and job requirements.
        
        Args:
            candidate_skills: List of candidate's skills.
            required_skills: List of required skills for the job.
            
        Returns:
            Set of matching skills (case-insensitive).
        """
        candidate_skills_lower = {s.lower() for s in candidate_skills}
        matches = set()
        for skill in required_skills:
            if skill.lower() in candidate_skills_lower:
                matches.add(skill)
        return matches

    def _find_related_skill_matches(
        self,
        candidate_skills: List[str],
        required_skills: List[str],
        direct_matches: Set[str]
    ) -> Set[str]:
        """Find required skills that have related skills in candidate's profile.
        
        Args:
            candidate_skills: List of candidate's skills.
            required_skills: List of required skills for the job.
            direct_matches: Skills already matched directly.
            
        Returns:
            Set of required skills that have related matches.
        """
        candidate_skills_lower = {s.lower() for s in candidate_skills}
        related_matches = set()
        
        for required_skill in required_skills:
            # Skip if already directly matched
            if required_skill in direct_matches:
                continue
                
            # Check if candidate has any related skills
            related_skills = self.RELATED_SKILLS.get(required_skill, set())
            for related in related_skills:
                if related.lower() in candidate_skills_lower:
                    related_matches.add(required_skill)
                    break
        
        return related_matches

    def _calculate_experience_score(
        self,
        candidate_years: int,
        required_years: int
    ) -> float:
        """Calculate experience relevance score.
        
        Args:
            candidate_years: Candidate's years of experience.
            required_years: Minimum required years for the role.
            
        Returns:
            Score between 0 and 100.
        """
        if required_years <= 0:
            return 100.0
        
        if candidate_years >= required_years:
            return 100.0
        
        # Partial credit for having some experience
        return (candidate_years / required_years) * 100

    def find_skill_gaps(
        self,
        candidate: CandidateProfile,
        job_role: JobRole
    ) -> List[str]:
        """Identify missing required skills for a candidate.
        
        Args:
            candidate: The candidate profile.
            job_role: The job role to check against.
            
        Returns:
            List of required skills the candidate is missing.
        """
        candidate_skills_lower = {s.lower() for s in candidate.skills}
        gaps = []
        
        for required_skill in job_role.required_skills:
            if required_skill.lower() not in candidate_skills_lower:
                gaps.append(required_skill)
        
        return gaps

    def find_transferable_skills(
        self,
        candidate: CandidateProfile,
        job_role: JobRole
    ) -> List[str]:
        """Find candidate skills that are related to but not required by the job.
        
        Args:
            candidate: The candidate profile.
            job_role: The job role to check against.
            
        Returns:
            List of transferable skills.
        """
        required_lower = {s.lower() for s in job_role.required_skills}
        preferred_lower = {s.lower() for s in job_role.preferred_skills}
        transferable = []
        
        for skill in candidate.skills:
            skill_lower = skill.lower()
            # Skip if it's a required or preferred skill
            if skill_lower in required_lower or skill_lower in preferred_lower:
                continue
            
            # Check if this skill is related to any required skill
            for required_skill in job_role.required_skills:
                related_skills = self.RELATED_SKILLS.get(required_skill, set())
                if skill in related_skills or skill_lower in {s.lower() for s in related_skills}:
                    transferable.append(skill)
                    break
        
        return transferable

    def rank_candidates(
        self,
        candidates: List[CandidateProfile],
        job_role: JobRole
    ) -> List[CandidateMatch]:
        """Rank candidates for a job role by match score.
        
        Candidates are sorted by:
        1. Match score (descending)
        2. Graph centrality / skill connections (descending) as tiebreaker
        
        Args:
            candidates: List of candidate profiles to rank.
            job_role: The job role to match against.
            
        Returns:
            List of CandidateMatch objects sorted by score.
        """
        matches = []
        
        for candidate in candidates:
            score = self.calculate_match_score(candidate, job_role)
            direct_matches = list(self._find_direct_skill_matches(
                candidate.skills, 
                job_role.required_skills
            ))
            related_matches = list(self._find_related_skill_matches(
                candidate.skills,
                job_role.required_skills,
                set(direct_matches)
            ))
            skill_gaps = self.find_skill_gaps(candidate, job_role)
            transferable = self.find_transferable_skills(candidate, job_role)
            
            match = CandidateMatch(
                candidate_id=candidate.candidate_id,
                candidate_name=candidate.candidate_name,
                match_score=score,
                direct_skill_matches=direct_matches,
                related_skill_matches=related_matches,
                skill_gaps=skill_gaps,
                transferable_skills=transferable,
                experience_summary=candidate.experience_summary,
                graph_path=[],  # Would be populated by graph traversal
                explanation=""  # Would be generated by LLM
            )
            matches.append((match, candidate.skill_connections))
        
        # Sort by match_score descending, then by skill_connections (centrality) descending
        matches.sort(key=lambda x: (-x[0].match_score, -x[1]))
        
        return [m[0] for m in matches]
