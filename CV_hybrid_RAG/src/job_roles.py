"""Job Role Service for CV Job Matcher."""

import json
from pathlib import Path
from typing import Dict, List, Optional

from .models import JobRole


class JobRoleService:
    """Manages job role definitions and their graph representation."""

    PREDEFINED_ROLES: Dict[str, JobRole] = {
        "data_scientist": JobRole(
            role_id="data_scientist",
            title="Data Scientist",
            department="AI",
            required_skills=["Python", "Machine Learning", "Statistics", "SQL", "Data Analysis"],
            preferred_skills=["Deep Learning", "NLP", "Computer Vision", "Spark", "TensorFlow", "PyTorch"],
            min_experience_years=3,
            education_requirements=["Bachelor's in Computer Science", "Master's in Data Science", "PhD"],
            description="Analyze complex datasets and build predictive models"
        ),
        "data_engineer": JobRole(
            role_id="data_engineer",
            title="Data Engineer",
            department="AI",
            required_skills=["Python", "SQL", "ETL", "Data Pipelines", "AWS"],
            preferred_skills=["Spark", "Airflow", "Kafka", "Snowflake", "dbt", "Terraform"],
            min_experience_years=3,
            education_requirements=["Bachelor's in Computer Science", "Bachelor's in Engineering"],
            description="Build and maintain data infrastructure and pipelines"
        ),
        "ml_engineer": JobRole(
            role_id="ml_engineer",
            title="Machine Learning Engineer",
            department="AI",
            required_skills=["Python", "Machine Learning", "MLOps", "Docker", "AWS"],
            preferred_skills=["Kubernetes", "SageMaker", "MLflow", "Feature Stores", "Model Serving"],
            min_experience_years=4,
            education_requirements=["Bachelor's in Computer Science", "Master's in ML/AI"],
            description="Deploy and operationalize machine learning models at scale"
        ),
        "cloud_architect": JobRole(
            role_id="cloud_architect",
            title="Cloud Architect",
            department="AI",
            required_skills=["AWS", "Cloud Architecture", "Infrastructure as Code", "Security", "Networking"],
            preferred_skills=["Terraform", "Kubernetes", "Serverless", "Multi-cloud", "Cost Optimization"],
            min_experience_years=5,
            education_requirements=["Bachelor's in Computer Science", "AWS Solutions Architect"],
            description="Design and implement cloud infrastructure for AI workloads"
        )
    }

    def __init__(self, json_path: Optional[Path] = None):
        """Initialize JobRoleService with optional JSON file path."""
        self._roles = dict(self.PREDEFINED_ROLES)
        if json_path and json_path.exists():
            self._load_from_json(json_path)

    def _load_from_json(self, json_path: Path) -> None:
        """Load job roles from JSON file."""
        with open(json_path, "r") as f:
            data = json.load(f)
        
        for role_id, role_data in data.get("job_roles", {}).items():
            self._roles[role_id] = JobRole(
                role_id=role_data["role_id"],
                title=role_data["title"],
                department=role_data["department"],
                required_skills=role_data["required_skills"],
                preferred_skills=role_data["preferred_skills"],
                min_experience_years=role_data["min_experience_years"],
                education_requirements=role_data["education_requirements"],
                description=role_data["description"]
            )

    def get_role(self, role_id: str) -> JobRole:
        """Get a job role by ID.
        
        Args:
            role_id: The unique identifier for the job role.
            
        Returns:
            The JobRole object.
            
        Raises:
            ValueError: If role_id is not found.
        """
        if role_id not in self._roles:
            available = list(self._roles.keys())
            raise ValueError(f"Invalid role_id '{role_id}'. Available roles: {available}")
        return self._roles[role_id]

    def get_all_roles(self) -> List[JobRole]:
        """Get all predefined job roles."""
        return list(self._roles.values())

    def get_role_ids(self) -> List[str]:
        """Get all available role IDs."""
        return list(self._roles.keys())
