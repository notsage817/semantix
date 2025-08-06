# Job URL Crawler

This module provides tools for crawling company career pages to extract job posting URLs using Scrapy-Playwright.

## Features

- **Scrapy-Playwright Integration**: Uses Playwright for JavaScript-heavy career pages
- **YAML Configuration**: Flexible pattern matching via YAML configuration files
- **Metadata Extraction**: Extracts job titles, locations, departments, and other metadata
- **JSON Output**: Structured output with all job URLs and metadata
- **Respectful Crawling**: Built-in delays and robots.txt compliance

## Usage

### Basic Usage

```bash
python -m semantix.crawler.url_fetcher \
    --home-url "https://company.com/careers" \
    --output-file "jobs.json" \
    --pattern-yaml "pattern.yaml"
```

### Command Line Options

- `--home-url`: The home URL of the company's career page to crawl
- `--output-file`: Path to the output JSON file
- `--pattern-yaml`: Path to the YAML configuration file with extraction patterns
- `--user-agent`: Custom user agent string (optional)
- `--verbose, -v`: Enable verbose logging (optional)

## YAML Pattern Configuration

The YAML configuration file defines how to extract job URLs and metadata from the career page. See `pattern_example.yaml` for a complete example.

### Basic Structure

```yaml
company_name: "Company Name"

# Optional: Wait for dynamic content
wait_for:
  type: "selector"  # or "timeout"
  value: ".job-listing"

# Job URL extraction patterns
job_url_selectors:
  - selector: "a.job-link"
    attribute: "href"
    metadata:
      title: ".job-title::text"
      location: ".job-location::text"
      department: ".job-department::text"
```

### Metadata Extraction

For each job listing, you can extract metadata using CSS selectors:

```yaml
metadata:
  title:
    selector: ".job-title"
    attribute: "text"  # or any HTML attribute
    transform: "strip"  # optional: strip, lower, upper
  
  location: ".location::text"  # simplified syntax
```

## Output Format

The tool generates a JSON file with the following structure:

```json
{
  "source_url": "https://company.com/careers",
  "total_jobs": 25,
  "extraction_timestamp": "2024-01-15T10:30:00",
  "company_name": "Company Name",
  "jobs": [
    {
      "url": "https://company.com/careers/job/123",
      "title": "Software Engineer",
      "location": "San Francisco, CA",
      "department": "Engineering",
      "job_type": "Full-time",
      "posted_date": "2024-01-10",
      "company": "Company Name",
      "source_url": "https://company.com/careers",
      "metadata": {
        "title": "Software Engineer",
        "location": "San Francisco, CA"
      }
    }
  ]
}
```

## Installation Requirements

The crawler requires the following dependencies (automatically installed with the package):

- `scrapy>=2.11.0`
- `scrapy-playwright>=0.0.31`
- `pyyaml>=6.0`
- `click>=8.0.0`

## Browser Setup

Scrapy-Playwright requires browser binaries to be installed:

```bash
playwright install chromium
```