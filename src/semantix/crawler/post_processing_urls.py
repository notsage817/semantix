#!/usr/bin/env python3
"""
Post-processing script for job URL validation and deduplication.

This script processes the output from url_fetcher.py to:
1. Validate job URLs against defined patterns
2. Extract job metadata (ID, team, title) from URLs
3. Remove duplicate jobs based on job ID
4. Filter out invalid URLs
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse, parse_qs

import click
import yaml


def load_pattern_config(pattern_file: Path) -> Dict[str, Any]:
    """Load and validate pattern configuration from YAML file."""
    try:
        with open(pattern_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        # Validate required fields for post-processing
        required_fields = ["url_validation"]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field '{field}' in pattern configuration")
        
        return config
    
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML format: {e}")
    except FileNotFoundError:
        raise ValueError(f"Pattern file not found: {pattern_file}")


def validate_url(url: str, validation_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validate a job URL against the configured patterns and extract metadata.
    
    Returns:
        Dict with extracted fields if valid, None if invalid
    """
    if not url or not isinstance(url, str):
        return None
    
    # Check against invalid patterns first
    invalid_patterns = validation_config.get("invalid_patterns", [])
    for pattern in invalid_patterns:
        if re.search(pattern, url):
            return None
    
    # Check against valid pattern and extract fields
    valid_pattern = validation_config.get("valid_pattern", "")
    if not valid_pattern:
        return None
    
    match = re.match(valid_pattern, url)
    if not match:
        return None
    
    # Extract fields from the URL
    extracted_data = match.groupdict()
    
    # Clean up job title (URL decode and format)
    if "job_title" in extracted_data and extracted_data["job_title"]:
        job_title = extracted_data["job_title"]
        # Replace hyphens with spaces and title case
        job_title = job_title.replace("-", " ").title()
        extracted_data["job_title"] = job_title
    
    # Ensure all required fields are present
    extracted_fields = validation_config.get("extracted_fields", [])
    for field in extracted_fields:
        if field not in extracted_data:
            extracted_data[field] = ""
    
    return extracted_data


def process_jobs(input_data: Dict[str, Any], validation_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process job URLs to validate, extract metadata, and deduplicate.
    
    Args:
        input_data: Raw data from url_fetcher.py
        validation_config: URL validation configuration
        
    Returns:
        Processed data with validated and deduplicated jobs
    """
    original_jobs = input_data.get("jobs", [])
    processed_jobs = []
    seen_job_ids: Set[str] = set()
    
    stats = {
        "original_count": len(original_jobs),
        "valid_count": 0,
        "invalid_count": 0,
        "duplicate_count": 0,
        "final_count": 0
    }
    
    for job in original_jobs:
        url = job.get("url", "")
        
        # Validate URL and extract metadata
        validation_result = validate_url(url, validation_config)
        
        if validation_result is None:
            stats["invalid_count"] += 1
            continue
        
        stats["valid_count"] += 1
        
        # Check for duplicates by job_id
        job_id = validation_result.get("job_id", "")
        if job_id in seen_job_ids:
            stats["duplicate_count"] += 1
            continue
        
        if job_id:
            seen_job_ids.add(job_id)
        
        # Create processed job entry
        processed_job = {
            "url": url,
            "job_id": validation_result.get("job_id", ""),
            "team": validation_result.get("team", ""),
            "job_title": validation_result.get("job_title", ""),
            "title": job.get("title", ""),  # Keep original title if available
            "location": job.get("location", ""),
            "department": job.get("department", ""),
            "job_type": job.get("job_type", ""),
            "posted_date": job.get("posted_date", ""),
            "company": job.get("company", ""),
            "source_url": job.get("source_url", ""),
            "metadata": job.get("metadata", {}),
            "extracted_fields": validation_result
        }
        
        processed_jobs.append(processed_job)
    
    stats["final_count"] = len(processed_jobs)
    
    # Create output data structure
    output_data = {
        "source_url": input_data.get("source_url", ""),
        "original_total_jobs": stats["original_count"],
        "processed_total_jobs": stats["final_count"],
        "processing_stats": stats,
        "processing_timestamp": datetime.now().isoformat(),
        "company_name": input_data.get("company_name", ""),
        "total_pages_crawled": input_data.get("total_pages_crawled", 0),
        "jobs": processed_jobs
    }
    
    return output_data


@click.command()
@click.option(
    "--url-file",
    required=True,
    type=click.Path(exists=True),
    help="Input JSON file from url_fetcher.py containing raw job URLs",
)
@click.option(
    "--output-file",
    required=True,
    type=click.Path(),
    help="Output JSON file for processed and validated job URLs",
)
@click.option(
    "--pattern-yaml",
    required=True,
    type=click.Path(exists=True),
    help="YAML configuration file with URL validation patterns",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose logging",
)
def main(
    url_file: str,
    output_file: str,
    pattern_yaml: str,
    verbose: bool,
) -> None:
    """
    Post-process job URLs for validation, metadata extraction, and deduplication.
    
    This tool processes the raw job URL data from url_fetcher.py to:
    - Validate URLs against configured patterns
    - Extract metadata like job ID, team, and title from URLs
    - Remove duplicate jobs based on job ID
    - Filter out invalid or unwanted URLs
    """
    try:
        # Load configuration
        if verbose:
            click.echo("Loading pattern configuration...")
        pattern_config = load_pattern_config(Path(pattern_yaml))
        validation_config = pattern_config.get("url_validation", {})
        
        # Load input data
        if verbose:
            click.echo(f"Loading input data from {url_file}...")
        with open(url_file, "r", encoding="utf-8") as f:
            input_data = json.load(f)
        
        if verbose:
            click.echo(f"Found {len(input_data.get('jobs', []))} jobs to process")
        
        # Process jobs
        if verbose:
            click.echo("Processing and validating job URLs...")
        output_data = process_jobs(input_data, validation_config)
        
        # Save processed data
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        # Display results
        stats = output_data["processing_stats"]
        click.echo(f"Processing complete!")
        click.echo(f"Original jobs: {stats['original_count']}")
        click.echo(f"Valid jobs: {stats['valid_count']}")
        click.echo(f"Invalid jobs: {stats['invalid_count']}")
        click.echo(f"Duplicate jobs: {stats['duplicate_count']}")
        click.echo(f"Final jobs: {stats['final_count']}")
        click.echo(f"Results saved to: {output_path}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()