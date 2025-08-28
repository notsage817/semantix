#!/usr/bin/env python3
"""
Job HTML Extractor

This script extracts job posting information from HTML files using configurable YAML patterns
and converts them to JobPosting dataclass instances.
"""

import argparse
import os
import re
import sys
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse, parse_qs

from bs4 import BeautifulSoup
import logging

# Add the parent directory to Python path to import our models
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from src.semantix.models import JobPosting
    from src.semantix.models.job_posting import JobType, ExperienceLevel, WorkArrangement
except ImportError:
    # Try relative imports if absolute imports fail
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from semantix.models import JobPosting
    from semantix.models.job_posting import JobType, ExperienceLevel, WorkArrangement


class HTMLJobExtractor:
    """Extracts job posting information from HTML files using YAML configuration patterns."""

    def __init__(self, pattern_file: str):
        """
        Initialize the HTML job extractor.

        Args:
            pattern_file: Path to YAML pattern configuration file
        """
        self.pattern_file = pattern_file
        self.patterns = self._load_patterns()
        self.logger = logging.getLogger(__name__)

    def _load_patterns(self) -> Dict[str, Any]:
        """Load extraction patterns from YAML file."""
        try:
            with open(self.pattern_file, "r", encoding="utf-8") as f:
                full_config = yaml.safe_load(f)

            # Extract just the html_extraction section if it exists
            if "html_extraction" in full_config:
                patterns = full_config["html_extraction"]
            else:
                # Fall back to the full config for backward compatibility
                patterns = full_config

            return patterns
        except (FileNotFoundError, yaml.YAMLError) as e:
            raise ValueError(f"Error loading pattern file {self.pattern_file}: {e}")

    def _extract_with_selector(
        self, soup: BeautifulSoup, config: Dict[str, Any], source_url: str = ""
    ) -> Optional[str]:
        """
        Extract text using CSS selector configuration.

        Args:
            soup: BeautifulSoup parsed HTML
            config: Selector configuration from YAML
            source_url: Source URL for absolute URL conversion

        Returns:
            Extracted text or None if not found
        """
        if isinstance(config, dict):
            # Handle default values
            if "default" in config and not config.get("selector"):
                default_value = config["default"]
                if default_value == "current_timestamp":
                    return datetime.now().isoformat()
                return default_value

            # Handle URL parameter extraction
            if config.get("url_param") and source_url:
                parsed_url = urlparse(source_url)
                query_params = parse_qs(parsed_url.query)
                param_value = query_params.get(config["url_param"])
                if param_value:
                    return param_value[0]
                return None

            selector = config.get("selector")
            attribute = config.get("attribute", "text")
            fallback_selectors = config.get("fallback_selectors", [])
            transform = config.get("transform")

            # Try primary selector
            if selector:
                element = soup.select_one(selector)
                if element:
                    value = self._get_element_value(element, attribute)
                    if value:
                        return self._apply_transform(value, transform, source_url)

            # Try fallback selectors
            for fallback in fallback_selectors:
                element = soup.select_one(fallback)
                if element:
                    value = self._get_element_value(element, attribute)
                    if value:
                        return self._apply_transform(value, transform, source_url)

            return None
        else:
            # Simple string selector
            element = soup.select_one(config)
            if element:
                return element.get_text(strip=True)
            return None

    def _get_element_value(self, element, attribute: str) -> Optional[str]:
        """Get value from HTML element based on attribute type."""
        if attribute == "text":
            return element.get_text(strip=True)
        elif attribute == "content":
            return element.get("content")
        elif attribute == "href":
            return element.get("href")
        elif attribute in ["datetime", "value", "id", "class"]:
            return element.get(attribute)
        else:
            return element.get(attribute)

    def _apply_transform(self, value: str, transform: Optional[str], source_url: str = "") -> str:
        """Apply transformation to extracted value."""
        if not transform or not value:
            return value

        transformations = self.patterns.get("transformations", {})
        if transform in transformations:
            transform_config = transformations[transform]
            transform_type = transform_config.get("type")

            if transform_type == "regex_replace":
                pattern = transform_config.get("pattern")
                replacement = transform_config.get("replacement", "")
                return re.sub(pattern, replacement, value)

            elif transform_type == "whitespace_normalize":
                return " ".join(value.split())

            elif transform_type == "bullet_points_to_list":
                # Extract bullet points from text - enhanced for HTML content
                if not value:
                    return []

                # Try to split by common bullet point patterns
                lines = value.split("\n")
                bullet_points = []

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    # Remove common bullet point characters and clean
                    if line.startswith(("•", "-", "*", "▪", "‣", "▸")):
                        clean_line = line.lstrip("•-*▪‣▸ ").strip()
                        if clean_line:
                            bullet_points.append(clean_line)
                    elif (
                        line and len(line.strip()) > 10
                    ):  # Assume non-bullet lines that are long enough are items
                        bullet_points.append(line.strip())

                return bullet_points if bullet_points else [value.strip()] if value.strip() else []

            elif transform_type == "extract_html_list_items":
                # Extract list items from HTML - this needs the soup object
                # This transformation should be handled in _extract_list_items method
                return self._extract_html_list_items(value, transform_config.get("soup"))

            elif transform_type == "absolute_url":
                base_url = transform_config.get("base_url", source_url)
                if value.startswith("/"):
                    return urljoin(base_url, value)
                return value

        return value

    def _extract_list_items(self, soup: BeautifulSoup, selector: str) -> List[str]:
        """
        Extract list items from HTML elements as a list of strings.

        Args:
            soup: BeautifulSoup parsed HTML
            selector: CSS selector for the container element

        Returns:
            List of text content from list items
        """
        container = soup.select_one(selector)
        if not container:
            return []

        # Look for list items within the container
        list_items = container.select("li")
        if list_items:
            # Extract text from each list item and clean it
            items = []
            for li in list_items:
                text = li.get_text(strip=True)
                if text and len(text.strip()) > 2:  # Filter out empty or very short items
                    items.append(text)
            return items

        # If no list items found, try to extract bullet points from text
        text_content = container.get_text()
        if text_content:
            return self._apply_transform(text_content, "bullet_points_to_list")

        return []

    def _extract_skills(self, text_content: str) -> Dict[str, List[str]]:
        """Extract skills from text using pattern matching."""
        skills_config = self.patterns.get("skills_extraction", {})
        technical_patterns = skills_config.get("technical_skills_patterns", [])
        soft_patterns = skills_config.get("soft_skills_patterns", [])

        required_skills = []

        # Extract technical skills
        for pattern in technical_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    required_skills.extend(match)
                else:
                    required_skills.append(match)

        # For Apple jobs, soft skills should go to required_skills, not preferred_skills
        # Only extract soft skills if they appear in qualifications text
        for pattern in soft_patterns:
            if re.search(pattern, text_content, re.IGNORECASE):
                # Clean up the pattern to get readable skill name
                skill_name = pattern.replace("\\\\b", "").replace("\\b", "").strip()
                required_skills.append(skill_name)

        return {
            "required_skills": list(set(required_skills)),
            "preferred_skills": [],  # Empty for Apple jobs as they don't have separate preferred skills
        }

    def _extract_salary_info(self, pay_text: str) -> Dict[str, Any]:
        """Extract salary information from pay and benefits text."""
        if not pay_text:
            return {}

        salary_patterns = self.patterns.get("salary_patterns", {})
        result = {}

        # Extract salary range
        range_pattern = salary_patterns.get("salary_range_pattern")
        if range_pattern:
            match = re.search(range_pattern, pay_text)
            if match:
                try:
                    min_salary = float(match.group(1).replace(",", ""))
                    max_salary = float(match.group(2).replace(",", ""))
                    result["salary_min"] = min_salary
                    result["salary_max"] = max_salary
                    result["salary_currency"] = "USD"
                except (ValueError, IndexError):
                    pass

        # Extract hourly rate
        hourly_pattern = salary_patterns.get("hourly_rate_pattern")
        if hourly_pattern:
            match = re.search(hourly_pattern, pay_text)
            if match:
                try:
                    hourly_rate = float(match.group(1))
                    result["hourly_rate_min"] = hourly_rate
                except (ValueError, IndexError):
                    pass

        return result

    def _determine_experience_level(
        self, title: str, description: str
    ) -> Optional[ExperienceLevel]:
        """Determine experience level from title and description."""
        exp_patterns = self.patterns.get("experience_patterns", {})
        combined_text = f"{title} {description}".lower()

        for level, keywords in exp_patterns.items():
            for keyword in keywords:
                if re.search(keyword, combined_text, re.IGNORECASE):
                    try:
                        return ExperienceLevel(level)
                    except ValueError:
                        continue

        return None

    def _determine_job_type(self, title: str, description: str) -> Optional[JobType]:
        """Determine job type from title and description."""
        job_patterns = self.patterns.get("job_type_patterns", {})
        combined_text = f"{title} {description}".lower()

        for job_type, keywords in job_patterns.items():
            for keyword in keywords:
                if re.search(keyword, combined_text, re.IGNORECASE):
                    try:
                        return JobType(job_type)
                    except ValueError:
                        continue

        return JobType.FULL_TIME  # Default assumption

    def _determine_work_arrangement(self, description: str) -> Optional[WorkArrangement]:
        """Determine work arrangement from description."""
        work_patterns = self.patterns.get("work_arrangement_patterns", {})
        text = description.lower()

        for arrangement, keywords in work_patterns.items():
            for keyword in keywords:
                if re.search(keyword, text, re.IGNORECASE):
                    try:
                        return WorkArrangement(arrangement)
                    except ValueError:
                        continue

        return None

    def _parse_location(self, location_text: str) -> Dict[str, str]:
        """Parse location text into components."""
        if not location_text:
            return {}

        result = {"location": location_text}

        # Simple location parsing - could be enhanced
        if "," in location_text:
            parts = [p.strip() for p in location_text.split(",")]
            if len(parts) >= 2:
                result["city"] = parts[0]
                result["state"] = parts[1]
                if len(parts) >= 3:
                    result["country"] = parts[2]
            else:
                result["city"] = parts[0] if parts else ""

        return result

    def extract_job_posting(
        self, html_content: str, source_url: str = "", filename: str = ""
    ) -> Optional[JobPosting]:
        """
        Extract job posting information from HTML content.

        Args:
            html_content: HTML content to parse
            source_url: Source URL of the job posting
            filename: Filename of the HTML file (for debugging)

        Returns:
            JobPosting instance or None if extraction fails
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Check for "page not found" or error pages
            error_indicators = [
                "Page not found",
                "Sorry, this role does not exist",
                "is no longer available",
                "page-not-found-wrapper",
            ]

            html_text = soup.get_text().lower()
            for indicator in error_indicators:
                if indicator.lower() in html_text:
                    self.logger.warning(f"Skipping error page in {filename}: {indicator}")
                    return None

            # Extract basic information
            basic_config = self.patterns.get("basic_info", {})
            job_id = self._extract_with_selector(soup, basic_config.get("job_id"), source_url)
            title = self._extract_with_selector(soup, basic_config.get("title"), source_url)
            company = self._extract_with_selector(soup, basic_config.get("company"), source_url)

            # Required fields validation
            if not job_id or not title:
                self.logger.warning(
                    f"Missing required fields in {filename}: job_id={job_id}, title={title}"
                )
                return None

            # Extract time information
            time_config = self.patterns.get("time_info", {})
            publish_date = self._extract_with_selector(
                soup, time_config.get("publish_date"), source_url
            )
            scraped_date = self._extract_with_selector(
                soup, time_config.get("scraped_date"), source_url
            )

            # Extract location
            location_config = self.patterns.get("location", {})
            location_text = self._extract_with_selector(
                soup, location_config.get("location"), source_url
            )
            location_parts = self._parse_location(location_text or "")

            # Extract content
            content_config = self.patterns.get("content", {})
            summary = self._extract_with_selector(soup, content_config.get("summary"), source_url)
            description = self._extract_with_selector(
                soup, content_config.get("description"), source_url
            )
            pay_benefit = self._extract_with_selector(
                soup, content_config.get("pay_benefit"), source_url
            )

            # Extract qualifications as lists
            minimum_qualifications = self._extract_list_items(
                soup, content_config.get("required_qualifications", {}).get("selector", "")
            )
            preferred_qualifications = self._extract_list_items(
                soup, content_config.get("preferred_qualifications", {}).get("selector", "")
            )

            # Also get text versions for skills extraction
            required_quals_text = self._extract_with_selector(
                soup, content_config.get("required_qualifications"), source_url
            )
            preferred_quals_text = self._extract_with_selector(
                soup, content_config.get("preferred_qualifications"), source_url
            )

            # Extract team information
            team_config = self.patterns.get("team_info", {})
            team = self._extract_with_selector(soup, team_config.get("team"), source_url)
            department = self._extract_with_selector(
                soup, team_config.get("department"), source_url
            )

            # Extract application information
            app_config = self.patterns.get("application", {})
            application_url = self._extract_with_selector(
                soup, app_config.get("application_url"), source_url
            )

            # Extract skills from qualifications text
            combined_quals = f"{required_quals_text or ''} {preferred_quals_text or ''}"
            skills_data = self._extract_skills(combined_quals)

            # Extract salary information
            salary_data = self._extract_salary_info(pay_benefit or "")

            # Determine job characteristics
            experience_level = self._determine_experience_level(
                title or "", f"{description or ''} {combined_quals}"
            )
            job_type = self._determine_job_type(title or "", description or "")
            work_arrangement = self._determine_work_arrangement(
                f"{description or ''} {combined_quals}"
            )

            # Extract additional fields from basic_info
            source_platform = self._extract_with_selector(
                soup, basic_config.get("source_platform"), source_url
            )
            if not source_url and basic_config.get("source_url"):
                source_url = (
                    self._extract_with_selector(soup, basic_config.get("source_url"), source_url)
                    or ""
                )

            # Create JobPosting instance
            job_posting = JobPosting(
                job_id=job_id,
                title=title,
                company=company or "Apple Inc.",
                description=description or "",
                summary=summary or "",
                # Location fields
                location=location_parts.get("location", location_text or ""),
                city=location_parts.get("city", ""),
                state=location_parts.get("state", ""),
                country=location_parts.get("country", ""),
                work_arrangement=work_arrangement,
                # Time fields
                publish_date=publish_date,
                scraped_date=scraped_date,
                # Employment details
                job_type=job_type,
                experience_level=experience_level,
                team=team or "",
                department=department or "",
                # Skills and requirements
                required_skills=skills_data.get("required_skills", []),
                preferred_skills=skills_data.get("preferred_skills", []),
                minimum_qualifications=minimum_qualifications,
                preferred_qualifications=preferred_qualifications,
                education_requirements=self._extract_education_requirements(minimum_qualifications),
                experience_requirements=self._extract_experience_requirements(
                    minimum_qualifications, preferred_qualifications
                ),
                # Compensation
                pay_benefit=pay_benefit or "",
                **salary_data,  # Includes salary_min, salary_max, hourly_rate_min, etc.
                # Application
                application_url=application_url or "",
                # Metadata
                source_url=source_url,
                source_platform=source_platform or "jobs.apple.com",
            )

            # Update scraped date
            job_posting.update_scraped_date()

            return job_posting

        except Exception as e:
            self.logger.error(f"Error extracting job from {filename}: {e}")
            return None

    def _convert_to_list(self, value: Any) -> List[str]:
        """Convert value to list of strings."""
        if isinstance(value, list):
            return [str(item) for item in value]
        elif isinstance(value, str):
            return [value] if value else []
        else:
            return []

    def _extract_education_requirements(self, qualifications: List[str]) -> List[str]:
        """Extract education-specific requirements from qualifications list."""
        education_requirements = []

        # Education-related keywords to look for
        education_keywords = [
            "degree",
            "bachelor",
            "master",
            "phd",
            "bs",
            "ba",
            "ms",
            "ma",
            "mba",
            "education",
            "university",
            "college",
            "graduate",
            "undergraduate",
            "computer science",
            "engineering",
            "equivalent education",
        ]

        for qual in qualifications:
            qual_lower = qual.lower()
            # Check if any education keyword appears in the qualification
            if any(keyword in qual_lower for keyword in education_keywords):
                education_requirements.append(qual)

        return education_requirements

    def _extract_experience_requirements(
        self, minimum_quals: List[str], preferred_quals: List[str]
    ) -> List[str]:
        """Extract experience-specific requirements from qualifications lists."""
        experience_requirements = []

        # Experience-related keywords to look for
        experience_keywords = [
            "experience",
            "years",
            "background",
            "familiar",
            "knowledge of",
            "understanding of",
            "skilled",
            "proficient",
            "expertise",
            "working with",
            "development",
            "programming",
        ]

        # Check minimum qualifications for experience-related items
        for qual in minimum_quals:
            qual_lower = qual.lower()
            # Skip education requirements
            if any(
                edu_keyword in qual_lower
                for edu_keyword in [
                    "degree",
                    "bachelor",
                    "master",
                    "phd",
                    "bs",
                    "ba",
                    "ms",
                    "ma",
                    "education",
                    "university",
                    "college",
                ]
            ):
                continue
            # Include experience-related items
            if any(keyword in qual_lower for keyword in experience_keywords):
                experience_requirements.append(qual)

        # Add all preferred qualifications as they are typically experience-related
        experience_requirements.extend(preferred_quals)

        return experience_requirements

    def process_html_files(self, html_dump_dir: str, json_dump_dir: str) -> None:
        """
        Process all HTML files in the dump directory and extract job postings.

        Args:
            html_dump_dir: Directory containing HTML files
            json_dump_dir: Directory to save extracted JSON files
        """
        html_dir = Path(html_dump_dir)
        json_dir = Path(json_dump_dir)

        if not html_dir.exists():
            raise FileNotFoundError(f"HTML dump directory not found: {html_dump_dir}")

        json_dir.mkdir(parents=True, exist_ok=True)

        html_files = list(html_dir.glob("*.html"))
        if not html_files:
            self.logger.warning(f"No HTML files found in {html_dump_dir}")
            return

        successful_extractions = 0
        failed_extractions = 0

        print(f"Processing {len(html_files)} HTML files...")

        for html_file in html_files:
            try:
                print(f"Processing: {html_file.name}")

                with open(html_file, "r", encoding="utf-8") as f:
                    html_content = f.read()

                job_posting = self.extract_job_posting(html_content, filename=html_file.name)

                if job_posting:
                    # Generate output filename
                    json_filename = html_file.stem + ".json"
                    json_filepath = json_dir / json_filename

                    # Save JobPosting as JSON
                    job_posting.save_to_file(str(json_filepath), indent=2)
                    print(f"  ✓ Extracted: {job_posting.title} (ID: {job_posting.job_id})")
                    successful_extractions += 1
                else:
                    print("  ✗ Failed to extract job posting")
                    failed_extractions += 1

            except Exception as e:
                print(f"  ✗ Error processing {html_file.name}: {e}")
                failed_extractions += 1

        print("\nExtraction Summary:")
        print(f"  Successful: {successful_extractions}")
        print(f"  Failed: {failed_extractions}")
        print(f"  Total: {len(html_files)}")
        print(f"\nJSON files saved to: {json_dump_dir}")


def main():
    """Main entry point for the job HTML extractor."""
    parser = argparse.ArgumentParser(
        description="Extract job posting information from HTML files using YAML patterns"
    )
    parser.add_argument(
        "--html-dump-dir", required=True, help="Directory containing HTML files to process"
    )
    parser.add_argument(
        "--json-dump-dir", required=True, help="Directory to save extracted JSON files"
    )
    parser.add_argument(
        "--pattern-yaml",
        default="apple_pattern.yaml",
        help="YAML pattern configuration file (default: apple_pattern.yaml)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Validate inputs
    if not os.path.isdir(args.html_dump_dir):
        print(f"Error: HTML dump directory not found: {args.html_dump_dir}", file=sys.stderr)
        sys.exit(1)

    if not os.path.isfile(args.pattern_yaml):
        print(f"Error: Pattern YAML file not found: {args.pattern_yaml}", file=sys.stderr)
        sys.exit(1)

    try:
        # Create extractor and process files
        extractor = HTMLJobExtractor(args.pattern_yaml)
        extractor.process_html_files(args.html_dump_dir, args.json_dump_dir)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
