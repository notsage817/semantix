"""
JobPosting data model for structured job posting data.

This module provides a comprehensive dataclass for modeling job postings
with JSON serialization/deserialization capabilities.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from enum import Enum


class JobType(Enum):
    """Enumeration for job types."""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    TEMPORARY = "temporary"
    INTERNSHIP = "internship"
    FREELANCE = "freelance"
    VOLUNTEER = "volunteer"


class ExperienceLevel(Enum):
    """Enumeration for experience levels."""
    ENTRY_LEVEL = "entry_level"
    ASSOCIATE = "associate"
    MID_LEVEL = "mid_level"
    SENIOR_LEVEL = "senior_level"
    DIRECTOR = "director"
    EXECUTIVE = "executive"
    INTERNSHIP = "internship"
    NOT_APPLICABLE = "not_applicable"


class WorkArrangement(Enum):
    """Enumeration for work arrangements."""
    ON_SITE = "on_site"
    REMOTE = "remote"
    HYBRID = "hybrid"


@dataclass
class JobPosting:
    """
    Comprehensive data model for job postings.
    
    This dataclass captures all common attributes of a job posting,
    including company information, job details, requirements, and metadata.
    """
    
    # Basic Job Information
    job_id: str
    title: str
    company: str
    description: str = ""
    summary: str = ""
    
    # Location and Work Arrangement
    location: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    work_arrangement: Optional[WorkArrangement] = None
    remote_work_option: bool = False
    hybrid_option: bool = False
    
    # Time-related Information
    publish_date: Optional[str] = None  # ISO format string
    application_deadline: Optional[str] = None  # ISO format string
    start_date: Optional[str] = None  # ISO format string
    scraped_date: Optional[str] = None  # ISO format string
    
    # Employment Details
    job_type: Optional[JobType] = None
    experience_level: Optional[ExperienceLevel] = None
    department: str = ""
    team: str = ""
    division: str = ""
    
    # Compensation
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: str = "USD"
    hourly_rate_min: Optional[float] = None
    hourly_rate_max: Optional[float] = None
    benefits: List[str] = field(default_factory=list)
    pay_benefit: str = ""
    equity_compensation: bool = False
    
    # Requirements and Skills
    required_skills: List[str] = field(default_factory=list)
    preferred_skills: List[str] = field(default_factory=list)
    minimum_qualifications: List[str] = field(default_factory=list)
    preferred_qualifications: List[str] = field(default_factory=list)
    education_requirements: List[str] = field(default_factory=list)
    experience_requirements: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    
    # Application Process
    application_url: str = ""
    contact_email: str = ""
    contact_person: str = ""
    application_instructions: str = ""
    
    # Company Information
    company_size: str = ""
    industry: str = ""
    company_website: str = ""
    company_description: str = ""
    
    # Additional Details
    work_schedule: str = ""
    visa_sponsorship: Optional[bool] = None
    security_clearance_required: Optional[bool] = None
    travel_required: Optional[str] = None  # e.g., "25%", "Minimal", "Extensive"
    relocation_assistance: Optional[bool] = None
    
    # Metadata
    source_url: str = ""
    source_platform: str = ""  # e.g., "jobs.apple.com", "linkedin", "indeed"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the JobPosting to a dictionary.
        
        Handles enum serialization properly.
        
        Returns:
            Dictionary representation of the job posting
        """
        data = asdict(self)
        
        # Convert enums to their values
        if self.job_type:
            data['job_type'] = self.job_type.value
        if self.experience_level:
            data['experience_level'] = self.experience_level.value
        if self.work_arrangement:
            data['work_arrangement'] = self.work_arrangement.value
            
        return data
    
    def to_json(self, indent: Optional[int] = None) -> str:
        """
        Convert the JobPosting to a JSON string.
        
        Args:
            indent: Number of spaces for indentation (None for compact JSON)
            
        Returns:
            JSON string representation of the job posting
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def save_to_file(self, file_path: str, indent: Optional[int] = 2) -> None:
        """
        Save the JobPosting to a JSON file.
        
        Args:
            file_path: Path to save the JSON file
            indent: Number of spaces for indentation
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=indent, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobPosting':
        """
        Create a JobPosting instance from a dictionary.
        
        Args:
            data: Dictionary containing job posting data
            
        Returns:
            JobPosting instance
        """
        # Handle enum conversion
        if 'job_type' in data and isinstance(data['job_type'], str):
            try:
                data['job_type'] = JobType(data['job_type'])
            except ValueError:
                data['job_type'] = None
                
        if 'experience_level' in data and isinstance(data['experience_level'], str):
            try:
                data['experience_level'] = ExperienceLevel(data['experience_level'])
            except ValueError:
                data['experience_level'] = None
                
        if 'work_arrangement' in data and isinstance(data['work_arrangement'], str):
            try:
                data['work_arrangement'] = WorkArrangement(data['work_arrangement'])
            except ValueError:
                data['work_arrangement'] = None
        
        # Filter out any keys that aren't valid fields
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered_data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'JobPosting':
        """
        Create a JobPosting instance from a JSON string.
        
        Args:
            json_str: JSON string containing job posting data
            
        Returns:
            JobPosting instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'JobPosting':
        """
        Load a JobPosting instance from a JSON file.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            JobPosting instance
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    @classmethod
    def load_multiple_from_file(cls, file_path: str) -> List['JobPosting']:
        """
        Load multiple JobPosting instances from a JSON file.
        
        Expects the file to contain either:
        - A list of job posting objects
        - An object with a 'jobs' key containing the list
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            List of JobPosting instances
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle different JSON structures
        if isinstance(data, list):
            jobs_data = data
        elif isinstance(data, dict) and 'jobs' in data:
            jobs_data = data['jobs']
        else:
            raise ValueError("JSON file must contain either a list of jobs or an object with a 'jobs' key")
        
        return [cls.from_dict(job_data) for job_data in jobs_data]
    
    def update_scraped_date(self) -> None:
        """Update the scraped_date to the current timestamp."""
        self.scraped_date = datetime.now().isoformat()
    
    def has_salary_info(self) -> bool:
        """Check if the job posting has any salary information."""
        return (
            self.salary_min is not None or 
            self.salary_max is not None or 
            self.hourly_rate_min is not None or 
            self.hourly_rate_max is not None or 
            bool(self.pay_benefit.strip())
        )
    
    def get_salary_range(self) -> Optional[str]:
        """
        Get a formatted salary range string.
        
        Returns:
            Formatted salary range or None if no salary info available
        """
        if self.salary_min and self.salary_max:
            return f"{self.salary_currency} {self.salary_min:,.0f} - {self.salary_max:,.0f}"
        elif self.salary_min:
            return f"{self.salary_currency} {self.salary_min:,.0f}+"
        elif self.salary_max:
            return f"Up to {self.salary_currency} {self.salary_max:,.0f}"
        elif self.hourly_rate_min and self.hourly_rate_max:
            return f"{self.salary_currency} {self.hourly_rate_min}/hr - {self.hourly_rate_max}/hr"
        elif self.hourly_rate_min:
            return f"{self.salary_currency} {self.hourly_rate_min}/hr+"
        elif self.hourly_rate_max:
            return f"Up to {self.salary_currency} {self.hourly_rate_max}/hr"
        return None